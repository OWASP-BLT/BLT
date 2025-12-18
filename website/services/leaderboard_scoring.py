from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone


class LeaderboardScoringService:
    @staticmethod
    def calculate_for_user(user):
        from website.models import DailyStatusReport, UserProfile

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

        cutoff_date = (timezone.now() - timedelta(days=30)).date()
        reports = DailyStatusReport.objects.filter(user=user, date__gte=cutoff_date)

        #  Do ALL counts in one aggregation
        stats = reports.aggregate(
            total=Count("id"),
            accomplished=Count("id", filter=Q(goal_accomplished=True)),
            has_prev=Count("id", filter=Q(previous_work__isnull=False) & ~Q(previous_work="")),
            has_next=Count("id", filter=~Q(next_plan="")),
            has_blockers=Count("id", filter=~Q(blockers="")),
            has_mood=Count("id", filter=~Q(current_mood="")),
        )
        if stats["total"] == 0:
            return 0, {"frequency": 0, "streak": 0, "goals": 0, "completeness": 0}

        #  Use aggregated values
        active_days = 22
        check_in_days = stats["total"]  #  No extra query
        frequency_score = (check_in_days / active_days) * 100

        streak_score = min(user.userprofile.current_streak * 2, 30)

        #  Use aggregated values
        total_reports = stats["total"]  #  No extra query
        if total_reports > 0:
            goal_score = (stats["accomplished"] / total_reports) * 100  # Already calculated
        else:
            goal_score = 0

        # Completeness score (same as before)
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
