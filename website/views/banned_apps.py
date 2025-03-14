from django.http import JsonResponse
from django.views.generic import TemplateView

from website.models import BannedApp


class BannedAppsView(TemplateView):
    template_name = "banned_apps.html"


def search_banned_apps(request):
    country = request.GET.get("country", "").strip()
    if not country:
        return JsonResponse({"apps": []})

    apps = BannedApp.objects.filter(country_name__icontains=country, is_active=True).values(
        "app_name", "app_type", "country_name", "ban_reason", "ban_date", "source_url"
    )

    return JsonResponse({"apps": list(apps)})
