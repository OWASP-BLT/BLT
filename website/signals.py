from website.models import DailyStatusReport


@receiver(post_save, sender=DailyStatusReport)
def update_score_on_checkin(sender, instance, **kwargs):
    try:
        profile = instance.user.userprofile
        profile.update_leaderboard_score()
    except UserProfile.DoesNotExist:
        pass
