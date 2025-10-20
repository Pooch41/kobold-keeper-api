import pytest
import json
from django.utils import timezone
from datetime import timedelta

from api.models import Roll, Character, Group, User
from api.dice_reader import LuckAnalyticsService, RollQueryFilter


@pytest.fixture
def setup_rolls(db):
    """
    Sets up a complex dataset of rolls for various filter and calculation tests.
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

    Roll.objects.create(
        character=char_pc, group=group_campaign, roll_input='1d20', roll_value=5,
        raw_dice_rolls=json.dumps([{"type": "d20", "rolls": [5]}]),
        rolled_at=timezone.now() - timedelta(hours=5)
    )

    Roll.objects.create(
        character=char_pc, group=group_campaign, roll_input='1d20+5', roll_value=25,
        raw_dice_rolls=json.dumps([{"type": "d20", "rolls": [20]}, {"type": "modifier", "value": 5}]),
        rolled_at=timezone.now() - timedelta(hours=4)
    )

    Roll.objects.create(
        character=char_pc, group=group_campaign, roll_input='3d6', roll_value=10,
        raw_dice_rolls=json.dumps([{"type": "d6", "rolls": [3, 4, 3]}]),
        rolled_at=timezone.now() - timedelta(hours=3)
    )

    Roll.objects.create(
        character=char_pc, group=group_campaign, roll_input='1d20', roll_value=20,
        raw_dice_rolls=json.dumps([{"type": "d20", "rolls": [20]}]),
        rolled_at=timezone.now() - timedelta(hours=2)
    )

    Roll.objects.create(
        character=char_npc, group=group_campaign, roll_input='1d20-1', roll_value=2,
        raw_dice_rolls=json.dumps([{"type": "d20", "rolls": [3]}, {"type": "modifier", "value": -1}]),
        rolled_at=timezone.now() - timedelta(hours=1)
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
    Tests that the global filter returns all rolls (all 5 rolls created).
    """
    rolls = RollQueryFilter.for_global()
    assert rolls.count() == 5
    assert set(rolls.values_list('roll_value', flat=True)) == {5, 25, 10, 20, 2}


def test_roll_query_filter_for_character(setup_rolls):
    """Tests filtering rolls specific to a single character (PC rolls only)."""
    rolls = RollQueryFilter.for_character(setup_rolls['char_pc'].id)

    assert rolls.count() == 4
    assert set(rolls.values_list('roll_value', flat=True)) == {5, 25, 10, 20}


def test_roll_query_filter_for_group(setup_rolls):
    """Tests filtering rolls for an entire group/campaign (PC + NPC rolls)."""
    rolls = RollQueryFilter.for_group(setup_rolls['group_campaign'].id)

    assert rolls.count() == 5
    assert set(rolls.values_list('roll_value', flat=True)) == {5, 25, 10, 20, 2}


def test_roll_query_filter_raises_on_none():
    """Tests that the filter methods raise ValueError if ID is missing."""
    with pytest.raises(ValueError, match="Character object is required"):
        RollQueryFilter.for_character(None)
    with pytest.raises(ValueError, match="Group ID is required"):
        RollQueryFilter.for_group(None)

class TestLuckAnalyticsService:

    def test_calculate_raw_dice_averages_all_rolls(self, setup_rolls):
        """
        Tests calculation of the overall raw dice average.
        It confirms the logic correctly parses the complex JSON string structure.
        """
        all_rolls = Roll.objects.all()
        analytics = LuckAnalyticsService(all_rolls)
        results = analytics.calculate_raw_dice_averages()

        assert "avg_raw_roll" in results
        assert "total_raw_dice_count" in results
        assert results['total_raw_dice_count'] == 7
        assert results['avg_raw_roll'] == pytest.approx(8.29, abs=0.01)

    def test_get_modified_roll_metrics_all_rolls(self, setup_rolls):
        """
        Tests simple aggregation metrics on the final roll value across ALL 5 rolls.
        """
        all_rolls = Roll.objects.all()
        analytics = LuckAnalyticsService(all_rolls)
        metrics = analytics.get_modified_roll_metrics()

        assert metrics['total_rolls'] == 5
        assert metrics['avg_modified_roll'] == pytest.approx(12.4)
        assert metrics['min_modified_roll'] == 2
        assert metrics['max_modified_roll'] == 25

    def test_empty_queryset_handling(self):
        """Tests that the service gracefully handles an empty QuerySet."""
        empty_qs = Roll.objects.none()
        analytics = LuckAnalyticsService(empty_qs)


        modified_metrics = analytics.get_modified_roll_metrics()
        assert modified_metrics == {"total_rolls": 0}

        raw_averages = analytics.calculate_raw_dice_averages()
        assert raw_averages == {"avg_raw_roll": 0.0, "total_raw_dice_count": 0}
