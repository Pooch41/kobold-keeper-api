"""
API Views for the Kobold Keeper application.

This module contains the ViewSets (for CRUD operations on Groups, Characters, and Rolls)
and the specific APIViews (for Luck Analytics) that serve the application's core logic.
All views enforce object-level permissions to ensure users only access their own data.
"""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, NotFound, APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django.shortcuts import get_object_or_404

from .dice_reader import LuckAnalyticsService
from .models import Group, Character, Roll
from .serializers import GroupSerializer, CharacterSerializer, RollSerializer

User = get_user_model()


def _get_analytics_queryset_and_name(user: User, character_id: str = None, group_id: str = None):
    """
    Safely retrieves a Roll QuerySet for analytics, enforcing that
    the requested character or group belongs to the authenticated user.

    Uses get_object_or_404 to ensure that if a character/group
    is specified, it belongs to the user, preventing a BOLA vulnerability.
    """


    user_owned_rolls = Roll.objects.filter(character__user=user)

    if character_id:
        character = get_object_or_404(Character.objects.filter(user=user), pk=character_id)
        queryset = user_owned_rolls.filter(character=character)
        scope = f"Character: {character.character_name}"
    elif group_id:
        group = get_object_or_404(Group.objects.filter(owner=user), pk=group_id)
        queryset = user_owned_rolls.filter(group=group)
        scope = f"Group: {group.group_name}"
    else:
        queryset = user_owned_rolls
        scope = "User's Entire Collection"

    return queryset, scope


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
        Ensures users can only view and manage Characters they own.
        """
        return Character.objects.filter(user=self.request.user).order_by('character_name')

    def perform_create(self, serializer):
        """
        Injects the current authenticated user as the `user` during creation.
        """
        serializer.save(user=self.request.user)


class RollViewSet(ModelViewSet):
    """
    ViewSet for managing Roll resources.
    Endpoint: /rolls/
    """
    serializer_class = RollSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Ensures users only see rolls associated with their characters.

        PERFORMANCE FIX: Added select_related to fix N+1 Query Problem.
        This fetches the character and group data in one query for serialization.
        """
        return Roll.objects.filter(
            character__user=self.request.user
        ).select_related('character', 'group').order_by('-rolled_at')

    def perform_create(self, serializer):
        """
        Injects the character's owner (current user) during roll creation and
        ensures the character belongs to the user.
        """
        character = serializer.validated_data['character']
        if character.user != self.request.user:
            raise PermissionDenied("You can only create rolls for your own characters.")

        serializer.save()


class LuckAnalyticsView(APIView):
    """
    API endpoint for retrieving general roll statistics (min, max, average)
    for a given scope (user, character, or group).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Calculates and returns general statistics (Min/Max/Avg).
        """
        user = request.user
        character_id = request.query_params.get('character_id')
        group_id = request.query_params.get('group_id')

        try:
            roll_queryset, scope = _get_analytics_queryset_and_name(
                user, character_id, group_id
            )
        except NotFound as e:
            raise e
        except Exception as e:
            raise APIException(f"Error determining query scope: {e}") from e


        if not roll_queryset.exists():
            return Response({
                "scope": scope,
                "detail": "No roll data found for this scope.",
                "statistics": {}
            }, status=status.HTTP_200_OK)

        analytics_service = LuckAnalyticsService(roll_queryset)
        stats = analytics_service.get_modified_roll_metrics()

        return Response({
            "scope": scope,
            "statistics": stats
        }, status=status.HTTP_200_OK)


class LuckiestRollerView(APIView):
    """
    API endpoint for retrieving the single character with the highest
    luck delta ratio (Actual vs. Theoretical Sum) for a given scope.
    This is intentionally separated from general luck statistics.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Calculates and returns the character with the highest luck delta ratio.
        """
        user = request.user
        character_id = request.query_params.get('character_id')
        group_id = request.query_params.get('group_id')

        try:
            roll_queryset, scope = _get_analytics_queryset_and_name(
                user, character_id, group_id
            )
        except NotFound as e:
            raise e
        except Exception as e:
            raise APIException(f"Error determining query scope: {e}") from e

        if not roll_queryset.exists():
            return Response({
                "scope": scope,
                "detail": "No roll data found for this scope.",
                "luckiest_roller": {}
            }, status=status.HTTP_200_OK)

        analytics_service = LuckAnalyticsService(roll_queryset)
        luckiest_roller_data = analytics_service.get_luckiest_roller_by_delta()

        return Response({
            "scope": scope,
            "luckiest_roller": luckiest_roller_data
        }, status=status.HTTP_200_OK)
