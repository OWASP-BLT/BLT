from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Thread


class EncryptedChatEmailTest(TestCase):
    """Test suite for encrypted chat email notification functionality"""

    def setUp(self):
        """Set up test users and client"""
        self.client = Client()
        # Create sender user
        self.sender = User.objects.create_user(
            username="sender_user", email="sender@example.com", password="testpass123"
        )
        # Create recipient user
        self.recipient = User.objects.create_user(
            username="recipient_user", email="recipient@example.com", password="testpass123"
        )
        # Login as sender
        self.client.login(username="sender_user", password="testpass123")

    def test_email_sent_when_new_thread_created(self):
        """Test that an email is sent when a new encrypted chat thread is started"""
        # Clear any existing emails
        mail.outbox = []

        # Start a new thread with the recipient
        response = self.client.post(reverse("start_thread", kwargs={"user_id": self.recipient.id}))

        # Check response is successful
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data["success"])
        self.assertIn("thread_id", response_data)

        # Verify thread was created
        thread = Thread.objects.get(id=response_data["thread_id"])
        self.assertEqual(thread.participants.count(), 2)
        self.assertIn(self.sender, thread.participants.all())
        self.assertIn(self.recipient, thread.participants.all())

        # Check that exactly one email was sent
        self.assertEqual(len(mail.outbox), 1)

        # Verify email details
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, "New encrypted chat from sender_user on OWASP BLT")
        self.assertEqual(sent_email.to, ["recipient@example.com"])
        self.assertIn("sender_user", sent_email.body)
        self.assertIn("recipient_user", sent_email.body)
        self.assertIn("/messaging/", sent_email.body)

    def test_no_email_sent_when_thread_already_exists(self):
        """Test that no email is sent when a thread already exists between users"""
        # Create an existing thread between the users
        thread = Thread.objects.create()
        thread.participants.set([self.sender, self.recipient])

        # Clear any existing emails
        mail.outbox = []

        # Try to start a thread again with the same recipient
        response = self.client.post(reverse("start_thread", kwargs={"user_id": self.recipient.id}))

        # Check response is successful and returns the existing thread
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data["success"])
        self.assertEqual(response_data["thread_id"], thread.id)

        # Check that no email was sent (thread already existed)
        self.assertEqual(len(mail.outbox), 0)

    def test_no_email_sent_when_recipient_has_no_email(self):
        """Test that no email is sent when the recipient has no email address"""
        # Create a recipient without an email
        recipient_no_email = User.objects.create_user(username="no_email_user", email="", password="testpass123")

        # Clear any existing emails
        mail.outbox = []

        # Start a new thread with the recipient who has no email
        response = self.client.post(reverse("start_thread", kwargs={"user_id": recipient_no_email.id}))

        # Check response is successful
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data["success"])

        # Verify thread was created
        thread = Thread.objects.get(id=response_data["thread_id"])
        self.assertEqual(thread.participants.count(), 2)

        # Check that no email was sent (recipient has no email)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_contains_correct_link(self):
        """Test that the email contains the correct link to the messaging page"""
        # Clear any existing emails
        mail.outbox = []

        # Start a new thread
        response = self.client.post(reverse("start_thread", kwargs={"user_id": self.recipient.id}))

        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)

        # Verify the email contains the messaging URL
        sent_email = mail.outbox[0]
        self.assertIn("messaging", sent_email.body.lower())
        # Check that HTML version also has the link
        self.assertIn("messaging", sent_email.alternatives[0][0].lower())

    def test_start_thread_requires_post_method(self):
        """Test that start_thread endpoint only accepts POST requests"""
        # Try GET request
        response = self.client.get(reverse("start_thread", kwargs={"user_id": self.recipient.id}))

        # Should return error for non-POST request
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        self.assertIn("error", response_data)

    def test_start_thread_requires_authentication(self):
        """Test that start_thread requires user to be logged in"""
        # Logout
        self.client.logout()

        # Try to start a thread without authentication
        response = self.client.post(reverse("start_thread", kwargs={"user_id": self.recipient.id}))

        # Should redirect to login page (302) or return unauthorized
        self.assertIn(response.status_code, [302, 401, 403])

    def test_email_template_uses_correct_branding(self):
        """Test that the email uses OWASP BLT branding color"""
        # Clear any existing emails
        mail.outbox = []

        # Start a new thread
        self.client.post(reverse("start_thread", kwargs={"user_id": self.recipient.id}))

        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)

        # Verify the email HTML contains the BLT brand color
        sent_email = mail.outbox[0]
        html_content = sent_email.alternatives[0][0]
        # Check for the brand color #e74c3c
        self.assertIn("#e74c3c", html_content)
