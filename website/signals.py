import logging

from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from website.models import DailyStatusReport, UserProfile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DailyStatusReport)
def update_leaderboard_on_dsr_save(_sender=None, instance=None, created=None, **_kwargs):  # noqa: ARG001
    user = instance.user

    if getattr(instance, "_skip_leaderboard_update", False):
        return

    try:
        with transaction.atomic():
            profile = UserProfile.objects.select_for_update().get(user=user)
            instance._skip_leaderboard_update = True
            success = profile.update_streak_and_award_points()
            if not success:
                logger.warning(
                    "update_streak_and_award_points failed for user_id=%s; " "skipping leaderboard recalculation",
                    user.id,
                )
                return
            profile.calculate_leaderboard_score()
    except UserProfile.DoesNotExist:
        return

    team = profile.team
    if not team:
        return

    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern(f"team_lb:{team.id}:*")
    else:
        # Fallback: Delete known cache keys
        for page_size in [10, 20, 50, 100]:
            for order in ["score", "streak", "quality"]:
                # Delete up to 50 pages (covers teams with 5000 members at size=100)
                for page in range(1, 51):
                    cache_key = f"team_lb:{team.id}:{order}:{page}:{page_size}"
                    cache.delete(cache_key)
