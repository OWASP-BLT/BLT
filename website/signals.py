from django.db.models.signals import post_save
from django.dispatch import receiver

from website.models import DailyStatusReport, UserProfile


@receiver(post_save, sender=DailyStatusReport)
def update_score_on_checkin(sender, instance, **kwargs):
    try:
        profile = instance.user.userprofile
        profile.update_leaderboard_score()
    except UserProfile.DoesNotExist:
        logger.warning(f"Leaderboard update skipped: UserProfile missing for user {instance.user_id}")
