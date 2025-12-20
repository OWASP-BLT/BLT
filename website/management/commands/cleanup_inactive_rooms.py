from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count, Max
from django.utils import timezone

from website.models import Room


class Command(BaseCommand):
    help = "Clean up inactive discussion rooms"

    def add_arguments(self, parser):
        parser.add_argument(
            "--empty-days",
            type=int,
            default=7,
            help="Delete rooms with no messages older than this many days (default: 7)",
        )
        parser.add_argument(
            "--inactive-days",
            type=int,
            default=60,
            help="Delete rooms with messages but inactive for this many days (default: 60)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *_, **options):
        empty_days = options["empty_days"]
        inactive_days = options["inactive_days"]
        dry_run = options["dry_run"]

        now = timezone.now()
        empty_cutoff = now - timedelta(days=empty_days)
        inactive_cutoff = now - timedelta(days=inactive_days)

        empty_rooms = Room.objects.annotate(message_count=Count("messages")).filter(
            message_count=0, created_at__lt=empty_cutoff
        )

        inactive_rooms = Room.objects.annotate(
            message_count=Count("messages"),
            last_message=Max("messages__timestamp"),
        ).filter(message_count__gt=0, last_message__lt=inactive_cutoff)

        total_to_delete = empty_rooms.count() + inactive_rooms.count()

        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would delete {total_to_delete} inactive discussion rooms"))

            if empty_rooms.exists():
                self.stdout.write(f"\nRooms with no messages older than {empty_days} days:")
                for room in empty_rooms[:10]:
                    self.stdout.write(f"  - {room.name} (created: {room.created_at})")

            if inactive_rooms.exists():
                self.stdout.write(f"\nRooms inactive for more than {inactive_days} days:")
                for room in inactive_rooms[:10]:
                    self.stdout.write(f"  - {room.name} (last message: {room.last_message})")

            if total_to_delete > 20:
                self.stdout.write("  ... and more")

        else:
            empty_count = empty_rooms.count()
            inactive_count = inactive_rooms.count()
            empty_rooms.delete()
            inactive_rooms.delete()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {deleted_empty + deleted_inactive} inactive discussion rooms "
                    f"({deleted_empty} empty, {deleted_inactive} inactive)"
                )
            )
