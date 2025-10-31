"""
Service and utility classes for calculating comprehensive luck and rolling
statistics from the Roll data model.

This module provides filtering capabilities (RollQueryFilter) and the core
analytics engine (LuckAnalyticsService) to derive metrics based on both the
final modified roll value and the raw, unmodified dice components stored
in the JSON field.

Classes:
    RollQueryFilter: Provides static methods to build optimized QuerySets
                     for filtering Roll data (e.g., by character, by group).
    LuckAnalyticsService: A service that consumes a Roll QuerySet and
                          provides methods to calculate:
                          - General modified roll statistics (min, max, avg).
                          - Raw (unmodified) dice averages.
                          - Luck indices (weighted) per die-type and overall.
                          - Character-based luck rankings.
"""


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
        # OPTIMIZATION: Use select_related to pre-fetch character data for the service
        return Roll.objects.filter(character__id=character_id).select_related('character', 'group')

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
        # OPTIMIZATION: Use select_related to pre-fetch character data for the service
        return Roll.objects.filter(group__id=group_id).select_related('character', 'group')

    @staticmethod
    def for_global():
        """
        Returns a QuerySet containing all Roll objects (global scope).

        :return: QuerySet of all Roll objects.
        """
        # OPTIMIZATION: Use select_related to pre-fetch character data for the service
        return Roll.objects.all().select_related('character', 'group')


class LuckAnalyticsService:
    """
    A service class dedicated to calculating various luck and rolling statistics
    from a given queryset of Roll objects.

    It handles both simple database aggregations (for modified roll values) and
    complex Python-based JSON parsing (for raw dice rolls).
    """

    # Dictionary mapping die size to its theoretical average value: (Max value + 1) / 2
    THEORETICAL_AVERAGES = {
        4: 2.5, 6: 3.5, 8: 4.5, 10: 5.5, 12: 6.5, 20: 10.5, 100: 50.5
    }

    # Regex to extract the die size from a formula string (e.g., 'd20' from '2d20kh1+5')
    DICE_TYPE_PATTERN = re.compile(r'd(\d+)')

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

    def _get_character_roll_data_aggregated(self) -> Dict[int, Dict[str, Any]]:
        """
        Private helper that aggregates raw dice sums, theoretical sums, and roll counts
        for every character found in the current queryset.

        This logic was extracted from the original get_luckiest_roller_by_delta method.

        :return: A dictionary keyed by character ID, holding raw aggregation totals.
        """
        character_metrics: Dict[int, Dict[str, Any]] = {}

        for roll in self.roll_queryset:
            char_id = roll.character_id
            char_name = roll.character.character_name if roll.character else 'Unknown Character'

            if not char_id or char_name == 'Unknown Character':
                continue

            raw_dice_sum = 0.0
            theoretical_sum = 0.0
            total_dice_count = 0

            try:
                raw_rolls_components = roll.raw_dice_rolls
                if isinstance(raw_rolls_components, str):
                    raw_rolls_components = json.loads(raw_rolls_components)

                if not isinstance(raw_rolls_components, list):
                    continue

                for component in raw_rolls_components:
                    if component.get('component_type') == 'dice':
                        formula = component.get('formula', '').lower()
                        rolls_list = component.get('rolls', [])

                        match = self.DICE_TYPE_PATTERN.search(formula)
                        if not match or not rolls_list:
                            continue

                        die_size = int(match.group(1))

                        component_raw_sum = sum(rolls_list)
                        raw_dice_sum += component_raw_sum

                        num_dice = len(rolls_list)
                        theoretical_avg = self.THEORETICAL_AVERAGES.get(die_size, 0.0)
                        theoretical_sum += num_dice * theoretical_avg

                        total_dice_count += num_dice

            except (json.JSONDecodeError, Exception):
                # Print to console for debugging, but continue processing rolls
                continue

            if char_id not in character_metrics:
                character_metrics[char_id] = {
                    'character_name': char_name,
                    'total_raw_sum': 0.0,
                    'total_theoretical_sum': 0.0,
                    'total_rolls': 0,
                    'total_raw_dice_count': 0,
                }

            metrics = character_metrics[char_id]
            metrics['total_raw_sum'] += raw_dice_sum
            metrics['total_theoretical_sum'] += theoretical_sum
            metrics['total_rolls'] += 1
            metrics['total_raw_dice_count'] += total_dice_count

        return character_metrics

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

        It also calculates a per-die 'luck_index' (average / theoretical average).
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

            luck_index = avg / theoretical_avg if theoretical_avg > 0 else 0.0

            results[die_label] = {
                "average_roll": round(avg, 2),
                "theoretical_average": round(theoretical_avg, 2),
                "roll_count": data['count'],
                "sum": data['sum'],
                "luck_index": round(luck_index, 4)
            }

        return dict(sorted(results.items(), key=lambda item: int(item[0][1:])))

    def calculate_luck_index(self) -> Dict[str, Any]:
        """
        Calculates the overall 'luck_index' for the character/group by taking a
        weighted average of the luck index for each die type rolled.

        The weight is the number of times that specific die type was rolled.

        :return: A dictionary containing the overall 'luck_index' and the
                 'total_raw_dice_count' for the entire analysis period.
        """
        die_averages = self.calculate_dice_type_averages()

        if not die_averages:
            return {"luck_index": 0.0, "total_raw_dice_count": 0}

        total_weighted_luck_sum = 0.0
        total_raw_dice_count = 0

        for die_type_data in die_averages.values():
            luck_index = die_type_data.get('luck_index', 0.0)
            roll_count = die_type_data.get('roll_count', 0)

            total_weighted_luck_sum += (luck_index * roll_count)
            total_raw_dice_count += roll_count

        if total_raw_dice_count > 0:
            overall_luck_index = total_weighted_luck_sum / total_raw_dice_count
        else:
            overall_luck_index = 0.0

        return {
            "luck_index": round(overall_luck_index, 4),
            "total_raw_dice_count": total_raw_dice_count
        }

    def calculate_luck_delta_by_character(self) -> List[Dict[str, Any]]:
        """
        Calculates the luck delta and ratio for all characters in the queryset.
        Returns a list of dictionaries, one for each character. This is used
        as a source for ranking or for display of all character luck metrics.

        :return: A list of character luck metrics (List[Dict]).
        """
        character_metrics = self._get_character_roll_data_aggregated()

        results = []
        for char_id, metrics in character_metrics.items():
            actual = metrics['total_raw_sum']
            theoretical = metrics['total_theoretical_sum']
            total_dice = metrics['total_raw_dice_count']

            if total_dice > 0:
                luck_delta = actual - theoretical

                luck_delta_ratio = luck_delta / theoretical if theoretical > 0 else 0.0
            else:
                luck_delta = 0.0
                luck_delta_ratio = 0.0

            results.append({
                'character_id': char_id,
                'character_name': metrics['character_name'],
                'total_rolls': metrics['total_rolls'],
                'total_raw_dice_count': total_dice,
                'total_raw_sum': round(actual, 2),
                'total_theoretical_sum': round(theoretical, 2),
                'luck_delta': round(luck_delta, 4),
                'luck_delta_ratio': round(luck_delta_ratio, 4),
            })

        return results

    def get_luckiest_roller_by_delta(self, min_rolls: int = 1) -> Dict[str, Any]:
        """
        Identifies the character with the highest 'luck delta ratio', ensuring they
        meet a minimum threshold of dice rolled for statistical significance.

        The luck delta ratio is calculated as:
        (Total Actual Raw Dice Sum - Total Theoretical Sum) / Total Theoretical Sum

        :param min_rolls: The minimum number of individual dice that must have been
                          rolled by a character to be considered. Defaults to 1.
        :return: A dictionary containing the luckiest character's details and ratio,
                 or an empty dictionary if no rolls are present or no character meets the threshold.
        """
        all_luck_data = self.calculate_luck_delta_by_character()

        filtered_data = [
            data for data in all_luck_data
            if data['total_raw_dice_count'] >= min_rolls and data['total_theoretical_sum'] > 0
        ]

        if not filtered_data:
            return {}

        luckiest_roller = max(filtered_data, key=lambda x: x['luck_delta_ratio'])

        return luckiest_roller
