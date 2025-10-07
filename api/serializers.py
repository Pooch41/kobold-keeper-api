from rest_framework import serializers
from api.models import Group, Roll, User

class GroupSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    class Meta:
        model = Group
        fields = ['id', 'group_name']