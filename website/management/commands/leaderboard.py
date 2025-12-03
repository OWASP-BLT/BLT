from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.dispatch import receiver

from website.management.base import LoggedBaseCommand
from website.models import DailyStatusReport, Issue, UserProfile


class Command(LoggedBaseCommand):
    help = "Update user based on number of bugs"

    def handle(self, *args, **options):
        all_user_prof = UserProfile.objects.all()
        all_user = User.objects.all()
        for user_ in all_user:
            user_prof = UserProfile.objects.get(user=user_)
            total_issues = Issue.objects.filter(user=user_).count()
            if total_issues <= 10:
                user_prof.title = 1
            elif total_issues <= 50:
                user_prof.title = 2
            elif total_issues <= 200:
                user_prof.title = 3
            else:
                user_prof.title = 4

            user_prof.save()

        return str("All users updated.")


from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.dispatch import receiver

from website.models import DailyStatusReport, UserProfile


@receiver(post_save, sender=DailyStatusReport)
def update_leaderboard_on_dsr_save(sender, instance, created, **kwargs):
    """
    Recalculate leaderboard score when a DSR is created/updated.
    Also invalidate team leaderboard caches.
    """
    user = instance.user
    try:
        profile = user.userprofile
    except ObjectDoesNotExist:
        return

    if getattr(instance, "_skip_leaderboard_update", False):
        return

    # Update streak BEFORE score recalculation
    profile.update_streak_and_award_points()

    # Recalculate the score
    try:
        profile.calculate_leaderboard_score()
    except Exception:
        pass  # never break DSR flow

    # -------- CACHE INVALIDATION --------
    team = profile.team
    if team:
        pattern = f"team_lb:{team.id}:*"
        try:
            cache.delete_pattern(pattern)
        except Exception:
            # LocMemCache doesn't support delete_pattern
            # Manual brute force: iterate all possible pages
            for order in ("score", "streak", "quality"):
                for page in range(1, 20):
                    cache_key = f"team_lb:{team.id}:{order}:{page}:20"
                    cache.delete(cache_key)
