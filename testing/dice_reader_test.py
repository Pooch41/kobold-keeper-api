import json
from datetime import timedelta

import pytest
from django.utils import timezone

from api.dice_reader import LuckAnalyticsService, RollQueryFilter
from api.models import Roll, Character, Group, User


@pytest.fixture
def setup_rolls(db):
    """
    Sets up a complex dataset of rolls for various filter and calculation tests.

    This fixture uses the realistic JSON structure returned by the DiceRoller utility
    to accurately test the parsing logic in LuckAnalyticsService.
    """
    User.objects.create_user(username='global_user', password='password1')
    user_char = User.objects.create_user(username='character_user', password='password2')
    user_group = User.objects.create_user(username='group_user', password='password3')
    group_campaign = Group.objects.create(group_name='A Shared Campaign', owner=user_group)
    Group.objects.create(group_name='Another Campaign', owner=user_char)

    char_pc = Character.objects.create(
        character_name='Amaryllis the Rogue',
        user=user_char,
        group=group_campaign,
        character_note='Main Player Character'
    )
    char_npc = Character.objects.create(
        character_name='Goblin Grunt',
        user=user_group,
        group=group_campaign,
        is_npc=True
    )

    # Roll 1: 1d20 (Result 5)
    Roll.objects.create(
        character=char_pc, group=group_campaign, roll_input='1d20', roll_value=5,
        raw_dice_rolls=json.dumps([
            {"rolls": [5], "total": 5, "formula": "1d20", "component_type": "dice"}
        ]),
        rolled_at=timezone.now() - timedelta(hours=5)
    )

    # Roll 2: 1d20+5 (Result 25) - Natural 20
    Roll.objects.create(
        character=char_pc, group=group_campaign, roll_input='1d20+5', roll_value=25,
        raw_dice_rolls=json.dumps([
            {"rolls": [20], "total": 20, "formula": "1d20", "component_type": "dice"},
            {"value": 5, "formula": "5", "component_type": "modifier"}
        ]),
        rolled_at=timezone.now() - timedelta(hours=4)
    )

    # Roll 3: 3d6 (Result 10)
    Roll.objects.create(
        character=char_pc, group=group_campaign, roll_input='3d6', roll_value=10,
        raw_dice_rolls=json.dumps([
            {"rolls": [3, 4, 3], "total": 10, "formula": "3d6", "component_type": "dice"}
        ]),
        rolled_at=timezone.now() - timedelta(hours=3)
    )

    # Roll 4: 1d20 (Result 20)
    Roll.objects.create(
        character=char_pc, group=group_campaign, roll_input='1d20', roll_value=20,
        raw_dice_rolls=json.dumps([
            {"rolls": [20], "total": 20, "formula": "1d20", "component_type": "dice"}
        ]),
        rolled_at=timezone.now() - timedelta(hours=2)
    )

    # Roll 5: 1d20-1 (Result 2) - Low roll
    Roll.objects.create(
        character=char_npc, group=group_campaign, roll_input='1d20-1', roll_value=2,
        raw_dice_rolls=json.dumps([
            {"rolls": [3], "total": 3, "formula": "1d20", "component_type": "dice"},
            {"value": -1, "formula": "-1", "component_type": "modifier"}
        ]),
        rolled_at=timezone.now() - timedelta(hours=1)
    )

    # Roll 6: Complex 2d8kh1 + 1d4 roll for dice type variety
    Roll.objects.create(
        character=char_pc, group=group_campaign, roll_input='2d8kh1+1d4', roll_value=12,
        raw_dice_rolls=json.dumps([
            {"rolls": [8, 4], "total": 8, "formula": "2d8kh1", "component_type": "dice", "retained_rolls": [8]},
            {"rolls": [4], "total": 4, "formula": "1d4", "component_type": "dice"}
        ]),
        rolled_at=timezone.now()
    )

    return {
        'user_char': user_char,
        'user_group': user_group,
        'group_campaign': group_campaign,
        'char_pc': char_pc,
        'char_npc': char_npc
    }


def test_roll_query_filter_for_global(setup_rolls):
    """
    Tests that the global filter returns all rolls (all 6 rolls created).
    """
    rolls = RollQueryFilter.for_global()
    assert rolls.count() == 6
    assert set(rolls.values_list('roll_value', flat=True)) == {5, 25, 10, 20, 2, 12}


def test_roll_query_filter_for_character(setup_rolls):
    """Tests filtering rolls specific to a single character (PC rolls only)."""
    rolls = RollQueryFilter.for_character(setup_rolls['char_pc'].id)

    assert rolls.count() == 5
    assert set(rolls.values_list('roll_value', flat=True)) == {5, 25, 10, 20, 12}


def test_roll_query_filter_for_group(setup_rolls):
    """Tests filtering rolls for an entire group/campaign (PC + NPC rolls)."""
    rolls = RollQueryFilter.for_group(setup_rolls['group_campaign'].id)

    assert rolls.count() == 6
    assert set(rolls.values_list('roll_value', flat=True)) == {5, 25, 10, 20, 2, 12}


def test_roll_query_filter_raises_on_none():
    """Tests that the filter methods raise ValueError if ID is missing."""
    with pytest.raises(ValueError, match="Character object is required"):
        RollQueryFilter.for_character(None)
    with pytest.raises(ValueError, match="Group ID is required"):
        RollQueryFilter.for_group(None)


class TestLuckAnalyticsService:

    def test_calculate_raw_dice_averages_all_rolls(self, setup_rolls):
        """
        Tests calculation of the overall raw dice average across all rolls.

        Total Raw Sum: 5 (R1) + 20 (R2) + 10 (R3) + 20 (R4) + 3 (R5) + (8+4+4) (R6) = 74
        Total Raw Count: 1 + 1 + 3 + 1 + 1 + 3 = 10
        Average: 74 / 10 = 7.4
        """
        all_rolls = Roll.objects.all()
        analytics = LuckAnalyticsService(all_rolls)
        results = analytics.calculate_raw_dice_averages()

        assert "avg_raw_roll" in results
        assert "total_raw_dice_count" in results
        assert results['total_raw_dice_count'] == 10
        assert results['avg_raw_roll'] == pytest.approx(7.4)

    def test_get_modified_roll_metrics_all_rolls(self, setup_rolls):
        """
        Tests simple aggregation metrics on the final roll value across ALL 6 rolls.
        """
        all_rolls = Roll.objects.all()
        analytics = LuckAnalyticsService(all_rolls)
        metrics = analytics.get_modified_roll_metrics()

        assert metrics['total_rolls'] == 6
        # (5 + 25 + 10 + 20 + 2 + 12) / 6 = 74 / 6 = 12.333...
        assert metrics['avg_modified_roll'] == pytest.approx(12.33, abs=0.01)
        assert metrics['min_modified_roll'] == 2
        assert metrics['max_modified_roll'] == 25

    def test_calculate_dice_type_averages(self, setup_rolls):
        """
        Tests calculation of average roll and count broken down by die type (d4, d6, d8, d20).
        """
        all_rolls = Roll.objects.all()
        analytics = LuckAnalyticsService(all_rolls)
        results = analytics.calculate_dice_type_averages()

        # d4: 1 roll (R6). Sum: 4. Count: 1. Avg: 4.0. Theoretical: 2.5.
        assert 'd4' in results
        assert results['d4']['roll_count'] == 1
        assert results['d4']['average_roll'] == pytest.approx(4.0)
        assert results['d4']['theoretical_average'] == pytest.approx(2.5)

        # d6: 1 roll (R3). Sum: 10 (3+4+3). Count: 3. Avg: 3.33. Theoretical: 3.5.
        assert 'd6' in results
        assert results['d6']['roll_count'] == 3
        assert results['d6']['average_roll'] == pytest.approx(3.33, abs=0.01)
        assert results['d6']['theoretical_average'] == pytest.approx(3.5)

        # d8: 1 roll (R6). Sum: 12 (8+4). Count: 2. Avg: 6.0. Theoretical: 4.5.
        assert 'd8' in results
        assert results['d8']['roll_count'] == 2
        assert results['d8']['average_roll'] == pytest.approx(6.0)
        assert results['d8']['theoretical_average'] == pytest.approx(4.5)

        # d20: 4 rolls (R1, R2, R4, R5). Sum: 5 + 20 + 20 + 3 = 48. Count: 4. Avg: 12.0. Theoretical: 10.5.
        assert 'd20' in results
        assert results['d20']['roll_count'] == 4
        assert results['d20']['average_roll'] == pytest.approx(12.0)
        assert results['d20']['theoretical_average'] == pytest.approx(10.5)

    def test_empty_queryset_handling(self):
        """Tests that the service gracefully handles an empty QuerySet."""
        empty_qs = Roll.objects.none()
        analytics = LuckAnalyticsService(empty_qs)

        modified_metrics = analytics.get_modified_roll_metrics()
        assert modified_metrics == {"total_rolls": 0}

        raw_averages = analytics.calculate_raw_dice_averages()
        assert raw_averages == {"avg_raw_roll": 0.0, "total_raw_dice_count": 0}

        type_averages = analytics.calculate_dice_type_averages()
        assert type_averages == {}
