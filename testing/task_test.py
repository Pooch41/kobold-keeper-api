import pytest
from django.utils import timezone
from django.test import override_settings
from api.models import User, Group, Character, Roll, GroupPerformanceRecord
from api.tasks import update_all_group_performance_records

pytestmark = pytest.mark.django_db

#setup
@pytest.fixture
def test_user():
    return User.objects.create_user(username="task_tester", password="password123")


@pytest.fixture
def test_group(test_user):
    return Group.objects.create(group_name="Task Test Group", owner=test_user)


@pytest.fixture
def test_character(test_group, test_user):
    return Character.objects.create(
        character_name="Task Hero",
        group=test_group,
        user=test_user
    )



@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_update_performance_records_creates_stats(test_group, test_character):
    """
    Integration Test:
    Verifies that the Celery task correctly aggregates Roll data into a GroupPerformanceRecord.
    """
    now = timezone.now()

    Roll.objects.create(
        character=test_character,
        group=test_group,
        roll_input="1d20",
        roll_value=20,
        luck_index=1.0,
        raw_dice_rolls='[]',
        rolled_at=now
    )

    Roll.objects.create(
        character=test_character,
        group=test_group,
        roll_input="1d20",
        roll_value=1,
        luck_index=0.0,
        raw_dice_rolls='[]',
        rolled_at=now
    )

    update_all_group_performance_records.delay()

    record = GroupPerformanceRecord.objects.get(group=test_group)

    assert record.total_rolls == 2
    assert record.average_luck_index == 0.5
    assert record.highest_roll == 20
    assert record.lowest_roll == 1


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_update_performance_records_idempotency(test_group, test_character):
    """
    Reliability Test:
    Verifies that running the task multiple times does not corrupt data.
    """
    Roll.objects.create(
        character=test_character,
        group=test_group,
        roll_value=10,
        luck_index=0.5,
        raw_dice_rolls='[]',
        rolled_at=timezone.now()
    )

    update_all_group_performance_records.delay()
    update_all_group_performance_records.delay()

    assert GroupPerformanceRecord.objects.filter(group=test_group).count() == 1

    record = GroupPerformanceRecord.objects.get(group=test_group)
    assert record.total_rolls == 1