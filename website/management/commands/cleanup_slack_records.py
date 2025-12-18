import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import SlackHuddle, SlackPoll, SlackReminder

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Cleanup old Slack polls, reminders, and huddles"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=90, help="Age in days after which records are cleaned")
        parser.add_argument(
            "--dry-run", action="store_true", help="Show what would be deleted without performing the cleanup"
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options["days"])
        dry_run = options["dry_run"]

        polls_qs = SlackPoll.objects.filter(status="closed", closed_at__lte=cutoff)
        reminders_qs = SlackReminder.objects.filter(status__in=["sent", "failed", "cancelled"], remind_at__lte=cutoff)
        huddles_qs = SlackHuddle.objects.filter(status__in=["completed", "cancelled"], scheduled_at__lte=cutoff)

        stats = {
            "polls": polls_qs.count(),
            "reminders": reminders_qs.count(),
            "huddles": huddles_qs.count(),
        }

        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    f"[DRY RUN] Would delete: polls={stats['polls']}, reminders={stats['reminders']}, huddles={stats['huddles']}"
                )
            )
            return

        polls_deleted, _ = polls_qs.delete()
        reminders_deleted, _ = reminders_qs.delete()
        huddles_deleted, _ = huddles_qs.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted polls={polls_deleted}, reminders={reminders_deleted}, huddles={huddles_deleted} older than {options['days']} days"
            )
        )
