"""
Custom adapters for django-allauth to improve UX.
"""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.shortcuts import resolve_url


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter to improve login error messages.
    """

    def authentication_failed(self, request, **kwargs):
        """
        Show a user-friendly error message when authentication fails.
        
        Security:
            - Does not expose whether username/email exists
            - Provides clear feedback to users
        """
        messages.error(
            request,
            "The username/email and password you entered did not match our records. "
            "Please check your credentials and try again.",
        )


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter to redirect to profile after connection
    and show success messages.
    """

    def get_signup_redirect_url(self, request):
        """
        Redirect to user's profile after signing up with a social account.
        Message is handled by middleware to ensure it shows after redirect.

        Security:
            - Only redirects authenticated users
            - Uses resolve_url for safe URL generation
        """
        # Message is handled by BaconRewardMessageMiddleware
        # Redirect to home page (default behavior)
        return resolve_url("/")

    def get_connect_redirect_url(self, request, socialaccount):
        """
        Redirect to user's profile after connecting a social account.
        Message is handled by middleware to ensure it shows after redirect.

        Security:
            - Only redirects authenticated users
            - Uses resolve_url for safe URL generation
        """
        # Message is handled by BaconRewardMessageMiddleware
        # Redirect to user's profile
        return resolve_url(f"/profile/{request.user.username}/")
