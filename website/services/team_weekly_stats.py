from django.db.models import Sum
from website.models import Organization, ContributorStats


def get_weekly_team_stats(start_date, end_date):
    """
    Aggregate weekly stats for teams (Organization type = TEAM).

    Returns an empty list if no TEAM organizations or contributor stats
    exist in the given date range.
    """
    team_stats = []

    teams = Organization.objects.filter(type="team")

    for team in teams:
        # Get all repos owned by this team
        repos = team.repos.all()

        # Aggregate contributor stats for these repos in the given week
        stats = ContributorStats.objects.filter(
            repo__in=repos,
            granularity="day",
            date__gte=start_date,
            date__lte=end_date,
        ).aggregate(
            commits=Sum("commits"),
            issues_opened=Sum("issues_opened"),
            issues_closed=Sum("issues_closed"),
            pull_requests=Sum("pull_requests"),
            comments=Sum("comments"),
        )

        team_stats.append({
            "team_id": team.id,
            "team_name": team.name,
            "start_date": start_date,
            "end_date": end_date,
            "stats": {
                "commits": stats["commits"] or 0,
                "issues_opened": stats["issues_opened"] or 0,
                "issues_closed": stats["issues_closed"] or 0,
                "pull_requests": stats["pull_requests"] or 0,
                "comments": stats["comments"] or 0,
            },
        })

    return team_stats
