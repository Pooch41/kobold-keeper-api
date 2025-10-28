import logging
from celery import shared_task
from django.db import transaction
from django.db.models import Avg, Min, Max  # Import Min and Max
from django.utils import timezone
from .models import Roll, Group, GroupPerformanceRecord, DailyLuckRecord, Character

logger = logging.getLogger(__name__)


@shared_task
@transaction.atomic
def update_all_group_performance_records():
    """
    Calculates and updates aggregate performance statistics for all groups.
    Runs daily or on demand. Returns a status message on completion.
    """
    try:
        logger.info("TASK: Starting update_all_group_performance_records...")
        groups = Group.objects.all()

        if not groups.exists():
            msg = "TASK: No groups found. Exiting."
            logger.info(msg)
            return msg

        for group in groups:
            eligible_rolls = Roll.objects.filter(group=group, character__isnull=False, luck_index__isnull=False)
            total_rolls = eligible_rolls.count()

            average_luck_index = 0.0
            luckiest_player_name = "N/A"
            luckiest_player_score = 0.0
            least_lucky_player_name = "N/A"
            least_lucky_player_score = 0.0

            lowest_roll = None
            highest_roll = None

            if total_rolls == 0:
                logger.info(f"TASK: Group '{group.group_name}' has 0 eligible rolls. Resetting stats to defaults.")
            else:
                stats_results = eligible_rolls.aggregate(
                    Avg('luck_index'),
                    Min('final_roll_value'),
                    Max('final_roll_value')
                )

                average_luck_index = stats_results.get('luck_index__avg') or 0.0
                lowest_roll = stats_results.get('final_roll_value__min')
                highest_roll = stats_results.get('final_roll_value__max')

                player_luck_stats = eligible_rolls.values(
                    'character__character_name'
                ).annotate(
                    avg_luck=Avg('luck_index')
                ).order_by('-avg_luck')

                if player_luck_stats.exists():
                    luckiest = player_luck_stats.first()
                    least_lucky = player_luck_stats.last()  # Because it's ordered descending

                    luckiest_player_name = luckiest['character__character_name']
                    luckiest_player_score = luckiest['avg_luck']

                    least_lucky_player_name = least_lucky['character__character_name']
                    least_lucky_player_score = least_lucky['avg_luck']

            GroupPerformanceRecord.objects.update_or_create(
                group=group,
                defaults={
                    'average_luck_index': average_luck_index,
                    'total_rolls': total_rolls,
                    'lowest_roll': lowest_roll,
                    'highest_roll': highest_roll,
                    'luckiest_player_name': luckiest_player_name,
                    'luckiest_player_score': luckiest_player_score,
                    'least_lucky_player_name': least_lucky_player_name,
                    'least_lucky_player_score': least_lucky_player_score,
                    'last_updated': timezone.now(),
                }
            )
            logger.info(f"TASK: Updated Group Performance Record for '{group.group_name}' (Rolls: {total_rolls})")

        msg = "TASK: Successfully processed all groups for performance records."
        logger.info(msg)
        return msg

    except Exception as e:
        logger.error("FATAL ERROR during update_all_group_performance_records.", exc_info=True)
        raise


@shared_task
@transaction.atomic
def calculate_luckiest_roller_of_the_day():
    """
    Finds the luckiest roller across ALL groups for the current day
    and records the winner in DailyLuckRecord. Returns a status dictionary.
    """
    try:
        today = timezone.localdate()
        logger.info(f"TASK: Starting calculate_luckiest_roller_of_the_day for {today}...")

        luckiest_roll = Roll.objects.filter(
            rolled_at__date=today,
            luck_index__isnull=False
        ).order_by('-luck_index').select_related('character', 'group').first()

        if not luckiest_roll:
            msg = "TASK: No processed rolls found for today. Exiting."
            logger.info(msg)
            return {"status": "graceful_exit", "message": msg}

        character_name_snapshot = luckiest_roll.character.character_name
        group_name_snapshot = luckiest_roll.group.group_name
        luck_index = luckiest_roll.luck_index

        DailyLuckRecord.objects.update_or_create(
            date=today,
            defaults={
                'character': luckiest_roll.character,
                'luck_index': luck_index,
                'character_name_snapshot': character_name_snapshot,
                'group_name_snapshot': group_name_snapshot,
                'total_rolls_parsed': 1,
            }
        )

        msg = f"TASK: Daily Luck Record updated for {today}. Winner: {character_name_snapshot}"
        logger.info(msg)
        return {
            "status": "success",
            "date": str(today),
            "winner": character_name_snapshot,
            "luck_index": luck_index
        }

    except Exception as e:
        logger.error("FATAL ERROR during calculate_luckiest_roller_of_the_day.", exc_info=True)
        raise


@shared_task
@transaction.atomic
def delete_nameless_entities():
    """
    Deletes Characters and Groups that were created without a name ('Nameless' or empty).
    Returns the count of deleted entities.
    """
    logger.info("TASK: Starting delete_nameless_entities...")

    nameless_char_query = Character.objects.filter(
        character_name="Nameless"
    )
    chars_deleted, _ = nameless_char_query.delete()
    logger.info(f"TASK: Deleted {chars_deleted} Characters named 'Nameless'.")

    nameless_group_query = Group.objects.filter(
        group_name=""
    )
    groups_deleted, _ = nameless_group_query.delete()
    logger.info(f"TASK: Deleted {groups_deleted} Groups with an empty name.")

    total_deleted = chars_deleted + groups_deleted

    if total_deleted > 0:
        msg = f"TASK: Finished delete_nameless_entities. Total entities (Characters/Groups) deleted: {total_deleted}"
        logger.info(msg)
        return total_deleted
    else:
        msg = "TASK: Finished delete_nameless_entities. (No entities deleted in placeholder logic)."
        logger.info(msg)
        return msg
