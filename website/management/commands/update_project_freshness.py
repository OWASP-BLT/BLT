
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

        from django.db.models import Prefetch
        from website.models import Contribution, Repo
        qs = Project.objects.all().order_by("id")
        if limit and limit > 0:
            qs = qs[:limit]
        qs = qs.prefetch_related(
            Prefetch("repos", queryset=Repo.objects.all()),
            Prefetch("contribution_set", queryset=Contribution.objects.all()),
        )
        total = qs.count()

        self.stdout.write(f"[{timezone.now()}] Starting freshness update for {total} projects (batch={batch})")
        processed = 0
        errors = 0
        error_details = []

        start_index = 0
        while start_index < total:
            chunk = list(qs[start_index : start_index + batch])
            with transaction.atomic():
                for p in chunk:
                    try:
                        new_score = p.calculate_freshness()
                        p.freshness = new_score
                        p.save(update_fields=["freshness"])
                        processed += 1
                    except Exception as e:
                        error_msg = f"Error processing project id={getattr(p, 'id', 'unknown')}: {e}"
                        self.stderr.write(error_msg)
                        error_details.append(error_msg)
                        errors += 1
            start_index += batch
            self.stdout.write(f"Processed {min(start_index, total)}/{total}")

        self.stdout.write(self.style.SUCCESS(f"Finished. processed={processed} errors={errors}"))
        # Analytics summary: distribution of freshness scores
        from collections import Counter
        scores = [p.freshness for p in Project.objects.all()]
        bins = [0, 10, 30, 50, 70, 90, 100]
        dist = Counter()
        for s in scores:
            for b in bins:
                if s <= b:
                    dist[b] += 1
                    break
        self.stdout.write("Freshness score distribution:")
        for b in bins:
            self.stdout.write(f"<= {b}: {dist[b]}")
        if errors:
            self.stdout.write("Error details:")
            for msg in error_details:
                self.stdout.write(msg)
