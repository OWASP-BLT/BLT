from django.http import JsonResponse
from django.views.decorators.http import require_GET

from website.services.trademark_integration import get_trademark_report


@require_GET
def trademark_report_view(request):
    """
    Return a JSON trademark report for a given website/company name.

    GET /api/trademark-report/?name=BugHeist
    """
    name = request.GET.get("name", "").strip()
    if not name:
        return JsonResponse(
            {"error": "Missing 'name' query parameter"},
            status=400,
        )

    report = get_trademark_report(name)
    return JsonResponse(report)
