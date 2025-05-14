import logging
import time

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import Domain

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
        found = 0
        errors = 0

        # Process in batches to avoid memory issues
        for i in range(0, total, batch_size):
            batch = domains[i : i + batch_size]
            for domain in batch:
                try:
                    # Ensure URL has a scheme
                    domain_url = domain.url
                    if not domain_url.startswith(("http://", "https://")):
                        domain_url = f"https://{domain_url}"

                    # Remove trailing slash if present
                    if domain_url.endswith("/"):
                        domain_url = domain_url[:-1]

                    has_security_txt = False

                    # Check at well-known location first (/.well-known/security.txt)
                    security_txt_url = f"{domain_url}/.well-known/security.txt"
                    try:
                        response = requests.head(security_txt_url, timeout=timeout)
                        if response.status_code == 200:
                            has_security_txt = True
                    except requests.RequestException:
                        pass

                    # If not found, check at root location (/security.txt)
                    if not has_security_txt:
                        security_txt_url = f"{domain_url}/security.txt"
                        try:
                            response = requests.head(security_txt_url, timeout=timeout)
                            if response.status_code == 200:
                                has_security_txt = True
                        except requests.RequestException:
                            pass

                    # Update the domain with the results
                    domain.has_security_txt = has_security_txt
                    domain.security_txt_checked_at = timezone.now()
                    domain.save(update_fields=["has_security_txt", "security_txt_checked_at"])

                    if has_security_txt:
                        found += 1
                        self.stdout.write(f"Found security.txt for {domain.name} ({domain.url})")

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
                f"Finished processing {processed} domains. "
                f"Found security.txt on {found} domains with {errors} errors."
            )
        )
