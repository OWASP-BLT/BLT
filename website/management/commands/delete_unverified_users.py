import logging
from datetime import timedelta

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from comments.models import Comment
from website.management.base import LoggedBaseCommand
from website.models import (
    Activity,
    ActivityLog,
    BaconToken,
    Bid,
    Contribution,
    DailyStatusReport,
    Domain,
    InviteFriend,
    InviteOrganization,
    Issue,
    JoinRequest,
    Organization,
    OrganizationAdmin,
    Points,
    SearchHistory,
    TimeLog,
    UserProfile,
    Wallet,
    Winner,
)

logger = logging.getLogger(__name__)


class Command(LoggedBaseCommand):
    help = "Delete users who have not verified their email addresses within a specified timeframe"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Delete users who have been unverified for this many days (default: 30, minimum: 7)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of users to process in each batch (default: 100)",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        # Enforce minimum days for safety
        if days < 7:
            self.stdout.write(
                self.style.ERROR("Minimum days must be 7 or greater for safety. Provided: {}".format(days))
            )
            return

        # Enforce minimum batch size for safety
        if batch_size < 1:
            self.stdout.write(self.style.ERROR("Batch size must be 1 or greater. Provided: {}".format(batch_size)))
            return

        cutoff_date = timezone.now() - timedelta(days=days)

        # Find users to delete
        unverified_users = self.get_unverified_users(cutoff_date)
        total_count = unverified_users.count()

        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS("No unverified users found registered more than {} days ago".format(days))
            )
            return

        if dry_run:
            self.display_dry_run_preview(unverified_users, days, batch_size)
        else:
            self.delete_users_in_batches(unverified_users, days, batch_size)

    def get_unverified_users(self, cutoff_date):
        """
        Get users who:
        1. Registered before the cutoff date
        2. Have no verified email addresses OR no email addresses at all
        3. Are not staff or superusers
        4. Have no significant activity (issues, points, comments, etc.)

        Uses database-level filtering with Exists() subqueries for optimal performance.
        """
        User = get_user_model()

        # Get users with verified emails
        verified_user_ids = EmailAddress.objects.filter(verified=True).values_list("user_id", flat=True).distinct()

        # Create Exists subqueries for all activity checks
        # This is done at the database level to avoid N+1 query problems

        # Check for recent login (logged in after cutoff)
        has_recent_login = Q(last_login__gte=cutoff_date)

        # Check for reported issues
        has_issues = Exists(Issue.objects.filter(user=OuterRef("pk")))

        # Check for points earned
        has_points = Exists(Points.objects.filter(user=OuterRef("pk")))

        # Check for domain management (users can be domain managers)
        has_domains = Exists(Domain.objects.filter(managers=OuterRef("pk")))

        # Check for comments - need to check if user's UserProfile has comments
        # We need to use a subquery since Comment links to UserProfile, not User directly
        has_comments = Exists(Comment.objects.filter(author_fk__user=OuterRef("pk")))

        # Check for bids
        has_bids = Exists(Bid.objects.filter(user=OuterRef("pk")))

        # Check for organization admin role
        has_org_admin = Exists(Organization.objects.filter(admin=OuterRef("pk")))

        # Check for organization manager role
        has_org_manager = Exists(Organization.objects.filter(managers=OuterRef("pk")))

        # Check for organization admin/moderator role
        has_org_admin_role = Exists(OrganizationAdmin.objects.filter(user=OuterRef("pk")))

        # Check for join requests
        has_join_requests = Exists(JoinRequest.objects.filter(user=OuterRef("pk")))

        # Check for sent invites to friends
        has_sent_invites = Exists(InviteFriend.objects.filter(sender=OuterRef("pk")))

        # Check for received invites to friends
        has_received_invites = Exists(InviteFriend.objects.filter(recipients=OuterRef("pk")))

        # Check for sent organization invites
        has_sent_org_invites = Exists(InviteOrganization.objects.filter(sender=OuterRef("pk")))

        # Check for search history
        has_search_history = Exists(SearchHistory.objects.filter(user=OuterRef("pk")))

        # Check for contributions
        has_contributions = Exists(Contribution.objects.filter(user=OuterRef("pk")))

        # Check for bacon tokens
        has_bacon_tokens = Exists(BaconToken.objects.filter(user=OuterRef("pk")))

        # Check for time logs
        has_time_logs = Exists(TimeLog.objects.filter(user=OuterRef("pk")))

        # Check for activity logs
        has_activity_logs = Exists(ActivityLog.objects.filter(user=OuterRef("pk")))

        # Check for daily status reports
        has_status_reports = Exists(DailyStatusReport.objects.filter(user=OuterRef("pk")))

        # Check for activity records
        # NOTE: A "signup" Activity is auto-created for every user, so we exclude it
        has_activities = Exists(Activity.objects.filter(user=OuterRef("pk")).exclude(action_type="signup"))

        # Check for winners (winner, runner, or second_runner)
        # Note: Cannot use Q() with OR inside Exists(), use three separate checks
        has_wins_winner = Exists(Winner.objects.filter(winner=OuterRef("pk")))
        has_wins_runner = Exists(Winner.objects.filter(runner=OuterRef("pk")))
        has_wins_second = Exists(Winner.objects.filter(second_runner=OuterRef("pk")))

        # Note: Wallets are auto-created with $0 balance for all users and are not considered activity
        # Note: UserProfiles are auto-created for all users via AutoOneToOneField

        # Check for wallets with non-zero balance
        # NOTE: Wallets are auto-created with $0 balance for all users, so only non-zero balances count
        has_wallet = Exists(Wallet.objects.filter(user=OuterRef("pk"), current_balance__gt=0))

        # NOTE: UserProfile is auto-created for all users via AutoOneToOneField
        # Check if profile has meaningful content (avatar or description set and non-empty)
        # Split into two separate Exists() because ImageField empty string causes SQL issues when
        # combined in a single query. Two chained .exclude() calls give correct OR semantics:
        # both avatar and description must be absent for the user to be eligible for deletion.
        has_avatar = Exists(
            UserProfile.objects.filter(user=OuterRef("pk"), user_avatar__isnull=False).exclude(user_avatar="")
        )
        has_description = Exists(
            UserProfile.objects.filter(user=OuterRef("pk"), description__isnull=False).exclude(description="")
        )

        # Build the query combining all conditions
        # Chain multiple .exclude() calls instead of using OR operator
        # This ensures proper evaluation of Exists() subqueries
        unverified_users = (
            User.objects.filter(date_joined__lt=cutoff_date, is_staff=False, is_superuser=False)
            .exclude(id__in=verified_user_ids)
            .exclude(has_recent_login)
            .exclude(has_issues)
            .exclude(has_points)
            .exclude(has_domains)
            .exclude(has_comments)
            .exclude(has_bids)
            .exclude(has_org_admin)
            .exclude(has_org_manager)
            .exclude(has_org_admin_role)
            .exclude(has_join_requests)
            .exclude(has_sent_invites)
            .exclude(has_received_invites)
            .exclude(has_sent_org_invites)
            .exclude(has_search_history)
            .exclude(has_contributions)
            .exclude(has_bacon_tokens)
            .exclude(has_time_logs)
            .exclude(has_activity_logs)
            .exclude(has_status_reports)
            .exclude(has_activities)
            .exclude(has_wins_winner)
            .exclude(has_wins_runner)
            .exclude(has_wins_second)
            .exclude(has_wallet)
            .exclude(has_avatar)
            .exclude(has_description)
        )

        return unverified_users

    def delete_users_in_batches(self, users, days, batch_size):
        """Delete users in batches with transaction safety and race condition protection"""
        total_count = users.count()
        deleted_count = 0
        email_addresses_deleted = 0
        skipped_count = 0
        batch_num = 0
        cutoff_date = timezone.now() - timedelta(days=days)

        self.stdout.write(
            self.style.WARNING(
                "Starting deletion of {} unverified users registered more than {} days ago...".format(total_count, days)
            )
        )

        # Process in batches
        user_ids = list(users.values_list("id", flat=True))

        User = get_user_model()
        for i in range(0, len(user_ids), batch_size):
            batch_num += 1
            batch_ids = user_ids[i : i + batch_size]

            # Re-fetch users using the same filtering logic to ensure they still qualify for deletion
            # This protects against race conditions where activity might have been added
            batch_users = self.get_unverified_users(cutoff_date).filter(id__in=batch_ids)

            actual_batch_size = batch_users.count()
            if actual_batch_size < len(batch_ids):
                # Some users no longer qualify for deletion
                skipped_this_batch = len(batch_ids) - actual_batch_size
                skipped_count += skipped_this_batch
                logger.info(
                    "Batch {}: Skipped {} users who gained activity since initial query".format(
                        batch_num, skipped_this_batch
                    )
                )

            if actual_batch_size == 0:
                # All users in this batch now have activity, skip
                continue

            try:
                with transaction.atomic():
                    # Count related EmailAddress records before deletion
                    email_count = EmailAddress.objects.filter(user__in=batch_users).count()

                    # Delete the batch
                    batch_deleted, objects_deleted = batch_users.delete()

                    # Extract actual User count from objects_deleted dict
                    user_model = get_user_model()
                    user_key = "{}.{}".format(user_model._meta.app_label, user_model.__name__)
                    users_deleted = objects_deleted.get(user_key, 0)

                    # Increment counters only after successful deletion
                    deleted_count += users_deleted
                    email_addresses_deleted += email_count
                    self.stdout.write(
                        "  Batch {}/{}: Deleted {} users".format(
                            batch_num, (len(user_ids) + batch_size - 1) // batch_size, users_deleted
                        )
                    )

                    logger.info(
                        "Deleted batch {} ({} users). Objects deleted: {}".format(
                            batch_num, users_deleted, objects_deleted
                        )
                    )

            except Exception as e:
                logger.error("Error deleting batch {}: {}".format(batch_num, str(e)), exc_info=True)
                self.stdout.write(self.style.ERROR("  Error deleting batch {}: {}".format(batch_num, str(e))))
                continue

        # Final summary
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(
            self.style.SUCCESS(
                "Successfully deleted {} unverified users registered more than {} days ago".format(deleted_count, days)
            )
        )
        self.stdout.write("  - Total EmailAddress records deleted: {}".format(email_addresses_deleted))
        if skipped_count > 0:
            self.stdout.write(
                self.style.WARNING("  - Skipped {} users who gained activity during deletion".format(skipped_count))
            )
        self.stdout.write("=" * 70)

        logger.info(
            "Completed deletion: {} users deleted, {} EmailAddress records removed, {} users skipped".format(
                deleted_count, email_addresses_deleted, skipped_count
            )
        )

    def display_dry_run_preview(self, users, days, batch_size):
        """Display preview of what would be deleted in dry-run mode"""
        total_count = users.count()

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(
            self.style.WARNING(
                "DRY RUN: Would delete {} unverified users registered more than {} days ago".format(total_count, days)
            )
        )
        self.stdout.write("=" * 70 + "\n")

        # Show sample users
        sample_size = min(10, total_count)
        sample_users = users[:sample_size]

        self.stdout.write("Sample users that would be deleted:")
        for user in sample_users:
            # Get email addresses for this user
            emails = EmailAddress.objects.filter(user=user)
            email_status = "No email addresses"
            if emails.exists():
                email_list = ["{} (verified: {})".format(e.email, e.verified) for e in emails]
                email_status = ", ".join(email_list)

            self.stdout.write(
                "  - {} ({}) | Registered: {} | Emails: {}".format(
                    user.username,
                    user.email or "no email",
                    user.date_joined.strftime("%Y-%m-%d %H:%M:%S"),
                    email_status,
                )
            )

        if total_count > sample_size:
            self.stdout.write("  ... and {} more".format(total_count - sample_size))

        # Count related objects
        email_address_count = EmailAddress.objects.filter(user__in=users).count()

        self.stdout.write("\n" + "-" * 70)
        self.stdout.write("Related objects that would be deleted:")
        self.stdout.write("  - EmailAddress records: {}".format(email_address_count))
        self.stdout.write("-" * 70)

        # Show statistics
        self.stdout.write("\nDeletion statistics:")
        self.stdout.write("  - Total users: {}".format(total_count))
        self.stdout.write("  - Batch size: {}".format(batch_size))
        self.stdout.write("  - Number of batches: {}".format((total_count + batch_size - 1) // batch_size))
        self.stdout.write("  - Age threshold: {} days".format(days))

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("To execute deletion, run this command without --dry-run"))
        self.stdout.write("=" * 70 + "\n")
