from allauth.socialaccount.models import SocialApp
from django.db.utils import ProgrammingError, OperationalError

def oauth_providers_status(request):
    try:
        github_oauth_available = SocialApp.objects.filter(provider="github").exists()
    except (ProgrammingError, OperationalError):
        github_oauth_available = False

    return {
        "github_oauth_available": github_oauth_available
    }