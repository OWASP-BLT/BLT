from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import InviteOrganization
from website.views.core import SAMPLE_INVITE_EMAIL_PATTERN


class Command(BaseCommand):
    help = "Clean up old sample invite records that are used only for displaying referral links"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Delete sample invites older than this many days (default: 7)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        cutoff_date = timezone.now() - timedelta(days=days)

        # Find sample invites to delete
        sample_invites = InviteOrganization.objects.filter(
            email__regex=SAMPLE_INVITE_EMAIL_PATTERN,
            organization_name="",
            created__lt=cutoff_date,
        )

        count = sample_invites.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would delete {count} sample invite records older than {days} days"
                )
            )
            if count > 0:
                self.stdout.write("Sample records that would be deleted:")
                for invite in sample_invites[:10]:  # Show first 10
                    self.stdout.write(f"  - {invite.email} (created: {invite.created})")
                if count > 10:
                    self.stdout.write(f"  ... and {count - 10} more")
        else:
            deleted_count, _ = sample_invites.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted {deleted_count} sample invite records older than {days} days"
                )
            )
