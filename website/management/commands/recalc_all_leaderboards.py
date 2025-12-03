from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction

from website.models import UserProfile
from website.services.leaderboard_scoring import LeaderboardScoringService


class Command(BaseCommand):
    help = "Recalculate leaderboard scores for all users and invalidate caches."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Recalculating leaderboard scores..."))

        profiles = UserProfile.objects.select_related("user", "team")
        total = profiles.count()

        team_ids_to_invalidate = set()

        for idx, profile in enumerate(profiles, start=1):
            user = profile.user
            team = profile.team

            try:
                with transaction.atomic():
                    # Update streak first
                    profile.update_streak_and_award_points()

                    # Calculate score
                    score, breakdown = LeaderboardScoringService.calculate_for_user(user)

                    profile.leaderboard_score = score
                    profile.quality_score = breakdown.get("goals", 0)
                    profile.check_in_count = profile.daily_reports.count()
                    profile.save(
                        update_fields=[
                            "leaderboard_score",
                            "quality_score",
                            "check_in_count",
                            "last_score_update",
                        ]
                    )

                    if team:
                        team_ids_to_invalidate.add(team.id)

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Error recalculating user {user.username}: {str(e)}"))

            if idx % 20 == 0:
                self.stdout.write(f"Processed {idx}/{total} users...")

        # Invalidate cache for all affected teams
        for team_id in team_ids_to_invalidate:
            try:
                cache.delete_pattern(f"team_lb:{team_id}:*")
            except Exception:
                # LocMem fallback (no delete_pattern support)
                for order in ("score", "streak", "quality"):
                    for page in range(1, 50):
                        cache.delete(f"team_lb:{team_id}:{order}:{page}:20")

        self.stdout.write(self.style.SUCCESS("Leaderboard recalculation completed."))
