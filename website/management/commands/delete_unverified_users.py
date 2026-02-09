import logging
from datetime import timedelta

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from website.management.base import LoggedBaseCommand

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

        cutoff_date = timezone.now() - timedelta(days=days)
        # Store cutoff for use in has_user_activity
        self.cutoff_datetime = cutoff_date

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
        4. Have no significant activity (issues, points, etc.)
        """
        User = get_user_model()
        # Get all users registered before cutoff who are not staff/superuser
        candidate_users = User.objects.filter(date_joined__lt=cutoff_date, is_staff=False, is_superuser=False)

        # Get users with verified emails
        verified_user_ids = EmailAddress.objects.filter(verified=True).values_list("user_id", flat=True).distinct()

        # Exclude users with verified emails
        unverified_users = candidate_users.exclude(id__in=verified_user_ids)

        # Exclude users with activity
        users_to_delete = []
        for user in unverified_users:
            if not self.has_user_activity(user):
                users_to_delete.append(user.id)

        return User.objects.filter(id__in=users_to_delete)

    def has_user_activity(self, user):
        """Check if user has any meaningful activity in the system"""
        try:
            # Check for recent login
            if user.last_login is not None and user.last_login >= self.cutoff_datetime:
                return True

            # Check for reported issues
            if hasattr(user, "issue_set") and user.issue_set.exists():
                return True

            # Check for points earned
            if hasattr(user, "points_set") and user.points_set.exists():
                return True

            # Check for domain ownership
            if hasattr(user, "domain_set") and user.domain_set.exists():
                return True

            # Check for comments
            if hasattr(user, "userprofile"):
                profile = user.userprofile
                # Check for any activity on the profile that indicates engagement
                if profile.user_avatar or profile.description:
                    return True

            # Check for hunt participation
            if hasattr(user, "hunt_set") and user.hunt_set.exists():
                return True

            return False
        except Exception as e:
            logger.warning("Error checking activity for user {}: {}".format(user.username, str(e)))
            # If we can't determine activity safely, don't delete
            return True

    def delete_users_in_batches(self, users, days, batch_size):
        """Delete users in batches with transaction safety"""
        total_count = users.count()
        deleted_count = 0
        email_addresses_deleted = 0
        batch_num = 0

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
            batch_users = User.objects.filter(id__in=batch_ids)

            try:
                with transaction.atomic():
                    # Count related EmailAddress records before deletion
                    email_count = EmailAddress.objects.filter(user__in=batch_users).count()
                    email_addresses_deleted += email_count

                    # Delete the batch
                    batch_deleted, objects_deleted = batch_users.delete()

                    # Extract actual User count from objects_deleted dict
                    user_model = get_user_model()
                    user_key = "{}.{}".format(user_model._meta.app_label, user_model.__name__)
                    users_deleted = objects_deleted.get(user_key, 0)

                    deleted_count += users_deleted
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
        self.stdout.write("=" * 70)

        logger.info(
            "Completed deletion: {} users deleted, {} EmailAddress records removed".format(
                deleted_count, email_addresses_deleted
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
