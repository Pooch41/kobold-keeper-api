from rest_framework import viewsets, permissions
from rest_framework.mixins import CreateModelMixin

from .serializers import GroupSerializer, CharacterSerializer, RollSerializer, UserSerializer
from .models import Group, Character, Roll, User

class GroupViewSet(viewsets.ModelViewSet):
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Group.objects.filter(owner=user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class CharacterViewSet(viewsets.ModelViewSet):
    serializer_class = CharacterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Character.objects.filter(group__owner=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class RollViewSet(viewsets.ModelViewSet):
    serializer_class = RollSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Roll.objects.filter(group__owner=user).order_by('-id')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserRegistrationViewSet(CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

