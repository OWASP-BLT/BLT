from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from website.models import Organization, SlackIntegration


@login_required
def slack_apps_view(request, org_slug):
    organization = Organization.objects.get(slug=org_slug)
    slack_integrations = SlackIntegration.objects.filter(integration__organization=organization)

    context = {
        "organization": organization,
        "slack_integrations": slack_integrations,
    }
    return render(request, "organization/slack_apps.html", context)
