import logging

from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from website.models import DailyStatusReport, UserProfile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DailyStatusReport)
def update_leaderboard_on_dsr_save(sender, instance, created, **kwargs):
    user = instance.user

    try:
        profile = UserProfile.objects.select_for_update().get(user=user)
    except UserProfile.DoesNotExist:
        return

    if getattr(instance, "_skip_leaderboard_update", False):
        return

    with transaction.atomic():
        profile.update_streak_and_award_points()
        profile.calculate_leaderboard_score()

    team = profile.team
    if team:
        try:
            cache.delete_pattern(f"team_lb:{team.id}:*")
        except Exception:
            pass
