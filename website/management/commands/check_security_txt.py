import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from website.models import Domain
from website.core.utils import check_security_txt

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Checks all active domains for security.txt files"

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain_id",
            type=int,
            help="Check specific domain by ID",
        )
        parser.add_argument(
            "--update_all",
            action="store_true",
            help="Check all domains, even if recently checked",
        )
        parser.add_argument(
            "--max_workers",
            type=int,
            default=10,
            help="Maximum number of concurrent workers for the check",
        )

    def check_domain(self, domain):
        """Check a single domain for security.txt"""
        self.stdout.write(f"Checking domain: {domain.name} ({domain.url})")

        try:
            has_security_txt = check_security_txt(domain.url)

            # Update domain with security.txt status
            domain.has_security_txt = has_security_txt
            domain.security_txt_checked_at = timezone.now()
            domain.save(update_fields=["has_security_txt", "security_txt_checked_at"])

            result = "FOUND" if has_security_txt else "NOT FOUND"
            self.stdout.write(f"  -> {result}")
            return domain.id, result
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"  -> REQUEST ERROR: {e}"))
            return domain.id, "ERROR"
        except (ValueError, TypeError) as e:
            self.stdout.write(self.style.ERROR(f"  -> VALUE ERROR: {e}"))
            return domain.id, "ERROR"
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  -> ERROR: {e}"))
            return domain.id, "ERROR"

    def handle(self, *args, **options):
        domain_id = options.get("domain_id")
        update_all = options.get("update_all")
        max_workers = options.get("max_workers")

        # Get domains to check
        if domain_id:
            domains = Domain.objects.filter(id=domain_id)
            if not domains.exists():
                self.stdout.write(self.style.ERROR(f"Domain with ID {domain_id} not found"))
                return
        else:
            domains = Domain.objects.filter(is_active=True)

            # Skip recently checked domains unless update_all is True
            if not update_all:
                # Only check domains that haven't been checked in the last 7 days
                last_week = timezone.now() - timezone.timedelta(days=7)
                domains = domains.filter(
                    Q(security_txt_checked_at__isnull=True) | Q(security_txt_checked_at__lt=last_week)
                )

        total_domains = domains.count()
        self.stdout.write(f"Checking {total_domains} domains for security.txt files...")

        # Initialize counters
        found_count = 0
        not_found_count = 0
        error_count = 0

        # Use ThreadPoolExecutor to check domains concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.check_domain, domain): domain for domain in domains}

            for future in as_completed(futures):
                _, result = future.result()
                if result == "FOUND":
                    found_count += 1
                elif result == "NOT FOUND":
                    not_found_count += 1
                else:
                    error_count += 1

        # Display summary
        self.stdout.write(self.style.SUCCESS(f"Check completed for {total_domains} domains:"))
        self.stdout.write(f"  -> Found security.txt: {found_count}")
        self.stdout.write(f"  -> No security.txt: {not_found_count}")
        self.stdout.write(f"  -> Errors: {error_count}")
