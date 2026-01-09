"""
API views for trademark matching.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from website.models import Organization, TrademarkMatch
from website.services.trademark_integration import get_trademark_report


@require_GET
def trademark_report_api(request):
    """
    JSON API endpoint for trademark reports.

    GET /api/trademark-report/?name=CompanyName
    Returns JSON with matches and detailed report.
    """
    name = request.GET.get("name", "").strip()
    if not name:
        return JsonResponse(
            {"error": "Missing 'name' query parameter"},
            status=400,
        )

    report = get_trademark_report(name)
    return JsonResponse(report)


@require_GET
@login_required
def organization_trademark_check(request, org_id):
    """
    JSON API to get trademark matches for a specific organization.

    GET /api/organization/{org_id}/trademarks/
    """
    org = get_object_or_404(Organization, id=org_id)

    matches = TrademarkMatch.objects.filter(organization=org).order_by("-similarity_score")

    data = {
        "organization_id": org.id,
        "organization_name": org.name,
        "total_matches": matches.count(),
        "high_risk_count": matches.filter(risk_level="high").count(),
        "matches": [
            {
                "id": m.id,
                "matched_trademark": m.matched_trademark_name,
                "similarity_score": m.similarity_score,
                "risk_level": m.risk_level,
                "status": m.status,
                "is_reviewed": m.is_reviewed,
                "checked_at": m.checked_at.isoformat(),
            }
            for m in matches
        ],
    }

    return JsonResponse(data)


@require_GET
@login_required
def website_trademark_check(request, website_id):
    """
    JSON API to get trademark matches for a specific website.

    GET /api/website/{website_id}/trademarks/
    """
    website = get_object_or_404(Website, id=website_id)

    matches = TrademarkMatch.objects.filter(website=website).order_by("-similarity_score")

    data = {
        "website_id": website.id,
        "website_name": website.name,
        "total_matches": matches.count(),
        "high_risk_count": matches.filter(risk_level="high").count(),
        "matches": [
            {
                "id": m.id,
                "matched_trademark": m.matched_trademark_name,
                "similarity_score": m.similarity_score,
                "risk_level": m.risk_level,
                "status": m.status,
                "is_reviewed": m.is_reviewed,
                "checked_at": m.checked_at.isoformat(),
            }
            for m in matches
        ],
    }

    return JsonResponse(data)
