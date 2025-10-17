from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import Group, Character, Roll
from .serializers import GroupSerializer, CharacterSerializer, RollSerializer, PasswordResetWithKeySerializer

User = get_user_model()


class GroupViewSet(ModelViewSet):
    """
    ViewSet for managing Group (Campaign) resources.
    Endpoint: /groups/
    """
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Ensures users can only view and manage Groups they own.
        Filtering by the authenticated user (`self.request.user`).
        """
        return Group.objects.filter(owner=self.request.user).order_by('group_name')

    def perform_create(self, serializer):
        """
        Injects the current authenticated user as the `owner` during creation.
        """
        serializer.save(owner=self.request.user)


class CharacterViewSet(ModelViewSet):
    """
    ViewSet for managing Character resources.
    Endpoint: /characters/
    """
    serializer_class = CharacterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Ensures users can only view characters belonging to Groups they own.
        This prevents viewing characters in shared groups or groups owned by others.
        """
        return Character.objects.filter(group__owner=self.request.user).order_by('character_name')

    def perform_create(self, serializer):
        """
        Validates ownership of the selected group and sets the character's owner.
        """
        group_instance = serializer.validated_data.get('group')
        if group_instance.owner != self.request.user:
            raise PermissionDenied("You don't have permission to create characters in this group.")
        serializer.save(user=self.request.user)


class RollViewSet(ModelViewSet):
    """
    ViewSet for managing Roll history records.
    Endpoint: /rolls/
    """
    serializer_class = RollSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Ensures users can only view rolls associated with groups they own.
        Roll -> Character -> Group -> Owner
        """
        return Roll.objects.filter(character__group__owner=self.request.user).order_by('-roll_id')

    def perform_create(self, serializer):
        """
        Validates that the character the roll is being created for is in a group
        owned by the current user.
        """
        character_instance = serializer.validated_data.get('character')
        if character_instance.group.owner != self.request.user:
            raise PermissionDenied("You do not have permission to record a roll for this character.")
        serializer.save()


class PasswordResetWithKeyView(APIView):
    """
    Custom APIView to handle password reset using a one-time recovery key.
    Endpoint: /auth/password/reset/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Processes the POST request containing username, recovery_key, and new_password.
        """
        serializer = PasswordResetWithKeySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Password has been successfully reset."},
            status=status.HTTP_200_OK
        )
