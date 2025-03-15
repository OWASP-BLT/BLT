# yourapp/management/commands/cleanup_gcs_screenshots.py

import logging

from django.conf import settings
from google.cloud import storage

from website.management.base import LoggedBaseCommand
from website.models import Issue, IssueScreenshot

logger = logging.getLogger(__name__)


class Command(LoggedBaseCommand):
    help = "Clean up orphaned screenshots in Google Cloud Storage"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete orphaned files from the bucket",
        )

    def handle(self, *args, **options):
        client = storage.Client()
        bucket = client.bucket(settings.GS_BUCKET_NAME)
        blobs = bucket.list_blobs(prefix="screenshots/")

        issue_screenshots = set(Issue.objects.values_list("screenshot", flat=True))
        issue_screenshot_files = set(IssueScreenshot.objects.values_list("image", flat=True))

        all_known_files = issue_screenshots.union(issue_screenshot_files)

        orphaned_files = []

        for blob in blobs:
            if blob.name not in all_known_files:
                orphaned_files.append(blob.name)
                self.stdout.write(f"Orphaned file found: {blob.name}")
                if options["delete"]:
                    try:
                        blob.delete()
                        self.stdout.write(f"Deleted orphaned file: {blob.name}")
                    except Exception as e:
                        logger.error(f"Error deleting file {blob.name}: {str(e)}")

        if not orphaned_files:
            self.stdout.write("No orphaned files found.")
        else:
            self.stdout.write(f"Total orphaned files: {len(orphaned_files)}")
