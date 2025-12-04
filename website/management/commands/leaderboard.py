from django.db import transaction


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

    # Wrap all profile updates in a transactional row-level lock
    with transaction.atomic():
        locked_profile = UserProfile.objects.select_for_update().get(pk=profile.pk)

        # Update streak BEFORE score recalculation
        locked_profile.update_streak_and_award_points()

        # Recalculate the score safely under lock
        try:
            locked_profile.calculate_leaderboard_score()
        except Exception as e:
            logger.exception("Failed to recalc leaderboard score for user %s: %s", user.id, e)

    # -------- CACHE INVALIDATION --------
    team = profile.team
    if team:
        pattern = f"team_lb:{team.id}:*"
        try:
            cache.delete_pattern(pattern)
        except Exception:
            # LocMemCache fallback
            for order in ("score", "streak", "quality"):
                for page in range(1, 20):
                    cache_key = f"team_lb:{team.id}:{order}:{page}:20"
                    cache.delete(cache_key)
