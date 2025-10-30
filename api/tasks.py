"""
Celery Task Definitions for Kobold Keeper.

This module contains periodic and on-demand background tasks for calculating
luck analytics, updating performance records, and performing database cleanup.
"""

import logging

from celery import shared_task
from django.db import transaction
from django.db.models import Avg, Min, Max
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
        today = timezone.localdate()

        group_ids_with_rolls = Roll.objects.filter(
            rolled_at__date=today,
            luck_index__isnull=False
        ).values_list('group_id', flat=True).distinct()

        groups = Group.objects.filter(id__in=group_ids_with_rolls)

        if not groups.exists():
            msg = "TASK: No groups found with eligible rolls today. Exiting."
            logger.info(msg)
            return {
                'status': 'graceful_exit',
                'message': "TASK: No groups processed for performance records."
            }

        for group in groups:
            eligible_rolls = Roll.objects.filter(
                group=group,
                rolled_at__date=today,
                character__isnull=False,
                luck_index__isnull=False
            )
            total_rolls = eligible_rolls.count()
            current_time = timezone.now()

            defaults = {
                'average_luck_index': 0.0,
                'total_rolls': total_rolls,
                'lowest_roll': None,
                'highest_roll': None,
                'luckiest_player_name': "N/A",
                'luckiest_player_score': 0.0,
                'least_lucky_player_name': "N/A",
                'least_lucky_player_score': 0.0,
                'last_updated': current_time,
            }

            if total_rolls == 0:
                logger.info("TASK: Group '%s' has 0 eligible rolls today. Skipping.", group.group_name)
                continue

            stats_results = eligible_rolls.aggregate(
                Avg('luck_index'),
                Min('roll_value'),
                Max('roll_value')
            )

            defaults['average_luck_index'] = stats_results.get('luck_index__avg') or 0.0
            defaults['lowest_roll'] = stats_results.get('roll_value__min')
            defaults['highest_roll'] = stats_results.get('roll_value__max')

            player_luck_stats = eligible_rolls.values(
                'character__character_name'
            ).annotate(
                avg_luck=Avg('luck_index')
            ).order_by('-avg_luck')

            if player_luck_stats.exists():
                luckiest = player_luck_stats.first()
                least_lucky = player_luck_stats.last()

                defaults['luckiest_player_name'] = luckiest['character__character_name']
                defaults['luckiest_player_score'] = luckiest['avg_luck']

                defaults['least_lucky_player_name'] = least_lucky['character__character_name']
                defaults['least_lucky_player_score'] = least_lucky['avg_luck']

            GroupPerformanceRecord.objects.update_or_create(
                group=group,
                defaults=defaults
            )
            logger.info("TASK: Updated Group Performance Record for '%s' (Rolls: %s)", group.group_name, total_rolls)

        msg = "TASK: Successfully processed all groups for performance records."
        logger.info(msg)
        return {
            'status': 'success',
            'message': msg
        }

    except Exception:
        logger.error("FATAL ERROR during update_all_group_performance_records.", exc_info=True)
        raise


@shared_task
@transaction.atomic
def calculate_luckiest_roller_of_the_day():
    """
    Finds the roller with the highest AVERAGE luck index across ALL rolls for the current day
    and records the winner in DailyLuckRecord.
    Returns a structured dictionary for robust test verification.
    """
    try:
        today = timezone.localdate()
        logger.info("TASK: Starting calculate_luckiest_roller_of_the_day for %s...", today)

        daily_luck_averages = Roll.objects.filter(
            rolled_at__date=today,
            luck_index__isnull=False
        ).values(
            'character',
            'character__character_name',
            'group__group_name'
        ).annotate(
            avg_luck=Avg('luck_index')
        ).order_by('-avg_luck')

        if not daily_luck_averages.exists():
            msg = "TASK: No processed rolls found for today. Exiting."
            logger.info(msg)
            return {
                'status': 'graceful_exit',
                'message': msg
            }

        luckiest_roller_stats = daily_luck_averages.first()
        winning_character = Character.objects.get(id=luckiest_roller_stats['character'])

        character_name_snapshot = luckiest_roller_stats['character__character_name']
        group_name_snapshot = luckiest_roller_stats['group__group_name']
        luck_index = luckiest_roller_stats['avg_luck']

        roll_count = Roll.objects.filter(
            rolled_at__date=today,
            character=winning_character
        ).count()

        DailyLuckRecord.objects.update_or_create(
            date=today,
            defaults={
                'character': winning_character,
                'luck_index': luck_index,
                'character_name_snapshot': character_name_snapshot,
                'group_name_snapshot': group_name_snapshot,
                'total_rolls_parsed': roll_count,
            }
        )

        msg = f"TASK: Daily Luck Record updated for {today}. Winner: {character_name_snapshot} (Avg Luck: {luck_index:.5f})"
        logger.info(msg)

        return {
            'status': 'success',
            'date': today.strftime('%Y-%m-%d'),
            'winner': character_name_snapshot,
            'luck_index': round(luck_index, 5),
            'rolls': roll_count
        }

    except Exception:
        logger.error("FATAL ERROR during calculate_luckiest_roller_of_the_day.", exc_info=True)
        raise


@shared_task
@transaction.atomic
def delete_nameless_entities():
    """
    Deletes Groups that were created without a name (empty string).
    Returns a status message suitable for result backend verification.
    """
    logger.info("TASK: Starting delete_nameless_entities...")

    chars_deleted = 0

    nameless_group_query = Group.objects.filter(
        group_name=""
    )
    groups_deleted, _ = nameless_group_query.delete()
    logger.info("TASK: Deleted %d Groups with an empty name.", groups_deleted)

    total_deleted = chars_deleted + groups_deleted

    msg = f"TASK: Nameless entities cleanup complete. Total deleted: {total_deleted}"
    return {
        'status': 'success',
        'message': msg
    }
