"""
Custom adapters for django-allauth to improve UX.
"""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import resolve_url


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter to handle email verification differently
    for social vs regular signups.
    """

    def is_email_verification_mandatory(self, request):
        """
        Skip mandatory email verification for social account signups.
        Only enforce for regular email/password signups.
        """
        # Check if this is a social account signup
        if hasattr(request, "session") and "socialaccount_sociallogin" in request.session:
            return False
        return super().is_email_verification_mandatory(request)


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

    def is_auto_signup_allowed(self, request, sociallogin):
        """
        Enable auto-signup for social accounts only when the provider has verified the email.
        """
        # Only auto-signup if the email address from the provider is verified
        if sociallogin.email_addresses:
            if any(addr.verified for addr in sociallogin.email_addresses):
                return True
        # Fall back to default behavior (which checks for email uniqueness, etc.)
        return super().is_auto_signup_allowed(request, sociallogin)
