import json
import re
from typing import Dict, Any, List

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

    def _get_all_dice_components(self) -> List[Dict[str, Any]]:
        """
        Fetches all raw_dice_rolls data, handles JSONField parsing variability (string vs. object),
        and flattens the result into a list of individual dice component dictionaries,
        filtering only for components where 'component_type' is 'dice'.
        """
        all_rolls_data = self.roll_queryset.values_list('raw_dice_rolls', flat=True)
        all_dice_components = []

        for roll_data in all_rolls_data:
            parsed_roll = None

            if roll_data is None:
                continue

            if isinstance(roll_data, str):
                try:
                    parsed_roll = json.loads(roll_data)
                except json.JSONDecodeError as e:
                    print(f"Error parsing raw_dice_rolls string: {e}")
                    continue
            else:
                parsed_roll = roll_data

            if isinstance(parsed_roll, list):
                for component in parsed_roll:
                    if component.get("component_type") == "dice":
                        all_dice_components.append(component)

        return all_dice_components

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
        Calculates statistics based on the raw, unmodified dice rolls across ALL dice.
        It sums all individual die rolls and counts how many dice were thrown.

        :return: A dictionary containing the 'avg_raw_roll' and 'total_raw_dice_count'.
        """

        all_dice_components = self._get_all_dice_components()
        if not all_dice_components:
            return {"avg_raw_roll": 0.0, "total_raw_dice_count": 0}

        total_raw_sum = 0
        total_raw_dice_count = 0

        for component in all_dice_components:
            individual_rolls = component.get("rolls", [])
            total_raw_sum += sum(individual_rolls)
            total_raw_dice_count += len(individual_rolls)

        avg_raw_roll = total_raw_sum / total_raw_dice_count if total_raw_dice_count > 0 else 0.0

        return {
            "avg_raw_roll": round(avg_raw_roll, 2),
            "total_raw_dice_count": total_raw_dice_count
        }

    def calculate_dice_type_averages(self) -> Dict[str, Any]:
        """
        Calculates the average roll value and count for each specific die type (d4, d6, d20, etc.)
        by parsing the 'formula' field using regex.
        """
        all_dice_components = self._get_all_dice_components()

        if not all_dice_components:
            return {}

        DICE_TYPE_PATTERN = re.compile(r'd(\d+)')
        type_tracker = {}

        for component in all_dice_components:
            formula = component.get('formula', '')
            individual_rolls = component.get('rolls', [])

            match = DICE_TYPE_PATTERN.search(formula)

            if match and individual_rolls:
                d_type_str = match.group(1)

                try:
                    d_type = int(d_type_str)
                except ValueError:
                    continue

                if d_type not in type_tracker:
                    type_tracker[d_type] = {'sum': 0, 'count': 0}

                type_tracker[d_type]['sum'] += sum(individual_rolls)
                type_tracker[d_type]['count'] += len(individual_rolls)

        results = {}
        for d_type, data in type_tracker.items():
            die_label = f"d{d_type}"
            avg = data['sum'] / data['count'] if data['count'] > 0 else 0.0

            theoretical_avg = (d_type + 1) / 2

            results[die_label] = {
                "average_roll": round(avg, 2),
                "theoretical_average": round(theoretical_avg, 2),
                "roll_count": data['count'],
                "sum": data['sum']
            }

        return dict(sorted(results.items(), key=lambda item: int(item[0][1:])))
