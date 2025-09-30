import logging
import time

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import Domain
from website.core.utils import check_security_txt

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check existing domains for security.txt files"

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=100, help="Number of domains to process in each batch")
        parser.add_argument("--timeout", type=int, default=5, help="Timeout for HTTP requests in seconds")

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        timeout = options["timeout"]

        domains = Domain.objects.all()
        total = domains.count()
        self.stdout.write(f"Processing {total} domains...")

        processed = 0
        updated = 0
        errors = 0

        # Process in batches to avoid memory issues
        for i in range(0, total, batch_size):
            batch = domains[i : i + batch_size]
            for domain in batch:
                try:
                    # Use the utility function instead of duplicating logic
                    has_security_txt = check_security_txt(domain.url)

                    # Update domain with security.txt status
                    domain.has_security_txt = has_security_txt
                    domain.security_txt_checked_at = timezone.now()
                    domain.save(update_fields=["has_security_txt", "security_txt_checked_at"])

                    updated += 1
                except requests.RequestException as e:
                    logger.error(f"Request error checking {domain.url}: {str(e)}")
                    errors += 1
                except (ValueError, TypeError) as e:
                    logger.error(f"Value error checking {domain.url}: {str(e)}")
                    errors += 1
                except Exception as e:
                    logger.error(f"Error checking {domain.url}: {str(e)}")
                    errors += 1

                processed += 1
                if processed % 50 == 0:
                    self.stdout.write(f"Processed {processed}/{total} domains...")

                # Add a small delay to avoid overwhelming servers
                time.sleep(0.1)

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished processing {processed} domains. " f"Updated {updated} domains with {errors} errors."
            )
        )
