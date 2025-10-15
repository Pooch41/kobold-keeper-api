from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from django.db import transaction
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password

from .models import User, Group, Character, Roll, RecoveryKey
from .utils import generate_key
from .dice_roller import DiceRoller, InvalidRollFormula

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True,
                                     required=True,
                                     style={'input_type': 'password'}
                                     )

    raw_recovery_key = serializers.CharField(max_length=10, read_only=True)

    class Meta:
        model = User
        fields = ['user_name', 'password', 'raw_recovery_key']

    def create(self, validated_data):
        with transaction.atomic():
            password = validated_data.pop('password')
            raw_key = generate_key()
            user = User.objects.create_user(**validated_data, password=password)
            recovery_key_instance = RecoveryKey.objects.create(user=user)
            recovery_key_instance.set_key(raw_key)
            recovery_key_instance.save()
            user.raw_recovery_key = raw_key

            return user

class GroupSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())

    characters = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='character_name'
    )

    class Meta:
        model = Group
        fields = ['id',
                  'group_name',
                  'owner',
                  'characters',
                  '_group_raw_avg',
                  '_group_crit_fail_count',
                  '_group_crit_success_count',
                  '_group_mod_avg',
                  '_group_mod_min',
                  '_group_mod_max',
                  ]
        read_only_fields = ['id',
                  'owner',
                  '_group_raw_avg',
                  '_group_crit_fail_count',
                  '_group_crit_success_count',
                  '_group_mod_avg',
                  '_group_mod_min',
                  '_group_mod_max',
                  ]


class CharacterSerializer(serializers.ModelSerializer):
    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all())

    class Meta:
        model = Character
        fields = [
            'id',
            'user',
            'character_name',
            'character_note',
            '_raw_avg',
            '_crit_fail_count',
            '_crit_success_count',
            '_mod_avg',
            '_mod_min',
            '_mod_max',
            'is_npc',
            'group'
        ]
        read_only_fields = ['id',
                            'user',
                            '_raw_avg',
                            '_crit_fail_count',
                            '_crit_success_count',
                            '_mod_avg',
                            '_mod_min',
                            '_mod_max']

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

    roll_formula = serializers.CharField(
        max_length=50,
        write_only=True,
        help_text="e.g., '2d6+5' or '1d20-1'")

    roll_input = serializers.CharField(read_only=True)
    roll_value = serializers.IntegerField(read_only=True)
    raw_dice_rolls = serializers.JSONField(read_only=True)

    class Meta:
        model = Roll
        fields = [
            'id', 'character', 'roll_formula',
            # Output fields:
            'roll_input', 'roll_value', 'raw_dice_rolls',
            'user', 'group', 'timestamp'
        ]
        read_only_fields = ['id', 'user', 'group', 'timestamp']

    def validate_roll_formula(self, roll_formula):
        try:
            DiceRoller.calculate_roll(roll_formula)
        except InvalidRollFormula as e:
            raise serializers.ValidationError(str(e))
        return roll_formula

    def create(self, validated_data):
        roll_formula = validated_data.pop('roll_formula')
        character_instance = validated_data.pop('character')
        group_instance=character_instance.group

        roll_results = DiceRoller.calculate_roll(roll_formula)

        validated_data['roll_input'] = roll_formula
        validated_data['roll_value'] = roll_results['final_result']
        validated_data['raw_dice_rolls'] = roll_results['outcomes']

        validated_data['character'] = character_instance
        validated_data['group'] = group_instance

        return Roll.objects.create(**validated_data)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
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
    username = serializers.CharField(required=True)
    recovery_key = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)

    def validate(self, data):
        username = data.get('username')
        recovery_key = data.get('recovery_key')
        try:
            user = User.objects.get(**{User.USERNAME_FIELD: username})
        except User.DoesNotExist:
            raise ValidationError("Authentication failed. Invalid username or recovery key.")
        try:
            recovery_instance = RecoveryKey.objects.get(user=user)
        except RecoveryKey.DoesNotExist:
            raise ValidationError("Authentication failed. Invalid username or recovery key.")

        if not check_password(recovery_key, recovery_instance.recovery_key_hash):
            raise ValidationError("Authentication failed. Invalid username or recovery key.")

        self.user = user
        return data

    def save(self):

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

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect current password.")
        return value

    def validate(self, data):
        new_password = data.get('new_password')
        new_password_confirm = data.get('new_password_confirm')
        user = self.context['request'].user

        if new_password != new_password_confirm:
            raise serializers.ValidationError(
                {"new_password_confirm": "New passwords do not match."}
            )

        try:
            validate_password(new_password, user)
        except ValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})

        return data

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
