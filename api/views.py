from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model

from .models import Group, Character, Roll
from .serializers import GroupSerializer, CharacterSerializer, RollSerializer, PasswordResetWithKeySerializer

User = get_user_model()

class GroupViewSet(ModelViewSet):
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Group.objects.filter(owner=self.request.user).order_by('group_name')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class CharacterViewSet(ModelViewSet):
    serializer_class = CharacterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Character.objects.filter(group__owner=self.request.user).order_by('character_name')

    def perform_create(self, serializer):
        group_instance = serializer.validated_data.get('group')
        if group_instance.owner != self.request.user:
            raise PermissionDenied("You don't have permission to create characters in this group.")
        serializer.save(user=self.request.user)


class RollViewSet(ModelViewSet):
    serializer_class = RollSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Roll.objects.filter(character__group__owner=self.request.user).order_by('-roll_id')

    def perform_create(self, serializer):
        character_instance = serializer.validated_data.get('character')
        if character_instance.group.owner != self.request.user:
            raise PermissionDenied("You do not have permission to record a roll for this character.")
        serializer.save()


class PasswordResetWithKeyView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = PasswordResetWithKeySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Password has been successfully reset."},
            status=status.HTTP_200_OK
        )