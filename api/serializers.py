"""
API Serializers for Kobold Keeper.

This module defines serializers for all core models (User, Group, Character, Roll)
and includes specialized serializers for authentication (JWT), password recovery,
and performance analytics. It handles validation, nested data representation,
and ensures transactional integrity for user registration and related flows.
"""


from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import (
    AuthenticationFailed,
    ValidationError,
    PermissionDenied
)
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User, Group, Character, Roll, RecoveryKey, GroupPerformanceRecord
from .utils import generate_key


class GroupPerformanceRecordSerializer(serializers.ModelSerializer):
    """
    Serializer for the GroupPerformanceRecord model, providing luck and roll statistics.
    """
    last_updated = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = GroupPerformanceRecord
        fields = [
            'average_luck_index',
            'total_rolls',
            'lowest_roll',
            'highest_roll',
            'luckiest_player_name',
            'luckiest_player_score',
            'least_lucky_player_name',
            'least_lucky_player_score',
            'last_updated',
        ]
        read_only_fields = fields


class GroupSerializer(serializers.ModelSerializer):
    """
    Serializer for the Group model (Campaigns).
    Includes nested, read-only performance analytics from GroupPerformanceRecord.
    """
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())

    characters = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='character_name'
    )

    performance = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ['id',
                  'group_name',
                  'owner',
                  'characters',
                  'performance',
                  ]
        read_only_fields = ['id',
                            'owner',
                            'performance',
                            ]

    def get_performance(self, obj):
        """
        Retrieves and serializes the single GroupPerformanceRecord linked
        via the 'performance_record' OneToOne relation.

        Args:
            obj (Group): The current Group instance.

        Returns:
            dict or None: Serialized record data or None if no record exists yet.
        """
        try:
            performance_instance = obj.performance_record
            return GroupPerformanceRecordSerializer(performance_instance).data

        except ObjectDoesNotExist:
            return None

    def create(self, validated_data):
        return Group.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.group_name = validated_data.get('group_name', instance.group_name)
        instance.save()
        return instance


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User registration. Handles creating a User and an associated
    RecoveryKey in a single, atomic transaction.
    """
    password = serializers.CharField(write_only=True,
                                     required=True,
                                     style={'input_type': 'password'}
                                     )

    recovery_key = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'recovery_key']

    def create(self, validated_data):
        """
        Overrides the create method to handle user creation and recovery key generation atomically.
        """
        with transaction.atomic():
            password = validated_data.pop('password')
            raw_key = generate_key()
            user = User.objects.create_user(**validated_data, password=password)
            recovery_key_instance = RecoveryKey.objects.create(user=user)
            recovery_key_instance.set_key(raw_key)
            recovery_key_instance.save()
            user.recovery_key = raw_key

            return user

    def update(self, instance, validated_data):
        """
        ModelSerializers intended for writing need both update and create.
        This serializer is typically only used for registration (creation),
        but we add this for completeness.
        """
        raise NotImplementedError("This serializer is for user registration (create) only.")

class CharacterSerializer(serializers.ModelSerializer):
    """
    Serializer for the Character model.
    Includes custom logic to restrict group choices to the user's owned groups.
    """
    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all())

    class Meta:
        model = Character
        fields = [
            'id',
            'character_name',
            'character_note',
            'user',
            'is_npc',
            'group'
        ]
        read_only_fields = ['id',
                            'user',
                            ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'request' in self.context:
            request = self.context['request']
            user = request.user

            if user and user.is_authenticated:
                self.fields['group'].queryset = Group.objects.filter(owner=user)
            else:
                self.fields['group'].queryset = Group.objects.none()


class RollSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new Roll record.
    It takes a die formula, validates it, calculates the result using DiceRoller,
    and stores the final values.
    """
    target_character_id = serializers.PrimaryKeyRelatedField(
        queryset=Character.objects.all(),
        source='character',
        write_only=True,
        help_text="The ID of the Character for whom the roll is being made."
    )

    roll_input = serializers.CharField(
        max_length=512,
        write_only=True,
        help_text="e.g., '2d6+5' or '1d20-1'"
    )

    group_id = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        source='group',
        write_only=True,
        help_text="The ID of the Group associated with the roll."
    )

    roll_value = serializers.IntegerField(read_only=True)
    raw_dice_rolls = serializers.JSONField(read_only=True)

    user_id = serializers.ReadOnlyField(source='character.user.id')

    class Meta:
        model = Roll
        fields = [
            'id',
            'target_character_id',
            'group_id',
            'roll_input',

            'roll_value',
            'raw_dice_rolls',
            'user_id',
        ]

    def validate(self, attrs):
        """
        Validates the character and group belong to the current user.
        """
        user = self.context['request'].user
        character = attrs.get('character')
        group = attrs.get('group')
        if character and character.user != user:
            raise PermissionDenied("Character does not belong to the current user.")

        if group:
            if group.owner != user:
                raise PermissionDenied("Group does not belong to the current user.")

            if character and character.group and character.group != group:
                raise ValidationError("Character must belong to the specified Group.")

        return attrs

    def create(self, validated_data):
        return Roll.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """Rolls are immutable and should not be updated."""
        raise NotImplementedError("Roll records are immutable and cannot be updated.")


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom serializer for JWT token acquisition.
    This overrides the default logic to ensure Django's standard `authenticate`
    is used against our custom User model.
    """

    def create(self, validated_data):
        """Not used for token generation, but required by Pylint/abstract base class."""
        raise NotImplementedError("Token serialization does not support direct creation.")

    def update(self, instance, validated_data):
        """Not used for token generation, but required by Pylint/abstract base class."""
        raise NotImplementedError("Token serialization does not support direct updating.")

    def validate(self, attrs):
        username = attrs.get(User.USERNAME_FIELD)
        password = attrs.get('password')
        user = authenticate(
            request=self.context.get('request'),
            username=username,
            password=password
        )

        if user is None or not user.is_active:
            raise AuthenticationFailed(
                self.error_messages['no_active_account'],
                'no_active_account',
            )

        self.user = user
        return super().validate(attrs)


class PasswordResetWithKeySerializer(serializers.Serializer):
    """
    Handles password reset using a one-time recovery key (used when the user is not logged in).
    """
    username = serializers.CharField(required=True)
    recovery_key = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)

    def create(self, validated_data):
        """Not used; logic is handled in .save()."""
        raise NotImplementedError("This serializer is for password reset (update logic only).")

    def update(self, instance, validated_data):
        """Not used; logic is handled in .save()."""
        raise NotImplementedError("This serializer is for password reset (update logic only).")

    def validate(self, attrs):
        """
        Validates the username and recovery key combination.
        Note: Renamed parameter from 'data' to 'attrs' to resolve W0237 warning.
        """
        username = attrs.get('username')
        recovery_key = attrs.get('recovery_key')

        try:
            user = User.objects.get(**{User.USERNAME_FIELD: username})
        except User.DoesNotExist as exc:
            raise ValidationError(
                "Authentication failed. Invalid username or recovery key."
            ) from exc

        try:
            recovery_instance = RecoveryKey.objects.get(user=user)
        except RecoveryKey.DoesNotExist as exc:
            raise ValidationError(
                "Authentication failed. Invalid username or recovery key."
            ) from exc

        if not check_password(recovery_key, recovery_instance.recovery_key_hash):
            raise ValidationError("Authentication failed. Invalid username or recovery key.")

        self.user = user
        return attrs

    def save(self, **kwargs):
        """
        Saves the new password. The recovery key is intentionally NOT invalidated here,
        as it is designed to be a multi-use key.
        """
        new_password = self.validated_data.get('new_password')
        self.user.set_password(new_password)
        self.user.save()

        return self.user


class UserPasswordChangeSerializer(serializers.Serializer):
    """
    Handles password change for a LOGGED-IN user.
    Requires old password verification.
    """
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    new_password_confirm = serializers.CharField(write_only=True, required=True)

    def create(self, validated_data):
        """Not used; logic is handled in .save()."""
        raise NotImplementedError("This serializer is for password change (update logic only).")

    def update(self, instance, validated_data):
        """Not used; logic is handled in .save()."""
        raise NotImplementedError("This serializer is for password change (update logic only).")

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect current password.")
        return value

    def validate(self, attrs):
        """
        Validates the new password matching and complexity.
        Note: Renamed parameter from 'data' to 'attrs' to resolve W0237 warning.
        """
        new_password = attrs.get('new_password')
        new_password_confirm = attrs.get('new_password_confirm')
        user = self.context['request'].user

        if new_password != new_password_confirm:
            raise serializers.ValidationError(
                {"new_password_confirm": "New passwords do not match."}
            )

        try:
            validate_password(new_password, user)
        except ValidationError as e:
            raise serializers.ValidationError({"new_password": list(e)})

        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
