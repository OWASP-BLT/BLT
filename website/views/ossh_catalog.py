from django.http import JsonResponse
from django.views.decorators.http import require_GET

from website.models import OsshArticle, OsshCommunity, OsshDiscussionChannel, Repo


def _tags(obj):
    # With prefetch_related("tags") this won't cause N+1 queries
    return [t.name for t in obj.tags.all()]


@require_GET
def ossh_catalog(request):
    """
    Returns the OSSH catalog (repos + communities + discussion_channels + articles) as JSON.
    Uses real model fields + prefetch_related("tags") to avoid N+1 queries.
    """

    # -----------------
    # Repos
    # -----------------
    repos_qs = Repo.objects.only(
        "id", "name", "repo_url", "primary_language", "stars", "forks", "description"
    ).prefetch_related("tags")

    repos = [
        {
            "name": r.name,
            "url": r.repo_url,
            "description": getattr(r, "description", "") or "",
            "primary_language": r.primary_language or "",
            "stars": r.stars or 0,
            "forks": r.forks or 0,
            "tags": _tags(r),
        }
        for r in repos_qs
    ]

    # -----------------
    # Communities
    # -----------------
    communities_qs = OsshCommunity.objects.only(
        "id",
        "name",
        "description",
        "website",
        "source",
        "category",
        "contributors_count",
    ).prefetch_related("tags")

    communities = [
        {
            "name": c.name,
            "description": c.description or "",
            "website": c.website or "",
            "source": c.source or "",
            "category": c.category or "",
            "contributors_count": c.contributors_count or 0,
            "tags": _tags(c),
        }
        for c in communities_qs
    ]

    # -----------------
    # Discussion Channels
    # -----------------
    channels_qs = OsshDiscussionChannel.objects.only(
        "id",
        "name",
        "description",
        "source",
        "member_count",
        "invite_url",
        "logo_url",
    ).prefetch_related("tags")

    discussion_channels = [
        {
            "name": ch.name,
            "description": ch.description or "",
            "source": ch.source or "",
            "member_count": ch.member_count or 0,
            "invite_url": ch.invite_url or "",
            "logo_url": ch.logo_url or "",
            "tags": _tags(ch),
        }
        for ch in channels_qs
    ]

    # -----------------
    # Articles
    # -----------------
    articles_qs = OsshArticle.objects.only(
        "id",
        "title",
        "author",
        "author_profile_image",
        "description",
        "publication_date",
        "source",
        "url",
        "cover_image",
        "reading_time_minutes",
    ).prefetch_related("tags")

    articles = [
        {
            "title": a.title,
            "author": a.author,
            "author_profile_image": a.author_profile_image or "",
            "description": a.description or "",
            "publication_date": a.publication_date.isoformat() if a.publication_date else "",
            "source": a.source or "",
            "url": a.url or "",
            "cover_image": a.cover_image or "",
            "reading_time_minutes": a.reading_time_minutes or 0,
            "tags": _tags(a),
        }
        for a in articles_qs
    ]

    payload = {
        "repos": repos,
        "communities": communities,
        "discussion_channels": discussion_channels,
        "articles": articles,
    }

    return JsonResponse(payload, json_dumps_params={"indent": 2})
