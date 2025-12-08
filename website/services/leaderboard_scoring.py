from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone


class LeaderboardScoringService:
    @staticmethod
    def calculate_for_user(user):
        from website.models import UserProfile

        """
        Returns:
            score (float)
            breakdown (dict)
        """
        try:
            # Touch related profile to ensure it exists
            user.userprofile
        except UserProfile.DoesNotExist:
            # Consistent zero-case return
            return 0.0, {"frequency": 0, "streak": 0, "goals": 0, "completeness": 0}

        from website.models import DailyStatusReport

        reports = DailyStatusReport.objects.filter(user=user, created__gte=timezone.now() - timedelta(days=30))

        if not reports.exists():
            return 0, {"frequency": 0, "streak": 0, "goals": 0, "completeness": 0}

        # Frequency score (0–100)
        active_days = 22  # Approximate business days in a 30-day period
        check_in_days = reports.count()
        frequency_score = (check_in_days / active_days) * 100

        # Streak score
        streak_score = min(user.userprofile.current_streak * 2, 30)

        # Count reports where goal was accomplished
        total_reports = reports.count()
        if total_reports > 0:
            accomplished = reports.filter(goal_accomplished=True).count()
            goal_score = (accomplished / total_reports) * 100
        else:
            goal_score = 0

        # Use aggregation instead of iteration
        stats = reports.aggregate(
            total=Count("id"),
            accomplished=Count("id", filter=Q(goal_accomplished=True)),
            has_prev=Count("id", filter=~Q(previous_work="")),
            has_next=Count("id", filter=~Q(next_plan="")),
            has_blockers=Count("id", filter=~Q(blockers="")),
            has_mood=Count("id", filter=~Q(current_mood="")),
        )

        # Completeness score
        completeness_score = (
            (
                (stats["has_prev"] + stats["has_next"] + stats["has_blockers"] * 0.5 + stats["has_mood"] * 0.5)
                / (stats["total"] * 3)
            )
            * 100
            if stats["total"] > 0
            else 0
        )

        # Weighted final
        final_score = frequency_score * 0.2 + streak_score * 0.2 + goal_score * 0.3 + completeness_score * 0.3

        return round(final_score, 2), {
            "frequency": round(frequency_score, 2),
            "streak": round(streak_score, 2),
            "goals": round(goal_score, 2),
            "completeness": round(completeness_score, 2),
        }
