from rest_framework import serializers

from api.models import Group, Roll, User, Character
from api.dice_roller import DiceRoller, InvalidRollFormula

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'user_name', 'password']
        read_only_fields = ['id']

    def create(self, validated_data):
        user = User.objects.create_user(
            user_name=validated_data['user_name'],
            password=validated_data['password']
        )
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
        fields = ['id', 'group_name', 'owner', 'characters',
                  '_group_raw_avg', '_group_mod_avg']
        read_only_fields = ['id', 'owner', '_group_raw_avg', '_group_mod_avg']


class CharacterSerializer(serializers.ModelSerializer):
    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all())

    class Meta:
        model = Character
        fields = [
            'id',
            'character_name',
            'character_note',
            'is_npc',
            'group'
        ]
        read_only_fields = ['id']

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
