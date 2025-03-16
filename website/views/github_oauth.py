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
        # Generate and store state parameter in session
        import secrets

        state = secrets.token_urlsafe(32)
        request.session["github_oauth_state"] = state

        # Construct the authorization URL with scope
        auth_url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope=user repo"
            f"&state={state}"
        )

        logger.info(f"OAuth Flow: Redirecting to GitHub (client_id: {client_id[:4]}...)")

        return redirect(auth_url)
    except Exception as e:
        logger.error(f"GitHub OAuth redirect error: {str(e)}")
        messages.error(request, "An error occurred during GitHub authentication. Please try again later.")
        return redirect("account_login")


def github_oauth_callback(request):
    """
    Custom callback handler for GitHub OAuth to validate the state parameter.
    After validating the state, it redirects to the standard allauth callback.
    """
    # Get state from query parameters
    state = request.GET.get("state")

    stored_state = request.session.get("github_oauth_state")

    # Remove state from session to prevent replay attacks
    if "github_oauth_state" in request.session:
        del request.session["github_oauth_state"]

    if not state or not stored_state or state != stored_state:
        logger.error("GitHub OAuth callback received invalid state parameter")
        messages.error(
            request,
            "Security validation failed. Please try logging in again. "
            "This could be due to an expired session or a potential security issue.",
        )
        return redirect("account_login")

    logger.info("GitHub OAuth state parameter validated successfully")

    # Continue to the allauth socialaccount_connections view which will complete the OAuth flow
    try:
        from allauth.socialaccount.providers.github.views import oauth2_callback

        return oauth2_callback(request)
    except ImportError:
        return redirect("socialaccount_connections")
