import json

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import UserProfile


class SendGridWebhookTestCase(TestCase):
    """Test SendGrid webhook handling"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.webhook_url = reverse("inbound_event_webhook_callback")

        # Create test user with email
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass")
        self.user_profile = UserProfile.objects.get(user=self.user)

    def test_webhook_updates_user_profile(self):
        """Test that webhook still updates user profile as before"""
        payload = [
            {
                "email": "test@example.com",
                "event": "bounce",
                "reason": "Invalid mailbox",
                "timestamp": "2024-01-01 12:00:00",
            }
        ]

        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        # Verify user profile was updated
        self.user_profile.refresh_from_db()
        self.assertEqual(self.user_profile.email_status, "bounce")
        self.assertEqual(self.user_profile.email_last_event, "bounce")
        self.assertEqual(self.user_profile.email_bounce_reason, "Invalid mailbox")
