from rest_framework import viewsets, permissions
from rest_framework.mixins import CreateModelMixin
from rest_framework.exceptions import PermissionDenied

from .serializers import GroupSerializer, CharacterSerializer, RollSerializer, UserSerializer
from .models import Group, Character, Roll, User


class GroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Group (Campaign) resources.
    - Provides CRUD operations for Groups.
    - Enforces ownership: Users can only see and modify Groups they own.
    """
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filters the queryset to ensure users can only access their own Groups.
        This is the primary security filter for read actions (list, retrieve).
        """
        user = self.request.user
        return Group.objects.filter(owner=user).order_by('group_name')

    def perform_create(self, serializer):
        """
        Automatically sets the `owner` field to the currently authenticated user
        when a new Group object is created.
        """
        serializer.save(owner=self.request.user)


class CharacterViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Character resources.
    - Provides CRUD operations for Characters.
    - Enforces that Characters must belong to a Group owned by the user.
    """
    serializer_class = CharacterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filters characters: only show characters whose associated Group is owned
        by the current authenticated user.
        """
        user = self.request.user
        return Character.objects.filter(group__owner=user).order_by('character_name')

    def perform_create(self, serializer):
        """
        Security Check: Ensures the user owns the Group specified in the request
        before creating the Character.
        """
        group_instance = serializer.validated_data.get('group')
        if group_instance.owner != self.request.user:
            raise PermissionDenied("You don't have permission to create characters in this group.")

        serializer.save(user=self.request.user)


class RollViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Roll history records.
    - Primarily used for creation and viewing history.
    - Enforces that Rolls must be associated with a Character whose Group is owned by the user.
    """
    serializer_class = RollSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filters rolls: only show rolls associated with characters in groups owned
        by the current authenticated user.
        """
        user = self.request.user
        return Roll.objects.filter(character__group__owner=user).order_by('-id')

    def perform_create(self, serializer):
        """
        Security Check: Ensures the user owns the Group associated with the Character
        before recording a new Roll.
        """
        character_instance = serializer.validated_data.get('character')
        if character_instance.group.owner != self.request.user:
            raise PermissionDenied("You do not have permission to record a roll for this character.")

        serializer.save(user=self.request.user, group=character_instance.group)


class UserRegistrationViewSet(CreateModelMixin, viewsets.GenericViewSet):
    """
    A minimal ViewSet used only for handling user registration (CREATE action).
    - Endpoint: /auth/register/ (assuming URL routing is set up this way)
    - Uses a serializer designed for user creation and key generation.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]