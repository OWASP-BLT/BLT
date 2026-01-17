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
        if limit and limit > 0:
            qs = qs.iterator()
            qs = (p for i, p in enumerate(qs) if i < limit)
        else:
            qs = qs.iterator()
        qs = list(qs)  # Prefetching not needed for freshness
        total = len(qs)

        self.stdout.write(f"[{timezone.now()}] Starting freshness update for {total} projects (batch={batch})")
        processed = 0
        errors = 0
        error_details = []

        from itertools import islice

        def batched(iterable, n):
            it = iter(iterable)
            while True:
                batch = list(islice(it, n))
                if not batch:
                    break
                yield batch

        for chunk in batched(qs, batch):
            for p in chunk:
                try:
                    with transaction.atomic():
                        new_score = p.calculate_freshness()
                        p.freshness = new_score
                        p.save(update_fields=["freshness"])
                    processed += 1
                except Exception as e:
                    error_msg = f"Error processing project id={getattr(p, 'id', 'unknown')}: {e}"
                    self.stderr.write(error_msg)
                    error_details.append(error_msg)
                    errors += 1
            self.stdout.write(f"Processed {min(processed, total)}/{total}")

        self.stdout.write(self.style.SUCCESS(f"Finished. processed={processed} errors={errors}"))
        # Analytics summary: distribution of freshness scores
        from collections import Counter

        scores = Project.objects.values_list("freshness", flat=True).iterator()
        bins = [0, 10, 30, 50, 70, 90, 100]
        dist = Counter()
        for s in scores:
            for b in bins:
                if s is not None and s <= b:
                    dist[b] += 1
                    break
        self.stdout.write("Freshness score distribution:")
        for b in bins:
            self.stdout.write(f"<= {b}: {dist[b]}")
        if errors:
            self.stdout.write("Error details:")
            for msg in error_details:
                self.stdout.write(msg)
