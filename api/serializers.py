from rest_framework import serializers
from django.db import transaction
from .models import User, Group, Character, Roll, RecoveryKey
from .utils import generate_key


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
