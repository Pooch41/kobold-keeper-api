from rest_framework import viewsets, permissions
from rest_framework.mixins import CreateModelMixin
from rest_framework.exceptions import PermissionDenied  # Import this for clarity

from .serializers import GroupSerializer, CharacterSerializer, RollSerializer, UserSerializer
from .models import Group, Character, Roll, User


class GroupViewSet(viewsets.ModelViewSet):
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Group.objects.filter(owner=user).order_by('group_name')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class CharacterViewSet(viewsets.ModelViewSet):
    serializer_class = CharacterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Character.objects.filter(group__owner=user).order_by('character_name')

    def perform_create(self, serializer):
        group_instance = serializer.validated_data.get('group')
        if group_instance.owner != self.request.user:
            raise PermissionDenied("You don't have permission to create characters in this group.")

        serializer.save(user=self.request.user)


class RollViewSet(viewsets.ModelViewSet):
    serializer_class = RollSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Roll.objects.filter(character__group__owner=user).order_by('-id')

    def perform_create(self, serializer):
        character_instance = serializer.validated_data.get('character')
        if character_instance.group.owner != self.request.user:
            raise PermissionDenied("You do not have permission to record a roll for this character.")

        serializer.save(user=self.request.user, group=character_instance.group)


class UserRegistrationViewSet(CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
