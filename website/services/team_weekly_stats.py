import logging
from datetime import date
from typing import Any, Dict, List

from django.db.models import Sum
from django.db.models.functions import Coalesce

from website.models import ContributorStats, OrganisationType, Organization

logger = logging.getLogger(__name__)


def get_weekly_team_stats(start_date: date, end_date: date) -> List[Dict[str, Any]]:
    """
    Aggregate weekly stats for TEAM organizations.

    Returns an empty list if no TEAM organizations or contributor stats
    exist in the given date range.
    """

    logger.info("Aggregating weekly team stats from %s to %s", start_date, end_date)

    teams = list(Organization.objects.filter(type=OrganisationType.TEAM.value).only("id", "name"))

    if not teams:
        logger.debug("No TEAM organizations found")
        return []

    # ContributorStats are stored at daily granularity.
    # Weekly stats are computed by aggregating daily records
    # over the given date range.
    team_ids = [t.id for t in teams]
    stats_queryset = (
        ContributorStats.objects.filter(
            repo__organization_id__in=team_ids,
            granularity="day",
            date__range=(start_date, end_date),
        )
        .values("repo__organization_id")
        .annotate(
            commits=Coalesce(Sum("commits"), 0),
            issues_opened=Coalesce(Sum("issues_opened"), 0),
            issues_closed=Coalesce(Sum("issues_closed"), 0),
            pull_requests=Coalesce(Sum("pull_requests"), 0),
            comments=Coalesce(Sum("comments"), 0),
        )
    )

    stats_map = {s["repo__organization_id"]: s for s in stats_queryset}

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
