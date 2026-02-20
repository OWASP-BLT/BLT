import logging
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import UserLoginEvent

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Purge UserLoginEvent records older than the retention window (default 90 days)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="Retention window in days (default: LOGIN_EVENT_RETENTION_DAYS setting or 90)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *_, **options):
        default_days = getattr(settings, "LOGIN_EVENT_RETENTION_DAYS", 90)
        days = options["days"] or default_days
        dry_run = options["dry_run"]

        cutoff = timezone.now() - timedelta(days=days)
        queryset = UserLoginEvent.objects.filter(timestamp__lt=cutoff)
        count = queryset.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No login events older than %d days." % days))
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN: Would delete %d login events older than %d days." % (count, days))
            )
        else:
            deleted, _ = queryset.delete()
            self.stdout.write(self.style.SUCCESS("Deleted %d login events older than %d days." % (deleted, days)))
            logger.info("purge_old_login_events: deleted %d records older than %d days", deleted, days)
