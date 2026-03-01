from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse


class MessagingNotificationTest(TestCase):
    """Tests for the messaging notification system."""

    def setUp(self):
        """Set up users and log in the sender."""
        self.user1 = User.objects.create_user(username="sender", email="sender@example.com", password="password")
        self.user2 = User.objects.create_user(username="recipient", email="recipient@example.com", password="password")
        self.client.login(username="sender", password="password")

    def test_start_thread_sends_email(self):
        """Verify that starting a thread triggers an email to the correct recipient."""
        # Initial check: No emails in outbox
        self.assertEqual(len(mail.outbox), 0)

        # Trigger the view
        url = reverse("start_thread", kwargs={"user_id": self.user2.id})
        response = self.client.post(url)

        # 1. Verify response is successful
        self.assertEqual(response.status_code, 200)

        # 2. Verify one email was sent
        self.assertEqual(len(mail.outbox), 1)

        # 3. Verify email metadata and content
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, f"New encrypted chat from {self.user1.username} on OWASP BLT")
        self.assertIn(self.user2.email, sent_email.to)
        self.assertIn(self.user2.username, sent_email.body)
        self.assertIn(self.user1.username, sent_email.body)
