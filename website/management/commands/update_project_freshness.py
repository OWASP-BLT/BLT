import time

from django.core.management.base import BaseCommand

from website.models import Project


class Command(BaseCommand):
    help = "Recalculate and update freshness score for all projects"

    def handle(self, *args, **options):
        start_time = time.time()

        projects = Project.objects.all()
        total = projects.count()

        processed = 0
        errors = 0

        self.stdout.write(f"Starting freshness update for {total} projects")

        for idx, project in enumerate(projects, start=1):
            try:
                freshness = project.calculate_freshness()
                project.freshness = freshness
                project.save(update_fields=["freshness"])
                processed += 1
            except Exception as e:
                errors += 1
                self.stderr.write(f"[ERROR] Project ID {project.id}: {str(e)}")

            if idx % 100 == 0:
                self.stdout.write(f"Processed {idx}/{total} projects...")

        duration = round(time.time() - start_time, 2)

        self.stdout.write(self.style.SUCCESS("Freshness update completed"))
        self.stdout.write(f"Processed: {processed}")
        self.stdout.write(f"Errors: {errors}")
        self.stdout.write(f"Execution time: {duration}s")
