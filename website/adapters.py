from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.urls import reverse


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_connect_redirect_url(self, request, socialaccount):
        """
        Returns the URL to redirect to after a social account connection.
        If there's an error, redirect to the connection error page.
        """
        # Check if there's an error in the request
        if hasattr(request, "socialaccount_connect_error"):
            return reverse("socialaccount_connection_error")

        # Default behavior - redirect to connections page
        return reverse("socialaccount_connections")
