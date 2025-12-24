"""
Custom account adapter for django-allauth to improve login error handling
and email verification messaging.
"""

from allauth.account.adapter import DefaultAccountAdapter
from django.contrib import messages
from django.shortcuts import resolve_url


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter to provide better error messages and UX.
    """

    def add_message(self, request, level, message_tag, message, **kwargs):
        """
        Override to provide cleaner error messages for login failures.
        """
        # Clean up generic error messages for better UX
        if message_tag == "account_login_failed":
            message = "Invalid username/email or password. Please check your credentials and try again."
        elif message_tag == "account_email_verification_sent":
            message = "We've sent a verification email to your address. Please check your inbox and click the verification link to activate your account."
        
        return super().add_message(request, level, message_tag, message, **kwargs)

    def get_email_confirmation_redirect_url(self, request):
        """
        Redirect after email confirmation to a user-friendly page.
        """
        return resolve_url("/")

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        """
        Override to customize email confirmation behavior.
        """
        super().send_confirmation_mail(request, emailconfirmation, signup)
        
        # Add a user-friendly message
        if signup:
            messages.success(
                request,
                "Account created successfully! Please check your email to verify your account before signing in."
            )