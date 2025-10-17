import json
from typing import Dict, Any

from django.db.models import Avg, Count, Max, Min

from .models import Roll


class RollQueryFilter:
    """
    A utility class containing static methods to build Django QuerySets for the Roll model.

    It allows filtering rolls based on the context: a specific character, a group,
    or all global rolls. This separation of concerns ensures clean, reusable query
    logic for the analytics service.
    """

    @staticmethod
    def for_character(character_id):
        """
        Returns a QuerySet of Rolls associated with a specific character.

        :param character_id: The ID of the Character to filter by.
        :raises ValueError: If the character_id is not provided.
        :return: QuerySet of Roll objects.
        """
        if not character_id:
            raise ValueError("Character object is required for character-specific rolls.")
        return Roll.objects.filter(character__id=character_id)

    @staticmethod
    def for_group(group_id):
        """
        Returns a QuerySet of Rolls associated with a specific group.

        :param group_id: The ID of the Group to filter by.
        :raises ValueError: If the group_id is not provided.
        :return: QuerySet of Roll objects.
        """
        if not group_id:
            raise ValueError("Group ID is required for group-specific rolls.")
        return Roll.objects.filter(group__id=group_id)

    @staticmethod
    def for_global():
        """
        Returns a QuerySet containing all Roll objects (global scope).

        :return: QuerySet of all Roll objects.
        """
        return Roll.objects.all()


class LuckAnalyticsService:
    """
    A service class dedicated to calculating various luck and rolling statistics
    from a given queryset of Roll objects.

    It handles both simple database aggregations (for modified roll values) and
    complex Python-based JSON parsing (for raw dice rolls).
    """

    def __init__(self, roll_queryset):
        self.roll_queryset = roll_queryset

    def get_modified_roll_metrics(self) -> Dict[str, Any]:
        """
        Calculates simple aggregation metrics (Avg, Min, Max, Count) based on the
        final modified roll value (`roll_value`), which includes modifiers.

        These are calculated efficiently at the database level using Django ORM aggregation.

        :return: A dictionary containing 'total_rolls', 'avg_modified_roll',
                 'min_modified_roll', and 'max_modified_roll'.
        """
        if not self.roll_queryset.exists():
            return {"total_rolls": 0}

        aggregation = self.roll_queryset.aggregate(
            total_rolls=Count('id'),
            avg_modified_roll=Avg('roll_value'),
            min_modified_roll=Min('roll_value'),
            max_modified_roll=Max('roll_value'),
        )

        return {
            "total_rolls": aggregation['total_rolls'],
            "avg_modified_roll": round(aggregation['avg_modified_roll'], 2),
            "min_modified_roll": aggregation['min_modified_roll'],
            "max_modified_roll": aggregation['max_modified_roll'],
        }

    def calculate_raw_dice_averages(self) -> Dict[str, Any]:
        """
        Calculates statistics based on the raw, unmodified dice rolls stored as JSON
        in the `raw_dice_rolls` field.

        This requires loading and parsing the JSON data in Python, summing all individual
        dice results across all rolls, and calculating a true average of the raw dice.

        :return: A dictionary containing the 'avg_raw_roll' and 'total_raw_dice_count'.
        """
        all_rolls_data = self.roll_queryset.values_list('raw_dice_rolls', flat=True)

        if not all_rolls_data:
            return {"avg_raw_roll": 0.0, "total_raw_dice_count": 0}

        total_raw_sum = 0
        total_raw_dice_count = 0

        for raw_roll_json in all_rolls_data:
            try:
                parsed_roll_list = json.loads(raw_roll_json)
                for die_group in parsed_roll_list:
                    individual_rolls = die_group.get('rolls', [])
                    total_raw_sum += sum(individual_rolls)
                    total_raw_dice_count += len(individual_rolls)

            except (json.JSONDecodeError, TypeError, AttributeError) as e:
                print(f"Error parsing raw_dice_rolls: {e} for data: {raw_roll_json}")
                continue

        avg_raw_roll = total_raw_sum / total_raw_dice_count if total_raw_dice_count > 0 else 0.0

        return {
            "avg_raw_roll": round(avg_raw_roll, 2),
            "total_raw_dice_count": total_raw_dice_count
        }
