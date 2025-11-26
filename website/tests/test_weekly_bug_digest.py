from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from website.models import Domain, Issue, Organization


class WeeklyBugDigestTestCase(TestCase):
    """Test cases for the weekly bug digest email command"""

    def setUp(self):
        """Set up test data"""
        # Create organization
        self.org = Organization.objects.create(
            name="Test Organization",
            slug="test-org",
            url="https://test.org",
            is_active=True,
        )

        # Create domains
        self.domain1 = Domain.objects.create(
            name="test1.com",
            url="https://test1.com",
            organization=self.org,
            is_active=True,
        )

        self.domain2 = Domain.objects.create(
            name="test2.com",
            url="https://test2.com",
            organization=self.org,
            is_active=True,
        )

        # Create users
        self.user1 = User.objects.create_user(
            username="testuser1",
            email="test1@example.com",
            password="testpass123",
        )

        self.user2 = User.objects.create_user(
            username="testuser2",
            email="test2@example.com",
            password="testpass123",
        )

        self.user_no_email = User.objects.create_user(
            username="noemail",
            password="testpass123",
        )

        # Subscribe users to domains
        self.user1.userprofile.subscribed_domains.add(self.domain1)
        self.user2.userprofile.subscribed_domains.add(self.domain1, self.domain2)

        # Create bugs
        self.bug1 = Issue.objects.create(
            domain=self.domain1,
            url="https://test1.com/bug1",
            description="Test bug 1 - Security issue",
            label=4,  # Security
            user=self.user1,
            is_hidden=False,
        )

        self.bug2 = Issue.objects.create(
            domain=self.domain2,
            url="https://test2.com/bug2",
            description="Test bug 2 - Functional issue",
            label=2,  # Functional
            user=self.user2,
            is_hidden=False,
        )

    def test_command_sends_emails_to_followers(self):
        """Test that emails are sent to users who follow domains"""
        # Clear mail outbox
        mail.outbox = []

        # Run command
        call_command("send_weekly_bug_digest", days=7)

        # Check that emails were sent (user1 subscribed to domain1, user2 to both)
        self.assertEqual(len(mail.outbox), 2, "Should send 2 emails to 2 subscribed users")

        # Check recipients match subscriptions
        recipients = [email.to[0] for email in mail.outbox]
        self.assertIn("test1@example.com", recipients, "User1 should receive email")
        self.assertIn("test2@example.com", recipients, "User2 should receive email")

    def test_command_respects_unsubscribed_users(self):
        """Test that unsubscribed users don't receive emails"""
        # Unsubscribe user1
        self.user1.userprofile.email_unsubscribed = True
        self.user1.userprofile.save()

        mail.outbox = []
        call_command("send_weekly_bug_digest", days=7)

        # Only user2 should receive email
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], "test2@example.com")

    def test_command_skips_users_without_email(self):
        """Test that users without email addresses are skipped"""
        # Subscribe user without email
        self.user_no_email.userprofile.subscribed_domains.add(self.domain1)

        mail.outbox = []
        call_command("send_weekly_bug_digest", days=7)

        # Should still send to users with emails
        self.assertEqual(len(mail.outbox), 2)
        recipients = [email.to[0] for email in mail.outbox]
        self.assertNotIn(None, recipients)

    def test_command_filters_by_date_range(self):
        """Test that only bugs within the date range are included"""
        # Create an old bug (outside date range)
        old_bug = Issue.objects.create(
            domain=self.domain1,
            url="https://test1.com/old",
            description="Old bug",
            user=self.user1,
            is_hidden=False,
        )
        # Manually set created date to 10 days ago
        old_bug.created = timezone.now() - timedelta(days=10)
        old_bug.save()

        mail.outbox = []
        call_command("send_weekly_bug_digest", days=7)

        # Check that old bug is not in email
        for email in mail.outbox:
            self.assertNotIn("Old bug", email.body)

    def test_command_excludes_hidden_bugs(self):
        """Test that hidden bugs are not included in digest"""
        # Create hidden bug
        hidden_bug = Issue.objects.create(
            domain=self.domain1,
            url="https://test1.com/hidden",
            description="Hidden bug - should not appear",
            user=self.user1,
            is_hidden=True,
        )

        mail.outbox = []
        call_command("send_weekly_bug_digest", days=7)

        # Check that hidden bug is not in email
        for email in mail.outbox:
            self.assertNotIn("Hidden bug", email.body)

    def test_command_excludes_inactive_organizations(self):
        """Test that inactive organizations are skipped"""
        # Deactivate organization
        self.org.is_active = False
        self.org.save()

        mail.outbox = []
        call_command("send_weekly_bug_digest", days=7)

        # No emails should be sent
        self.assertEqual(len(mail.outbox), 0)

    def test_command_excludes_inactive_domains(self):
        """Test that bugs from inactive domains are not included"""
        # Deactivate domain1
        self.domain1.is_active = False
        self.domain1.save()

        mail.outbox = []
        call_command("send_weekly_bug_digest", days=7)

        # Should send one email to user2 for active domain2
        self.assertEqual(len(mail.outbox), 1, "Should send email to user2 for active domain2")
        
        # Check emails don't contain bugs from inactive domain
        for email in mail.outbox:
            self.assertNotIn("test1.com", email.body)
            # Verify active domain bugs are still included
            self.assertIn("test2.com", email.body)

    def test_command_with_no_bugs(self):
        """Test command behavior when there are no bugs"""
        # Delete all bugs
        Issue.objects.all().delete()

        mail.outbox = []
        call_command("send_weekly_bug_digest", days=7)

        # No emails should be sent when there are no bugs
        self.assertEqual(len(mail.outbox), 0, "Should not send emails when no bugs exist")

    def test_command_with_no_followers(self):
        """Test command behavior when there are no followers"""
        # Remove all subscriptions
        self.user1.userprofile.subscribed_domains.clear()
        self.user2.userprofile.subscribed_domains.clear()

        mail.outbox = []
        call_command("send_weekly_bug_digest", days=7)

        # No emails should be sent
        self.assertEqual(len(mail.outbox), 0)

    def test_email_content_includes_bug_details(self):
        """Test that email contains bug details"""
        mail.outbox = []
        call_command("send_weekly_bug_digest", days=7)

        # Check first email
        email = mail.outbox[0]

        # Check subject
        self.assertIn("Test Organization", email.subject)
        self.assertIn("Weekly Bug Report Digest", email.subject)

        # Check body contains bug descriptions
        self.assertTrue(
            "Test bug 1" in email.body or "Test bug 2" in email.body,
            "Email should contain bug descriptions",
        )

    def test_email_has_html_alternative(self):
        """Test that email includes HTML version"""
        mail.outbox = []
        call_command("send_weekly_bug_digest", days=7)

        email = mail.outbox[0]

        # Check that HTML alternative exists
        self.assertEqual(len(email.alternatives), 1)
        html_content, content_type = email.alternatives[0]
        self.assertEqual(content_type, "text/html")
        self.assertIn("<!DOCTYPE html>", html_content)

    def test_dry_run_mode(self):
        """Test that dry-run mode doesn't send emails"""
        mail.outbox = []
        call_command("send_weekly_bug_digest", days=7, dry_run=True)

        # No emails should be sent in dry-run mode
        self.assertEqual(len(mail.outbox), 0)

    def test_custom_days_parameter(self):
        """Test command with custom days parameter"""
        # Create bug from 5 days ago
        bug = Issue.objects.create(
            domain=self.domain1,
            url="https://test1.com/recent",
            description="Recent bug",
            user=self.user1,
            is_hidden=False,
        )
        bug.created = timezone.now() - timedelta(days=5)
        bug.save()

        mail.outbox = []

        # Should include bug with days=7
        call_command("send_weekly_bug_digest", days=7)
        self.assertGreater(len(mail.outbox), 0)

        mail.outbox = []

        # Should not include bug with days=3
        call_command("send_weekly_bug_digest", days=3)
        for email in mail.outbox:
            self.assertNotIn("Recent bug", email.body)

    def test_specific_organization_filter(self):
        """Test filtering by specific organization"""
        # Create another organization
        org2 = Organization.objects.create(
            name="Other Org",
            slug="other-org",
            url="https://other.org",
            is_active=True,
        )

        domain3 = Domain.objects.create(
            name="other.com",
            url="https://other.com",
            organization=org2,
            is_active=True,
        )

        Issue.objects.create(
            domain=domain3,
            url="https://other.com/bug",
            description="Other org bug",
            user=self.user1,
            is_hidden=False,
        )

        self.user1.userprofile.subscribed_domains.add(domain3)

        mail.outbox = []
        call_command("send_weekly_bug_digest", days=7, organization="test-org")

        # Should only send emails for test-org
        for email in mail.outbox:
            self.assertIn("Test Organization", email.subject)
            self.assertNotIn("Other Org", email.subject)

    def test_error_handling(self):
        """Test that errors are handled gracefully"""
        with patch("django.core.mail.EmailMultiAlternatives.send") as mock_send:
            mock_send.side_effect = Exception("SMTP error")
            mail.outbox = []
            
            # Command should not crash and should continue processing
            try:
                call_command("send_weekly_bug_digest", days=7)
                command_completed = True
            except Exception:
                command_completed = False
            
            # Verify command completed despite errors
            self.assertTrue(command_completed, "Command should complete even with email errors")
            # Verify send was attempted for all recipients (2 users should receive emails)
            self.assertEqual(mock_send.call_count, 2, "Should attempt to send to all recipients despite errors")

    def test_inactive_users_are_skipped(self):
        """Test that inactive users don't receive emails"""
        self.user1.is_active = False
        self.user1.save()

        mail.outbox = []
        call_command("send_weekly_bug_digest", days=7)

        # Only active user should receive email
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], "test2@example.com")

    def test_zero_days_parameter_validation(self):
        """Test that zero or negative days parameter is handled"""
        mail.outbox = []
        call_command("send_weekly_bug_digest", days=0)
        
        # No emails should be sent
        self.assertEqual(len(mail.outbox), 0)
