import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.db.models import Q, Count, Min, Max
from django.db.utils import IntegrityError
from django.utils import timezone

from .dice_reader import LuckAnalyticsService
from .models import Roll, Character, Group, DailyLuckRecord, GroupPerformanceRecord

logger = logging.getLogger(__name__)


@shared_task
def calculate_luckiest_roller_of_the_day():
    """
    Analyzes all Roll records created in the last 24 hours to find the Character
    with the highest 'luck_index' and persists the result to DailyLuckRecord,
    including name snapshots for historical integrity.
    """
    analysis_date = timezone.now().date()
    logger.info(f"Starting daily 'luckiest roller' analysis for {analysis_date}...")
    if DailyLuckRecord.objects.filter(date=analysis_date).exists():
        logger.info(f"DailyLuckRecord already exists for {analysis_date}. Skipping calculation.")
        return "Record already exists."

    one_day_ago = timezone.now() - timedelta(hours=24)
    recent_rolls = Roll.objects.filter(rolled_at__gte=one_day_ago)

    if not recent_rolls.exists():
        logger.info("No relevant rolls found in the last 24 hours.")
        return "No data."

    unique_character_ids = recent_rolls.values_list('character_id', flat=True).distinct()
    luck_results = []

    for char_id in unique_character_ids:
        char_rolls = Roll.objects.filter(character_id=char_id, rolled_at__gte=one_day_ago)

        analytics_service = LuckAnalyticsService(char_rolls)

        try:
            luck_data = analytics_service.calculate_luck_index()
            if luck_data.get('total_raw_dice_count', 0) == 0:
                continue

            luck_results.append({
                'character_id': char_id,
                'luck_index': luck_data.get('luck_index', 0.0),
                'total_rolls': luck_data.get('total_raw_dice_count', 0),
            })

        except Exception as e:
            logger.error(f"Error calculating luck index for Character ID {char_id}: {e}")
            continue

    if not luck_results:
        logger.info("No characters had valid roll data for analysis.")
        return "No valid analysis data."

    luckiest_roller_data = max(luck_results, key=lambda x: x['luck_index'])
    luckiest_char = Character.objects.get(id=luckiest_roller_data['character_id'])

    character_name_snapshot = luckiest_char.character_name
    group_name_snapshot = None
    latest_roll_with_group = (
        Roll.objects.filter(character=luckiest_char, rolled_at__gte=one_day_ago)
        .filter(group__isnull=False)
        .order_by('-rolled_at')
        .select_related('group')
        .first()
    )

    if latest_roll_with_group and latest_roll_with_group.group:
        group_name_snapshot = latest_roll_with_group.group.name

    try:
        DailyLuckRecord.objects.create(
            date=analysis_date,
            character=luckiest_char,
            character_name_snapshot=character_name_snapshot,
            group_name_snapshot=group_name_snapshot,
            luck_index=luckiest_roller_data['luck_index'],
            total_rolls_analyzed=luckiest_roller_data['total_rolls']
        )
        log_message = (
            f"Daily Luckiest Roller RECORDED: Character '{character_name_snapshot}' "
            f"from Group '{group_name_snapshot or 'No Group'}' with Index: {luckiest_roller_data['luck_index']:.4f}"
        )
        logger.warning(log_message)
        return log_message

    except IntegrityError:
        logger.error(f"Integrity error: DailyLuckRecord for {analysis_date} already saved.")
        return "Race condition detected, record was already saved."
    except Exception as e:
        logger.critical(f"CRITICAL ERROR saving DailyLuckRecord: {e}")
        return f"CRITICAL ERROR: {e}"


@shared_task
@transaction.atomic
def update_all_group_performance_records():
    """
    Calculates detailed performance metrics for ALL Groups over their ENTIRE rolling history
    and updates the GroupPerformanceRecord table. This task runs daily via Celery Beat.
    """
    logger.info("Starting scheduled update of all GroupPerformanceRecords...")
    all_groups = Group.objects.all()
    groups_updated_count = 0

    for group in all_groups:
        group_rolls_qs = Roll.objects.filter(group=group)

        if not group_rolls_qs.exists():
            record, created = GroupPerformanceRecord.objects.update_or_create(
                group=group,
                defaults={
                    'average_luck_index': 0.0,
                    'total_rolls': 0,
                    'lowest_roll': None,
                    'highest_roll': None,
                    'luckiest_player_name': "N/A",
                    'luckiest_player_score': 0.0,
                    'least_lucky_player_name': "N/A",
                    'least_lucky_player_score': 0.0,
                }
            )
            logger.info(
                f"Group '{group.name}' has no rolls. Record {'created' if created else 'updated'} with defaults.")
            continue

        stats = group_rolls_qs.aggregate(
            total_rolls=Count('id'),
            lowest_roll=Min('roll_value'),
            highest_roll=Max('roll_value')
        )

        total_luck_sum = 0
        total_raw_dice_count = 0

        for roll in group_rolls_qs:
            analytics = LuckAnalyticsService(Roll.objects.filter(id=roll.id))
            luck_data = analytics.calculate_luck_index()

            total_luck_sum += luck_data.get('total_luck_sum', 0)
            total_raw_dice_count += luck_data.get('total_raw_dice_count', 0)

        avg_luck_index = total_luck_sum / total_raw_dice_count if total_raw_dice_count > 0 else 0.0

        unique_character_ids = group_rolls_qs.values_list('character_id', flat=True).distinct()
        character_luck_scores = []

        for char_id in unique_character_ids:
            char_group_rolls = group_rolls_qs.filter(character_id=char_id)

            if char_group_rolls.exists():
                char_analytics = LuckAnalyticsService(char_group_rolls)
                luck_data = char_analytics.calculate_luck_index()

                if luck_data.get('total_raw_dice_count', 0) > 0:
                    character_luck_scores.append({
                        'luck_index': luck_data.get('luck_index', 0.0),
                        'char_name': Character.objects.get(id=char_id).character_name
                    })

        luckiest_player_name = "N/A"
        luckiest_player_score = 0.0
        least_lucky_player_name = "N/A"
        least_lucky_player_score = 0.0

        if character_luck_scores:
            luckiest_data = max(character_luck_scores, key=lambda x: x['luck_index'])
            least_lucky_data = min(character_luck_scores, key=lambda x: x['luck_index'])

            luckiest_player_name = luckiest_data['char_name']
            luckiest_player_score = luckiest_data['luck_index']
            least_lucky_player_name = least_lucky_data['char_name']
            least_lucky_player_score = least_lucky_data['luck_index']

        GroupPerformanceRecord.objects.update_or_create(
            group=group,
            defaults={
                'average_luck_index': avg_luck_index,
                'total_rolls': stats['total_rolls'],
                'lowest_roll': stats['lowest_roll'],
                'highest_roll': stats['highest_roll'],
                'luckiest_player_name': luckiest_player_name,
                'luckiest_player_score': luckiest_player_score,
                'least_lucky_player_name': least_lucky_player_name,
                'least_lucky_player_score': least_lucky_player_score,
            }
        )
        groups_updated_count += 1
        logger.info(f"Performance record updated for Group: {group.name}")

    log_message = f"Finished updating {groups_updated_count} GroupPerformanceRecord(s)."
    logger.info(log_message)
    return log_message


@shared_task
@transaction.atomic
def delete_nameless_entities():
    """
    Database maintenance task: Deletes Group and Character entities
    where the name field is either NULL or an empty string.
    This ensures that only properly named entities persist, preventing
    issues with related objects that rely on descriptive names.
    """
    logger.info("Starting daily nameless entity cleanup...")

    nameless_filter = Q(name__isnull=True) | Q(name='')
    nameless_char_filter = Q(character_name__isnull=True) | Q(character_name='')

    groups_to_delete = Group.objects.filter(nameless_filter)
    deleted_groups_count = groups_to_delete.count()
    groups_to_delete.delete()

    chars_to_delete = Character.objects.filter(nameless_char_filter)
    deleted_chars_count = chars_to_delete.count()
    chars_to_delete.delete()

    log_message = (
        f"Cleanup complete. Deleted {deleted_groups_count} nameless Group(s) "
        f"and {deleted_chars_count} nameless Character(s)."
    )
    logger.info(log_message)
    return log_message
