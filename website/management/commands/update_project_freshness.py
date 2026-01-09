from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from website.models import Project

class Command(BaseCommand):
    help = "Recalculate and persist freshness for all projects."

    def add_arguments(self, parser):
        parser.add_argument("--batch", type=int, default=100, help="Batch size per transaction")
        parser.add_argument("--limit", type=int, default=0, help="Limit number of projects processed (for testing)")

    def handle(self, *args, **options):
        batch = options["batch"]
        limit = options["limit"]

        qs = Project.objects.all().order_by("id")
        total = qs.count()
        if limit and limit > 0:
            qs = qs[:limit]
            total = qs.count()

        self.stdout.write(f"[{timezone.now()}] Starting freshness update for {total} projects (batch={batch})")
        processed = 0
        errors = 0

        start_index = 0
        while start_index < total:
            chunk = list(qs[start_index : start_index + batch])
            with transaction.atomic():
                for p in chunk:
                    try:
                        # If you integrate BLT-Bumper, fetch activity_graph_score here and pass to calculate_freshness
                        new_score = p.calculate_freshness()
                        p.freshness = new_score
                        p.save(update_fields=["freshness"])
                        processed += 1
                    except Exception as e:
                        self.stderr.write(f"Error processing project id={getattr(p, 'id', 'unknown')}: {e}")
                        errors += 1
            start_index += batch
            self.stdout.write(f"Processed {min(start_index, total)}/{total}")

        self.stdout.write(self.style.SUCCESS(f"Finished. processed={processed} errors={errors}"))
