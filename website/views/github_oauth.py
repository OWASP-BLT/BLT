import logging

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


def github_oauth_login(request):
    """
    Direct GitHub OAuth login that forwards to GitHub OAuth authorization.
    Uses Django's built-in session mechanism without custom state management.
    """
    # Get GitHub OAuth settings from settings.py
    client_id = settings.SOCIALACCOUNT_PROVIDERS.get("github", {}).get("CLIENT_ID", "")

    if not client_id:
        messages.error(
            request, "GitHub authentication is temporarily unavailable. Please try again later or contact support."
        )
        logger.error("GitHub OAuth client_id missing in settings")
        return redirect("account_login")

    redirect_uri = getattr(settings, "CALLBACK_URL_FOR_GITHUB", "")

    if not redirect_uri:
        current_site = request.get_host()
        redirect_uri = f"{'https' if request.is_secure() else 'http'}://{current_site}/accounts/github/login/callback/"
        logger.info(f"Built callback URL from request: {redirect_uri}")

    try:
        # Construct the authorization URL with scope
        auth_url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope=user repo"
        )

        logger.info(f"OAuth Flow: Redirecting to GitHub (client_id: {client_id[:4]}...)")

        return redirect(auth_url)
    except Exception as e:
        logger.error(f"GitHub OAuth redirect error: {str(e)}")
        messages.error(request, "An error occurred during GitHub authentication. Please try again later.")
        return redirect("account_login")
