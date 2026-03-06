import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from website.models import OsshArticle, OsshCommunity, OsshDiscussionChannel, Repo


def _tags(obj):
    """
    Best-effort tags:
    - if obj.tags is a list/JSONField/text
    - or tags is ManyToMany
    """
    if hasattr(obj, "tags"):
        v = getattr(obj, "tags")
        # JSONField(list)
        if isinstance(v, (list, tuple)):
            return [str(x).strip() for x in v if str(x).strip()]
        # comma-separated text / JSON string
        if isinstance(v, str) and v.strip():
            s = v.strip()
            if s.startswith("[") and s.endswith("]"):
                try:
                    arr = json.loads(s)
                    if isinstance(arr, list):
                        return [str(x).strip() for x in arr if str(x).strip()]
                except Exception:
                    pass
            return [x.strip() for x in s.split(",") if x.strip()]
        # ManyToMany
        try:
            if hasattr(v, "all"):
                return [str(t).strip() for t in v.all() if str(t).strip()]
        except Exception:
            pass
    return []


@require_GET
def ossh_catalog(request):
    """
    Read-only catalog for BLT-OSSH GitHub Pages.

    Returns ONLY OSSH-related public data:
      - Repo
      - OsshCommunity
      - OsshDiscussionChannel
      - OsshArticle
    """
    repos = []
    for r in Repo.objects.all():
        repos.append(
            {
                "name": getattr(r, "name", "") or getattr(r, "repo_name", "") or "",
                "full_name": getattr(r, "full_name", "") or getattr(r, "github_full_name", "") or "",
                "description": getattr(r, "description", "") or "",
                "url": getattr(r, "url", "") or getattr(r, "repo_url", "") or getattr(r, "source_code", "") or "",
                "language": getattr(r, "language", "") or getattr(r, "primary_language", "") or "",
                "stars": int(getattr(r, "stars", 0) or getattr(r, "stargazers_count", 0) or 0),
                "forks": int(getattr(r, "forks", 0) or getattr(r, "forks_count", 0) or 0),
                "tags": _tags(r),
            }
        )

    communities = []
    for c in OsshCommunity.objects.all():
        communities.append(
            {
                "name": getattr(c, "name", "") or "",
                "description": getattr(c, "description", "") or "",
                "url": getattr(c, "url", "") or getattr(c, "link", "") or "",
                "members": getattr(c, "members", "") or getattr(c, "member_count", "") or "",
                "tags": _tags(c),
            }
        )

    discussion_channels = []
    for ch in OsshDiscussionChannel.objects.all():
        discussion_channels.append(
            {
                "name": getattr(ch, "name", "") or "",
                "platform": getattr(ch, "platform", "") or getattr(ch, "source", "") or "",
                "invite_url": getattr(ch, "invite_url", "") or getattr(ch, "url", "") or "",
                "member_count": int(getattr(ch, "member_count", 0) or getattr(ch, "members", 0) or 0),
                "tags": _tags(ch),
            }
        )

    articles = []
    for a in OsshArticle.objects.all():
        articles.append(
            {
                "title": getattr(a, "title", "") or getattr(a, "name", "") or "",
                "category": getattr(a, "category", "") or "",
                "url": getattr(a, "url", "") or getattr(a, "link", "") or "",
                "tags": _tags(a),
            }
        )

    payload = {
        "site": {
            "source": "OWASP-BLT/BLT",
            "generated_from": "database",
        },
        "repos": repos,
        "communities": communities,
        "discussion_channels": discussion_channels,
        "articles": articles,
    }

    resp = JsonResponse(payload, json_dumps_params={"indent": 2})
    resp["Access-Control-Allow-Origin"] = "*"
    resp["Cache-Control"] = "public, max-age=300"
    return resp
