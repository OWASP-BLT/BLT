from allauth.socialaccount.models import SocialApp


def oauth_providers_status(request):

    github_oauth_available = SocialApp.objects.filter(
        provider="github"
    ).exists()

    return {
        "github_oauth_available": github_oauth_available
    }