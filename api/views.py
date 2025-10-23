from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, NotFound, APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .dice_reader import LuckAnalyticsService, RollQueryFilter
from .models import Group, Character, Roll
from .serializers import GroupSerializer, CharacterSerializer, RollSerializer

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
        return Roll.objects.filter(character__group__owner=self.request.user).order_by('-id')

    def perform_create(self, serializer):
        """
        Validates that the character the roll is being created for is in a group
        owned by the current user.
        """
        character_instance = serializer.validated_data.get('character')
        if character_instance.group.owner != self.request.user:
            raise PermissionDenied("You do not have permission to record a roll for this character.")
        serializer.save()


class LuckAnalyticsView(APIView):
    """
    API endpoint for retrieving luck and rolling statistics.
    ...
    """

    permission_classes = [IsAuthenticated]

    def _get_scoped_queryset_and_name(self, user, character_id, group_id) -> tuple[QuerySet[Roll], str]:
        """
        Helper method to determine the scope of the roll query.
        """
        if character_id:
            if not Character.objects.filter(id=character_id, user=user).exists():
                raise NotFound(detail="Character not found or not owned by the user.")
            queryset = RollQueryFilter.for_character(character_id)
            scope_name = f"Character: {character_id}"
            return queryset, scope_name

        if group_id:
            if not Group.objects.filter(id=group_id, owner=user).exists():
                raise NotFound(detail="Group not found or not owned by the user.")
            queryset = RollQueryFilter.for_group(group_id)
            scope_name = f"Group: {group_id}"
            return queryset, scope_name

        queryset = Roll.objects.filter(character__user=user)
        return queryset, "Global"

    def _get_metrics_response_data(self, roll_queryset: QuerySet[Roll], scope: str) -> dict:
        """
        Calculates all required analytics using the service, handles errors,
        and formats the final response dictionary. (Resolves R0914)
        """
        analytics_service = LuckAnalyticsService(roll_queryset)

        try:
            modified_metrics = analytics_service.get_modified_roll_metrics()
            raw_metrics = analytics_service.calculate_raw_dice_averages()
            dice_type_breakdown = analytics_service.calculate_dice_type_averages()

        except Exception as e:
            raise APIException(
                detail=f"An error occurred during calculation: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) from e

        total_rolls_count = modified_metrics.pop("total_rolls")

        return {
            "scope": scope,
            "total_rolls": total_rolls_count,
            "metrics": {
                "modified": modified_metrics,
                "raw_dice": raw_metrics,
                "dice_type_breakdown": dice_type_breakdown,
            }
        }

    def get(self, request, *args, **kwargs):
        """
        Handles the GET request by determining the scope and running the analysis.
        """
        user = request.user
        character_id = request.query_params.get('character_id')
        group_id = request.query_params.get('group_id')

        try:
            roll_queryset, scope = self._get_scoped_queryset_and_name(
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
                "total_rolls": 0,
                "metrics": {}
            }, status=status.HTTP_200_OK)

        response_data = self._get_metrics_response_data(roll_queryset, scope)

        return Response(response_data, status=status.HTTP_200_OK)
