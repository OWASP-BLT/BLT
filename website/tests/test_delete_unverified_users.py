from datetime import timedelta
from io import StringIO

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone


class DeleteUnverifiedUsersCommandTest(TestCase):
    def setUp(self):
        old_date = timezone.now() - timedelta(days=60)

        # Old unverified user (should be deleted with default 30-day threshold)
        self.old_unverified = User.objects.create_user(
            username="old_unverified", email="old@example.com", password="testpass"
        )
        self.old_unverified.date_joined = old_date
        self.old_unverified.save(update_fields=["date_joined"])
        EmailAddress.objects.create(user=self.old_unverified, email="old@example.com", verified=False, primary=True)

        # Old verified user (should NOT be deleted)
        self.old_verified = User.objects.create_user(
            username="old_verified", email="verified@example.com", password="testpass"
        )
        self.old_verified.date_joined = old_date
        self.old_verified.save(update_fields=["date_joined"])
        EmailAddress.objects.create(user=self.old_verified, email="verified@example.com", verified=True, primary=True)

        # Recent unverified user (should NOT be deleted -- not past cutoff)
        self.recent_unverified = User.objects.create_user(
            username="recent_unverified", email="recent@example.com", password="testpass"
        )
        EmailAddress.objects.create(
            user=self.recent_unverified, email="recent@example.com", verified=False, primary=True
        )

        # Staff user with unverified email (should NOT be deleted)
        self.staff_user = User.objects.create_user(
            username="staff_user", email="staff@example.com", password="testpass", is_staff=True
        )
        self.staff_user.date_joined = old_date
        self.staff_user.save(update_fields=["date_joined"])
        EmailAddress.objects.create(user=self.staff_user, email="staff@example.com", verified=False, primary=True)

        # Superuser with unverified email (should NOT be deleted)
        self.superuser = User.objects.create_superuser(
            username="admin_user", email="admin@example.com", password="testpass"
        )
        self.superuser.date_joined = old_date
        self.superuser.save(update_fields=["date_joined"])
        EmailAddress.objects.create(user=self.superuser, email="admin@example.com", verified=False, primary=True)

    def test_deletes_old_unverified_users(self):
        """Should delete users with unverified email who joined before the cutoff."""
        call_command("delete_unverified_users")
        self.assertFalse(User.objects.filter(username="old_unverified").exists())

    def test_preserves_verified_users(self):
        """Should preserve users who have a verified email address."""
        call_command("delete_unverified_users")
        self.assertTrue(User.objects.filter(username="old_verified").exists())

    def test_preserves_recent_unverified_users(self):
        """Should preserve unverified users who joined within the cutoff period."""
        call_command("delete_unverified_users")
        self.assertTrue(User.objects.filter(username="recent_unverified").exists())

    def test_preserves_staff_users(self):
        """Should never delete staff users regardless of verification status."""
        call_command("delete_unverified_users")
        self.assertTrue(User.objects.filter(username="staff_user").exists())

    def test_preserves_superusers(self):
        """Should never delete superusers regardless of verification status."""
        call_command("delete_unverified_users")
        self.assertTrue(User.objects.filter(username="admin_user").exists())

    def test_dry_run_does_not_delete(self):
        """Dry run should report candidates without actually deleting them."""
        out = StringIO()
        call_command("delete_unverified_users", dry_run=True, stdout=out)
        self.assertTrue(User.objects.filter(username="old_unverified").exists())
        self.assertIn("DRY RUN", out.getvalue())

    def test_custom_days_argument(self):
        """Should respect the --days argument for cutoff calculation."""
        call_command("delete_unverified_users", days=90)
        # 60-day-old user should NOT be deleted with 90-day threshold
        self.assertTrue(User.objects.filter(username="old_unverified").exists())

    def test_rejects_non_positive_days(self):
        """Should raise CommandError when --days is zero or negative."""
        with self.assertRaises(CommandError):
            call_command("delete_unverified_users", days=0)
        with self.assertRaises(CommandError):
            call_command("delete_unverified_users", days=-5)

    def test_deletes_users_with_no_email_record(self):
        """Users with no EmailAddress record have no verified email and should be deleted."""
        old_date = timezone.now() - timedelta(days=60)
        no_email = User.objects.create_user(username="no_email_record", password="testpass")
        no_email.date_joined = old_date
        no_email.save(update_fields=["date_joined"])

        call_command("delete_unverified_users")
        self.assertFalse(User.objects.filter(username="no_email_record").exists())

    def test_preserves_user_with_at_least_one_verified_email(self):
        """User with multiple emails where at least one is verified should be preserved."""
        old_date = timezone.now() - timedelta(days=60)
        multi_email = User.objects.create_user(username="multi_email", email="primary@example.com", password="testpass")
        multi_email.date_joined = old_date
        multi_email.save(update_fields=["date_joined"])
        EmailAddress.objects.create(user=multi_email, email="primary@example.com", verified=False, primary=True)
        EmailAddress.objects.create(user=multi_email, email="secondary@example.com", verified=True, primary=False)

        call_command("delete_unverified_users")
        self.assertTrue(User.objects.filter(username="multi_email").exists())

    def test_output_message_on_success(self):
        """Should print a success message with the count of deleted users."""
        out = StringIO()
        call_command("delete_unverified_users", stdout=out)
        output = out.getvalue()
        self.assertIn("Successfully deleted", output)
        self.assertIn("1 unverified user", output)

    def test_dry_run_shows_usernames(self):
        """Dry run should list usernames of users that would be deleted."""
        out = StringIO()
        call_command("delete_unverified_users", dry_run=True, stdout=out)
        self.assertIn("old_unverified", out.getvalue())
