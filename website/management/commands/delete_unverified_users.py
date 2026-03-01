from datetime import timedelta

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.utils import timezone

from website.management.base import LoggedBaseCommand


class Command(LoggedBaseCommand):
    help = "List or delete users who have no verified email and are older than a threshold"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Minimum account age in days before a user is considered for deletion (default: 30)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Maximum number of users to process (default: 0 = no limit)",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Actually delete users. Without this flag, command runs in dry-run mode.",
        )
        parser.add_argument(
            "--include-staff",
            action="store_true",
            help="Include staff users in results (excluded by default).",
        )

    def handle(self, *_args, **options):
        days = options["days"]
        limit = options["limit"]
        execute = options["execute"]
        include_staff = options["include_staff"]

        if days < 0:
            self.stderr.write(self.style.ERROR("--days must be >= 0"))
            return

        if limit < 0:
            self.stderr.write(self.style.ERROR("--limit must be >= 0"))
            return

        user_model = get_user_model()
        cutoff = timezone.now() - timedelta(days=days)

        verified_user_ids = EmailAddress.objects.filter(verified=True).values_list("user_id", flat=True)

        queryset = user_model.objects.filter(date_joined__lt=cutoff).exclude(id__in=verified_user_ids).exclude(
            is_superuser=True
        )

        if not include_staff:
            queryset = queryset.exclude(is_staff=True)

        queryset = queryset.order_by("date_joined", "id")
        if limit > 0:
            queryset = queryset[:limit]

        users = list(queryset)

        mode = "EXECUTE" if execute else "DRY-RUN"
        self.stdout.write(f"Mode: {mode}")
        self.stdout.write(
            f"Candidates with no verified email and older than {days} day(s): {len(users)}"
        )

        if not users:
            self.stdout.write("No matching users found.")
            return

        for user in users:
            email = user.email or "(no email)"
            self.stdout.write(
                f"- id={user.id} username={user.username} email={email} joined={user.date_joined.isoformat()}"
            )

        if not execute:
            self.stdout.write("Dry-run only. Re-run with --execute to delete these users.")
            return

        deleted_count = 0
        for user in users:
            user.delete()
            deleted_count += 1

        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} user(s)."))
