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

    # Roll 1 (PC): 1d20 (Result 5) -> Actual: 5, Theoretical: 10.5
    Roll.objects.create(
        character=char_pc, group=group_campaign, roll_input='1d20', roll_value=5,
        raw_dice_rolls=json.dumps([
            {"rolls": [5], "total": 5, "formula": "1d20", "component_type": "dice"}
        ]),
        rolled_at=timezone.now() - timedelta(hours=5)
    )

    # Roll 2 (PC): 1d20+5 (Result 25) - Natural 20. Actual: 20, Theoretical: 10.5
    Roll.objects.create(
        character=char_pc, group=group_campaign, roll_input='1d20+5', roll_value=25,
        raw_dice_rolls=json.dumps([
            {"rolls": [20], "total": 20, "formula": "1d20", "component_type": "dice"},
            {"value": 5, "formula": "5", "component_type": "modifier"}
        ]),
        rolled_at=timezone.now() - timedelta(hours=4)
    )

    # Roll 3 (PC): 3d6 (Result 10) - Rolls 3, 4, 3. Actual: 10, Theoretical: 10.5
    Roll.objects.create(
        character=char_pc, group=group_campaign, roll_input='3d6', roll_value=10,
        raw_dice_rolls=json.dumps([
            {"rolls": [3, 4, 3], "total": 10, "formula": "3d6", "component_type": "dice"}
        ]),
        rolled_at=timezone.now() - timedelta(hours=3)
    )

    # Roll 4 (PC): 1d20 (Result 20). Actual: 20, Theoretical: 10.5
    Roll.objects.create(
        character=char_pc, group=group_campaign, roll_input='1d20', roll_value=20,
        raw_dice_rolls=json.dumps([
            {"rolls": [20], "total": 20, "formula": "1d20", "component_type": "dice"}
        ]),
        rolled_at=timezone.now() - timedelta(hours=2)
    )

    # Roll 5 (NPC): 1d20-1 (Result 2) - Low roll. Raw roll: 3. Actual: 3, Theoretical: 10.5
    Roll.objects.create(
        character=char_npc, group=group_campaign, roll_input='1d20-1', roll_value=2,
        raw_dice_rolls=json.dumps([
            {"rolls": [3], "total": 3, "formula": "1d20", "component_type": "dice"},
            {"value": -1, "formula": "-1", "component_type": "modifier"}
        ]),
        rolled_at=timezone.now() - timedelta(hours=1)
    )

    # Roll 6 (PC): Complex 2d8kh1 + 1d4. Rolls 8, 4 (d8) and 4 (d4). Actual: 8+4+4=16, Theoretical: 2*4.5 + 1*2.5 = 11.5
    Roll.objects.create(
        character=char_pc, group=group_campaign, roll_input='2d8kh1+1d4', roll_value=12,
        raw_dice_rolls=json.dumps([
            {"rolls": [8, 4], "total": 8, "formula": "2d8kh1", "component_type": "dice", "retained_rolls": [8]},
            # Rolls: 8, 4. Total raw sum: 12 (8+4)
            {"rolls": [4], "total": 4, "formula": "1d4", "component_type": "dice"}  # Rolls: 4. Total raw sum: 4
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

        Total Raw Sum: 5 (R1) + 20 (R2) + 10 (R3) + 20 (R4) + 3 (R5) + 16 (R6: 8+4+4) = 74
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

        # d4: 1 roll (R6). Sum: 4. Count: 1. Avg: 4.0. Theoretical: 2.5. Luck Index: 4.0/2.5 = 1.6
        assert 'd4' in results
        assert results['d4']['roll_count'] == 1
        assert results['d4']['average_roll'] == pytest.approx(4.0)
        assert results['d4']['luck_index'] == pytest.approx(1.6)

        # d6: 1 roll (R3). Sum: 10 (3+4+3). Count: 3. Avg: 3.33. Theoretical: 3.5. Luck Index: 3.33/3.5 = 0.952
        assert 'd6' in results
        assert results['d6']['roll_count'] == 3
        assert results['d6']['average_roll'] == pytest.approx(3.33, abs=0.01)
        assert results['d6']['luck_index'] == pytest.approx(0.952, abs=0.001)

        # d8: 1 roll (R6). Sum: 12 (8+4). Count: 2. Avg: 6.0. Theoretical: 4.5. Luck Index: 6.0/4.5 = 1.3333
        assert 'd8' in results
        assert results['d8']['roll_count'] == 2
        assert results['d8']['average_roll'] == pytest.approx(6.0)
        assert results['d8']['luck_index'] == pytest.approx(1.3333, abs=0.0001)

        # d20: 4 rolls (R1, R2, R4, R5). Sum: 5 + 20 + 20 + 3 = 48. Count: 4. Avg: 12.0. Theoretical: 10.5. Luck Index: 12.0/10.5 = 1.1428
        assert 'd20' in results
        assert results['d20']['roll_count'] == 4
        assert results['d20']['average_roll'] == pytest.approx(12.0)
        assert results['d20']['luck_index'] == pytest.approx(1.1428, abs=0.0001)

    # --- New Tests for Luck Delta and Luckiest Roller ---
    def test_calculate_luck_delta_by_character(self, setup_rolls):
        """
        Tests the per-character calculation of the luck delta and luck delta ratio.
        """
        all_rolls = Roll.objects.all()
        analytics = LuckAnalyticsService(all_rolls)
        results = analytics.calculate_luck_delta_by_character()

        pc_id = setup_rolls['char_pc'].id
        npc_id = setup_rolls['char_npc'].id

        # Find the character results using their IDs
        pc_data = next((r for r in results if r['character_id'] == pc_id), None)
        npc_data = next((r for r in results if r['character_id'] == npc_id), None)

        assert len(results) == 2

        # Amaryllis the Rogue (PC)
        # Total Actual Sum: 71.0, Total Theoretical Sum: 53.5
        # Luck Delta: 71.0 - 53.5 = 17.5
        # Luck Delta Ratio: 17.5 / 53.5 = 0.327102...
        assert pc_data is not None
        assert pc_data['character_name'] == 'Amaryllis the Rogue'
        assert pc_data['total_raw_dice_count'] == 9
        assert pc_data['luck_delta'] == pytest.approx(17.5)
        assert pc_data['luck_delta_ratio'] == pytest.approx(0.3271, abs=0.0001)

        # Goblin Grunt (NPC)
        # Total Actual Sum: 3.0, Total Theoretical Sum: 10.5
        # Luck Delta: 3.0 - 10.5 = -7.5
        # Luck Delta Ratio: -7.5 / 10.5 = -0.714285...
        assert npc_data is not None
        assert npc_data['character_name'] == 'Goblin Grunt'
        assert npc_data['total_raw_dice_count'] == 1
        assert npc_data['luck_delta'] == pytest.approx(-7.5)
        # Corrected assertion for precision: using -0.7143 for round(..., 4)
        assert npc_data['luck_delta_ratio'] == pytest.approx(-0.7143, abs=0.0001)

    def test_get_luckiest_roller_by_delta(self, setup_rolls):
        """
        Tests that the service correctly identifies the luckiest character based on ratio
        using the default min_rolls=1.
        """
        all_rolls = Roll.objects.all()
        analytics = LuckAnalyticsService(all_rolls)

        luckiest_roller = analytics.get_luckiest_roller_by_delta()

        # Amaryllis the Rogue (Ratio ~0.327) is the luckiest.
        assert luckiest_roller is not None
        assert luckiest_roller['character_name'] == 'Amaryllis the Rogue'
        assert luckiest_roller['luck_delta_ratio'] == pytest.approx(0.3271, abs=0.0001)

    def test_get_luckiest_roller_by_delta_with_min_rolls_constraint(self, setup_rolls):
        """
        Tests that the service ignores characters with too few rolls if a constraint is used.
        """
        # Create a third character with 4 rolls (less than the min_rolls=5 constraint)
        user = User.objects.create_user(username='extra_user', password='pw')
        char_tie = Character.objects.create(
            character_name='Tie Breaker',
            user=user,
            group=setup_rolls['group_campaign'],
        )
        # 4 rolls for 'Tie Breaker': 4x 1d6 (rolls 3,3,3,3). Actual=12, Theo=4*3.5=14. Ratio: (12-14)/14 = -0.1428
        for i in range(4):
            Roll.objects.create(
                character=char_tie, group=setup_rolls['group_campaign'], roll_input='1d6', roll_value=3,
                raw_dice_rolls=json.dumps([{"rolls": [3], "total": 3, "formula": "1d6", "component_type": "dice"}]),
                rolled_at=timezone.now() + timedelta(minutes=i)
            )

        all_rolls = Roll.objects.all()
        analytics = LuckAnalyticsService(all_rolls)

        # --- Scenario 1: min_rolls=5 (Excludes NPC (1) and Tie Breaker (4)) ---
        luckiest_roller = analytics.get_luckiest_roller_by_delta(min_rolls=5)

        # Only Amaryllis the Rogue (9 rolls) is considered, and she is the luckiest.
        assert luckiest_roller is not None
        assert luckiest_roller['character_name'] == 'Amaryllis the Rogue'
        assert luckiest_roller['luck_delta_ratio'] == pytest.approx(0.3271, abs=0.0001)

        # --- Scenario 2: min_rolls=1 (All characters are considered) ---
        luckiest_roller_min_1 = analytics.get_luckiest_roller_by_delta(min_rolls=1)

        # Amaryllis (0.327) > Tie Breaker (-0.142) > Goblin Grunt (-0.714)
        assert luckiest_roller_min_1['character_name'] == 'Amaryllis the Rogue'
        assert luckiest_roller_min_1['luck_delta_ratio'] == pytest.approx(0.3271, abs=0.0001)

        # --- Scenario 3: Check exclusion (should return {}) ---
        no_roller = analytics.get_luckiest_roller_by_delta(min_rolls=10)
        assert no_roller == {}
