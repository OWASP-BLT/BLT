from datetime import timedelta

from django.utils import timezone


class LeaderboardScoringService:
    @staticmethod
    def calculate_for_user(user):
        """
        Returns:
            score (float)
            breakdown (dict)
        """
        from website.models import DailyStatusReport

        reports = DailyStatusReport.objects.filter(
            user=user, created_at__gte=timezone.now() - timedelta(days=30)
        ).order_by("created_at")

        if not reports.exists():
            return 0, {"frequency": 0, "streak": 0, "goals": 0, "completeness": 0}

        # Frequency score (0–100)
        active_days = 22  # Approx business days
        check_in_days = reports.count()
        frequency_score = (check_in_days / active_days) * 100

        # Streak score
        streak_score = min(user.userprofile.current_streak * 2, 30)

        # Goal completion score
        goal_reports = reports.filter(has_goals=True)
        if goal_reports.exists():
            accomplished = goal_reports.filter(goals_accomplished=True).count()
            goal_score = (accomplished / goal_reports.count()) * 100
        else:
            goal_score = 0

        # Completeness score
        completeness_values = []
        for r in reports:
            c = (
                (1 if r.previous_work else 0)
                + (1 if r.next_plan else 0)
                + (0.5 if r.blockers else 0)
                + (0.5 if r.mood else 0)
            ) / 3
            completeness_values.append(c)

        completeness_score = (sum(completeness_values) / len(completeness_values)) * 100

        # Weighted final
        final_score = frequency_score * 0.2 + streak_score * 0.2 + goal_score * 0.3 + completeness_score * 0.3

        return round(final_score, 2), {
            "frequency": round(frequency_score, 2),
            "streak": round(streak_score, 2),
            "goals": round(goal_score, 2),
            "completeness": round(completeness_score, 2),
        }
