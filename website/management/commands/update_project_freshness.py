import time
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from website.models import Project

BATCH_SIZE = 500


class Command(BaseCommand):
    help = "Recalculate and update freshness score for all projects"

    def handle(self, *args, **options):
        start_time = time.time()

        qs = Project.objects.only("id")
        total = qs.count()

        processed = 0
        errors = 0

        self.stdout.write(f"Starting freshness update for {total} projects")

        for offset in range(0, total, BATCH_SIZE):
            batch_ids = list(qs.values_list("id", flat=True)[offset : offset + BATCH_SIZE])

            for project_id in batch_ids:
                try:
                    with transaction.atomic():
                        project = Project.objects.select_for_update().get(pk=project_id)

                        project.freshness = project.calculate_freshness()
                        # Update freshness history (ensure list exists)
                        history = project.freshness_history or []
                        history.append({"date": date.today().isoformat(), "score": float(project.freshness)})

                        # Keep only last 12 entries
                        project.freshness_history = history[-12:]

                        project.save(update_fields=["freshness", "freshness_history"])
                        processed += 1

                except Exception as e:
                    errors += 1
                    self.stderr.write(f"[ERROR] Project ID {project_id}: {str(e)}")

            self.stdout.write(
                f"Progress: {min(offset + BATCH_SIZE, total)}/{total} attempted "
                f"({processed} successful, {errors} errors)"
            )

        duration = round(time.time() - start_time, 2)

        self.stdout.write(self.style.SUCCESS("Freshness update completed"))
        self.stdout.write(f"Processed: {processed}")
        self.stdout.write(f"Errors: {errors}")
        self.stdout.write(f"Execution time: {duration}s")
