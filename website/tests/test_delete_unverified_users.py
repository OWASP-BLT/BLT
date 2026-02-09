from datetime import timedelta
from io import StringIO

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone


class DeleteUnverifiedUsersTest(TestCase):
    """Test suite for delete_unverified_users management command"""

    def setUp(self):
        """Set up test data before each test"""
        self.cutoff_days = 30
        self.cutoff_date = timezone.now() - timedelta(days=self.cutoff_days)

    def call_command(self, *args, **kwargs):
        """Helper to call the management command and capture output"""
        out = StringIO()
        err = StringIO()
        call_command("delete_unverified_users", *args, stdout=out, stderr=err, **kwargs)
        return out.getvalue(), err.getvalue()

    def test_delete_old_unverified_user(self):
        """Test that old unverified users are deleted"""
        # Create user older than threshold without verified email
        old_user = User.objects.create_user(username="oldunverified", email="old@example.com", password="testpass123")
        old_user.date_joined = self.cutoff_date - timedelta(days=5)
        old_user.save()

        # Create unverified email address
        EmailAddress.objects.create(user=old_user, email="old@example.com", verified=False, primary=True)

        # Run command without dry-run
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was deleted
        self.assertFalse(User.objects.filter(username="oldunverified").exists())
        self.assertIn("Successfully deleted", out)

    def test_keep_recent_unverified_user(self):
        """Test that recent unverified users are NOT deleted"""
        # Create user within threshold
        recent_user = User.objects.create_user(
            username="recentunverified", email="recent@example.com", password="testpass123"
        )
        recent_user.date_joined = timezone.now() - timedelta(days=2)
        recent_user.save()

        # Create unverified email address
        EmailAddress.objects.create(user=recent_user, email="recent@example.com", verified=False, primary=True)

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="recentunverified").exists())

    def test_keep_verified_user(self):
        """Test that verified users are NOT deleted regardless of age"""
        # Create old user with verified email
        verified_user = User.objects.create_user(
            username="verifieduser", email="verified@example.com", password="testpass123"
        )
        verified_user.date_joined = self.cutoff_date - timedelta(days=10)
        verified_user.save()

        # Create verified email address
        EmailAddress.objects.create(user=verified_user, email="verified@example.com", verified=True, primary=True)

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="verifieduser").exists())
        self.assertIn("No unverified users found", out)

    def test_keep_staff_user(self):
        """Test that staff users are NOT deleted"""
        # Create old staff user without verified email
        staff_user = User.objects.create_user(username="staffuser", email="staff@example.com", password="testpass123")
        staff_user.is_staff = True
        staff_user.date_joined = self.cutoff_date - timedelta(days=10)
        staff_user.save()

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="staffuser").exists())

    def test_keep_superuser(self):
        """Test that superusers are NOT deleted"""
        # Create old superuser without verified email
        superuser = User.objects.create_superuser(
            username="superuser", email="super@example.com", password="testpass123"
        )
        superuser.date_joined = self.cutoff_date - timedelta(days=10)
        superuser.save()

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="superuser").exists())

    def test_dry_run_no_deletion(self):
        """Test that dry-run mode doesn't actually delete users"""
        # Create old unverified user
        old_user = User.objects.create_user(username="testdryrun", email="dryrun@example.com", password="testpass123")
        old_user.date_joined = self.cutoff_date - timedelta(days=5)
        old_user.save()

        EmailAddress.objects.create(user=old_user, email="dryrun@example.com", verified=False, primary=True)

        # Run with dry-run
        out, err = self.call_command(days=self.cutoff_days, dry_run=True)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="testdryrun").exists())
        self.assertIn("DRY RUN", out)
        self.assertIn("Would delete", out)

    def test_minimum_days_enforcement(self):
        """Test that minimum 7 days is enforced"""
        # Create user
        user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        user.date_joined = timezone.now() - timedelta(days=3)
        user.save()

        # Try to run with less than 7 days
        out, err = self.call_command(days=5)

        # Verify error message
        self.assertIn("Minimum days must be 7 or greater", out)

        # Verify user still exists
        self.assertTrue(User.objects.filter(username="testuser").exists())

    def test_no_email_address_records(self):
        """Test deletion of users with no EmailAddress records at all"""
        # Create old user with no EmailAddress records
        old_user = User.objects.create_user(username="noemailuser", email="noemail@example.com", password="testpass123")
        old_user.date_joined = self.cutoff_date - timedelta(days=10)
        old_user.save()

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was deleted
        self.assertFalse(User.objects.filter(username="noemailuser").exists())

    def test_batch_processing(self):
        """Test that large number of users are processed in batches"""
        # Create multiple old unverified users
        for i in range(15):
            user = User.objects.create_user(
                username="batchuser{}".format(i), email="batch{}@example.com".format(i), password="testpass123"
            )
            user.date_joined = self.cutoff_date - timedelta(days=10)
            user.save()
            EmailAddress.objects.create(user=user, email="batch{}@example.com".format(i), verified=False, primary=True)

        # Run command with small batch size
        out, err = self.call_command(days=self.cutoff_days, batch_size=5)

        # Verify all users were deleted
        for i in range(15):
            self.assertFalse(User.objects.filter(username="batchuser{}".format(i)).exists())

        # Verify batch processing occurred
        self.assertIn("Batch", out)

    def test_mixed_verified_status(self):
        """Test with users having multiple email addresses with mixed verification"""
        # Create user with one verified and one unverified email
        user = User.objects.create_user(username="mixeduser", email="mixed@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="mixed@example.com", verified=True, primary=True)
        EmailAddress.objects.create(user=user, email="mixed2@example.com", verified=False, primary=False)

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # User should NOT be deleted (has at least one verified email)
        self.assertTrue(User.objects.filter(username="mixeduser").exists())

    def test_output_format_dry_run(self):
        """Test that dry-run output contains expected information"""
        # Create sample user
        user = User.objects.create_user(username="outputtest", email="output@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="output@example.com", verified=False, primary=True)

        # Run dry-run
        out, err = self.call_command(days=self.cutoff_days, dry_run=True)

        # Check output contains key information
        self.assertIn("DRY RUN", out)
        self.assertIn("outputtest", out)
        self.assertIn("Sample users that would be deleted", out)
        self.assertIn("Related objects that would be deleted", out)
        self.assertIn("Deletion statistics", out)

    def test_no_users_to_delete(self):
        """Test command when no users meet deletion criteria"""
        # Create only verified or recent users
        user1 = User.objects.create_user(username="verified", email="verified@example.com", password="testpass123")
        EmailAddress.objects.create(user=user1, email="verified@example.com", verified=True, primary=True)

        user2 = User.objects.create_user(username="recent", email="recent@example.com", password="testpass123")
        user2.date_joined = timezone.now()
        user2.save()

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify appropriate message
        self.assertIn("No unverified users found", out)

    def test_email_address_deletion(self):
        """Test that EmailAddress records are properly deleted along with users"""
        # Create user with multiple email addresses
        user = User.objects.create_user(username="multiemail", email="multi@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="multi1@example.com", verified=False, primary=True)
        EmailAddress.objects.create(user=user, email="multi2@example.com", verified=False, primary=False)

        initial_email_count = EmailAddress.objects.count()

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify EmailAddress records were deleted
        self.assertEqual(EmailAddress.objects.count(), initial_email_count - 2)
        self.assertFalse(EmailAddress.objects.filter(user__username="multiemail").exists())

    def test_keep_users_with_activity(self):
        """Test that users with activity (issues, points, etc.) are NOT deleted"""
        from website.models import Points

        # Create old unverified user
        active_user = User.objects.create_user(
            username="activeuser", email="active@example.com", password="testpass123"
        )
        active_user.date_joined = self.cutoff_date - timedelta(days=10)
        active_user.save()

        # Create unverified email
        EmailAddress.objects.create(user=active_user, email="active@example.com", verified=False, primary=True)

        # Add activity: create points for this user
        Points.objects.create(user=active_user, score=10)

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted due to activity
        self.assertTrue(User.objects.filter(username="activeuser").exists())

    def test_keep_users_with_recent_login(self):
        """Test that users with recent login activity are NOT deleted"""
        # Create old unverified user with recent login
        recent_login_user = User.objects.create_user(
            username="recentlogin", email="recentlogin@example.com", password="testpass123"
        )
        recent_login_user.date_joined = self.cutoff_date - timedelta(days=10)
        recent_login_user.last_login = timezone.now() - timedelta(days=5)  # Recent login
        recent_login_user.save()

        # Create unverified email
        EmailAddress.objects.create(
            user=recent_login_user, email="recentlogin@example.com", verified=False, primary=True
        )

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted due to recent login
        self.assertTrue(User.objects.filter(username="recentlogin").exists())
