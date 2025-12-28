from django.db.models import Sum

from website.models import ContributorStats, Organization


def get_weekly_team_stats(start_date, end_date):
    """
    Aggregate weekly stats for teams (Organization type = TEAM).

    Returns an empty list if no TEAM organizations or contributor stats
    exist in the given date range.
    """

    # Step 1: Get all teams
    teams = Organization.objects.filter(type="team")

    if not teams.exists():
        return []

    # Step 2: Aggregate stats for all repos of all teams at once
    stats_queryset = (
        ContributorStats.objects.filter(
            repo__organization__in=teams,
            granularity="day",
            date__gte=start_date,
            date__lte=end_date,
        )
        .values("repo__organization_id")  # Group by team
        .annotate(
            commits=Sum("commits"),
            issues_opened=Sum("issues_opened"),
            issues_closed=Sum("issues_closed"),
            pull_requests=Sum("pull_requests"),
            comments=Sum("comments"),
        )
    )

    # Step 3: Map stats by team ID
    stats_map = {s["repo__organization_id"]: s for s in stats_queryset}

    # Step 4: Build final list
    team_stats = []
    for team in teams:
        s = stats_map.get(team.id, {})
        team_stats.append(
            {
                "team_id": team.id,
                "team_name": team.name,
                "start_date": start_date,
                "end_date": end_date,
                "stats": {
                    "commits": s.get("commits", 0),
                    "issues_opened": s.get("issues_opened", 0),
                    "issues_closed": s.get("issues_closed", 0),
                    "pull_requests": s.get("pull_requests", 0),
                    "comments": s.get("comments", 0),
                },
            }
        )

    return team_stats
