from rest_framework import serializers
from api.models import Group, Roll, User, Character

class GroupSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    class Meta:
        model = Group
        fields = ['id', 'group_name']


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