from datetime import timedelta
from io import StringIO

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from comments.models import Comment
from website.models import (
    Activity,
    ActivityLog,
    BaconToken,
    Bid,
    Contribution,
    DailyStatusReport,
    Domain,
    Hunt,
    InviteFriend,
    InviteOrganization,
    Issue,
    JoinRequest,
    Organization,
    OrganizationAdmin,
    SearchHistory,
    TimeLog,
    UserProfile,
    Wallet,
    Winner,
)


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

    def test_batch_size_validation(self):
        """Test that batch_size must be at least 1"""
        # Create user
        user = User.objects.create_user(username="testuser2", email="test2@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        # Try to run with batch_size = 0
        out, err = self.call_command(days=self.cutoff_days, batch_size=0)

        # Verify error message
        self.assertIn("Batch size must be 1 or greater", out)

        # Verify user still exists
        self.assertTrue(User.objects.filter(username="testuser2").exists())

        # Try to run with negative batch_size
        out, err = self.call_command(days=self.cutoff_days, batch_size=-5)

        # Verify error message
        self.assertIn("Batch size must be 1 or greater", out)

        # Verify user still exists
        self.assertTrue(User.objects.filter(username="testuser2").exists())

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

    def test_keep_users_with_comments(self):
        """Test that users with comments are NOT deleted"""
        # Create old unverified user
        user = User.objects.create_user(username="commenter", email="commenter@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="commenter@example.com", verified=False, primary=True)

        # Create UserProfile and Comment
        profile = UserProfile.objects.create(user=user)
        Comment.objects.create(author_fk=profile, text="Test comment")

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="commenter").exists())

    def test_keep_users_with_bids(self):
        """Test that users with bids are NOT deleted"""
        user = User.objects.create_user(username="bidder", email="bidder@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="bidder@example.com", verified=False, primary=True)

        # Create bid
        Bid.objects.create(user=user, issue_url="https://github.com/test/issue/1", amount_bch=0.5)

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="bidder").exists())

    def test_keep_users_with_organization_admin(self):
        """Test that organization admins are NOT deleted"""
        user = User.objects.create_user(username="orgadmin", email="orgadmin@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="orgadmin@example.com", verified=False, primary=True)

        # Create organization with user as admin
        Organization.objects.create(admin=user, name="Test Org", url="https://testorg.com")

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="orgadmin").exists())

    def test_keep_users_with_organization_manager(self):
        """Test that organization managers are NOT deleted"""
        user = User.objects.create_user(username="orgmanager", email="orgmanager@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="orgmanager@example.com", verified=False, primary=True)

        # Create organization and add user as manager
        org = Organization.objects.create(name="Test Org 2", url="https://testorg2.com")
        org.managers.add(user)

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="orgmanager").exists())

    def test_keep_users_with_organization_admin_role(self):
        """Test that OrganizationAdmin role users are NOT deleted"""
        user = User.objects.create_user(
            username="orgadminrole", email="orgadminrole@example.com", password="testpass123"
        )
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="orgadminrole@example.com", verified=False, primary=True)

        # Create OrganizationAdmin role
        org = Organization.objects.create(name="Test Org 3", url="https://testorg3.com")
        OrganizationAdmin.objects.create(user=user, organization=org, role=0)

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="orgadminrole").exists())

    def test_keep_users_with_join_requests(self):
        """Test that users with organization join requests are NOT deleted"""
        user = User.objects.create_user(username="joiner", email="joiner@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="joiner@example.com", verified=False, primary=True)

        # Create join request
        org = Organization.objects.create(name="Test Org 4", url="https://testorg4.com")
        JoinRequest.objects.create(user=user, team=org)

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="joiner").exists())

    def test_keep_users_with_sent_invites(self):
        """Test that users who sent friend invites are NOT deleted"""
        user = User.objects.create_user(username="inviter", email="inviter@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="inviter@example.com", verified=False, primary=True)

        # Create sent invite
        InviteFriend.objects.create(sender=user)

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="inviter").exists())

    def test_keep_users_with_received_invites(self):
        """Test that users who received friend invites are NOT deleted"""
        sender = User.objects.create_user(username="sender", email="sender@example.com", password="testpass123")
        recipient = User.objects.create_user(
            username="recipient", email="recipient@example.com", password="testpass123"
        )
        recipient.date_joined = self.cutoff_date - timedelta(days=10)
        recipient.save()

        EmailAddress.objects.create(user=recipient, email="recipient@example.com", verified=False, primary=True)

        # Create invite with recipient
        invite = InviteFriend.objects.create(sender=sender)
        invite.recipients.add(recipient)

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify recipient was NOT deleted
        self.assertTrue(User.objects.filter(username="recipient").exists())

    def test_keep_users_with_sent_org_invites(self):
        """Test that users who sent organization invites are NOT deleted"""
        user = User.objects.create_user(username="orginviter", email="orginviter@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="orginviter@example.com", verified=False, primary=True)

        # Create organization invite
        InviteOrganization.objects.create(sender=user, email="invitee@example.com", organization_name="Test Org")

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="orginviter").exists())

    def test_keep_users_with_search_history(self):
        """Test that users with search history are NOT deleted"""
        user = User.objects.create_user(username="searcher", email="searcher@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="searcher@example.com", verified=False, primary=True)

        # Create search history
        SearchHistory.objects.create(user=user, query="test search", search_type="all")

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="searcher").exists())

    def test_keep_users_with_contributions(self):
        """Test that users with contributions are NOT deleted"""
        user = User.objects.create_user(username="contributor", email="contributor@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="contributor@example.com", verified=False, primary=True)

        # Create contribution
        Contribution.objects.create(
            user=user,
            title="Test Contribution",
            description="Test description",
            contribution_type="commit",
            created=timezone.now(),
            status="open",
        )

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="contributor").exists())

    def test_keep_users_with_bacon_tokens(self):
        """Test that users with bacon tokens are NOT deleted"""
        user = User.objects.create_user(username="baconholder", email="baconholder@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="baconholder@example.com", verified=False, primary=True)

        # Create contribution and bacon token
        contribution = Contribution.objects.create(
            user=user,
            title="Test Contribution",
            description="Test description",
            contribution_type="commit",
            created=timezone.now(),
            status="open",
        )
        BaconToken.objects.create(user=user, amount=100, contribution=contribution)

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="baconholder").exists())

    def test_keep_users_with_time_logs(self):
        """Test that users with time logs are NOT deleted"""
        user = User.objects.create_user(username="timelogger", email="timelogger@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="timelogger@example.com", verified=False, primary=True)

        # Create time log
        TimeLog.objects.create(user=user, start_time=timezone.now(), end_time=timezone.now() + timedelta(hours=1))

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="timelogger").exists())

    def test_keep_users_with_activity_logs(self):
        """Test that users with activity logs are NOT deleted"""
        user = User.objects.create_user(
            username="activitylogger", email="activitylogger@example.com", password="testpass123"
        )
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="activitylogger@example.com", verified=False, primary=True)

        # Create activity log
        ActivityLog.objects.create(user=user, window_title="Test Window")

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="activitylogger").exists())

    def test_keep_users_with_status_reports(self):
        """Test that users with daily status reports are NOT deleted"""
        user = User.objects.create_user(username="reporter", email="reporter@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="reporter@example.com", verified=False, primary=True)

        # Create status report
        DailyStatusReport.objects.create(
            user=user,
            date=timezone.now().date(),
            previous_work="Did work",
            next_plan="Will do work",
            blockers="No blockers",
        )

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="reporter").exists())

    def test_keep_users_with_activities(self):
        """Test that users with activity records are NOT deleted"""
        user = User.objects.create_user(
            username="activityuser", email="activityuser@example.com", password="testpass123"
        )
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="activityuser@example.com", verified=False, primary=True)

        # Create activity record
        Activity.objects.create(user=user)

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="activityuser").exists())

    def test_keep_users_with_wins(self):
        """Test that users with winner records are NOT deleted"""
        user = User.objects.create_user(username="winner", email="winner@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="winner@example.com", verified=False, primary=True)

        # Create domain and hunt for winner
        domain = Domain.objects.create(url="https://test.com", name="Test Domain")
        hunt = Hunt.objects.create(domain=domain, prize=100)
        Winner.objects.create(user=user, hunt=hunt, prize_money=50)

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="winner").exists())

    def test_keep_users_with_wallet(self):
        """Test that users with wallets are NOT deleted"""
        user = User.objects.create_user(
            username="walletholder", email="walletholder@example.com", password="testpass123"
        )
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="walletholder@example.com", verified=False, primary=True)

        # Create wallet
        Wallet.objects.create(user=user, current_balance=100.00)

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="walletholder").exists())

    def test_keep_users_with_profile_content(self):
        """Test that users with profile avatars or descriptions are NOT deleted"""
        # Test with avatar
        user1 = User.objects.create_user(username="avataruser", email="avataruser@example.com", password="testpass123")
        user1.date_joined = self.cutoff_date - timedelta(days=10)
        user1.save()

        EmailAddress.objects.create(user=user1, email="avataruser@example.com", verified=False, primary=True)
        UserProfile.objects.create(user=user1, user_avatar="avatars/test.jpg")

        # Test with description
        user2 = User.objects.create_user(username="biouser", email="biouser@example.com", password="testpass123")
        user2.date_joined = self.cutoff_date - timedelta(days=10)
        user2.save()

        EmailAddress.objects.create(user=user2, email="biouser@example.com", verified=False, primary=True)
        UserProfile.objects.create(user=user2, description="Test bio")

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify users were NOT deleted
        self.assertTrue(User.objects.filter(username="avataruser").exists())
        self.assertTrue(User.objects.filter(username="biouser").exists())

    def test_keep_users_with_issues(self):
        """Test that users with reported issues are NOT deleted"""
        user = User.objects.create_user(username="issuer", email="issuer@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="issuer@example.com", verified=False, primary=True)

        # Create issue
        domain = Domain.objects.create(url="https://test.com", name="Test Domain")
        Issue.objects.create(user=user, domain=domain, description="Test issue")

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="issuer").exists())

    def test_keep_users_with_domains(self):
        """Test that users with domain ownership are NOT deleted"""
        user = User.objects.create_user(username="domainowner", email="domainowner@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="domainowner@example.com", verified=False, primary=True)

        # Create domain
        Domain.objects.create(user=user, url="https://mydomain.com", name="My Domain")

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="domainowner").exists())

    def test_keep_users_with_hunts(self):
        """Test that users with hunt participation are NOT deleted"""
        user = User.objects.create_user(username="hunter", email="hunter@example.com", password="testpass123")
        user.date_joined = self.cutoff_date - timedelta(days=10)
        user.save()

        EmailAddress.objects.create(user=user, email="hunter@example.com", verified=False, primary=True)

        # Create hunt (with user relation if exists)
        domain = Domain.objects.create(url="https://test.com", name="Test Domain")
        Hunt.objects.create(domain=domain, prize=100, user=user)

        # Run command
        out, err = self.call_command(days=self.cutoff_days)

        # Verify user was NOT deleted
        self.assertTrue(User.objects.filter(username="hunter").exists())
