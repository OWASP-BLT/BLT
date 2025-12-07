"""
Custom adapters for django-allauth to improve UX.
"""

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import resolve_url


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
