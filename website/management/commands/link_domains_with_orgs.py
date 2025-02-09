import re

from django.core.management.base import BaseCommand
from django.db import transaction

from website.models import Domain, Organization


class Command(BaseCommand):
    help = "Clean URLs to just domains and set organizations active"

    def clean_url(self, url):
        if not url:
            return ""

        # Remove any whitespace
        url = url.strip()

        # Fix common issues with protocols
        url = re.sub(r"https?://https?://", "https://", url)

        # Extract domain using regex
        # Match after protocol until first slash or end of string
        domain_match = re.search(r"(?:https?://)?([^/\s]+)", url)
        if domain_match:
            domain = domain_match.group(1)
            # Remove www.
            domain = re.sub(r"^www\.", "", domain)
            return f"https://{domain}"

        return ""

    def handle(self, *args, **options):
        with transaction.atomic():
            # Process all organizations
            orgs = Organization.objects.select_for_update().all()

            self.stdout.write(f"Processing {orgs.count()} organizations")

            for org in orgs:
                try:
                    # Clean URL
                    old_url = org.url
                    new_url = self.clean_url(old_url)
                    if old_url != new_url:
                        self.stdout.write(f"Org {org.name}: {old_url} -> {new_url}")
                        org.url = new_url

                    # Set active
                    if not org.is_active:
                        org.is_active = True
                        self.stdout.write(f"Set {org.name} active")

                    org.save()

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error with org {org.name}: {e}"))

            # Process all domains
            domains = Domain.objects.select_for_update().all()

            self.stdout.write(f"Processing {domains.count()} domains")

            for domain in domains:
                try:
                    # Clean URL
                    old_url = domain.url
                    new_url = self.clean_url(old_url)
                    if old_url != new_url:
                        self.stdout.write(f"Domain {domain.name}: {old_url} -> {new_url}")
                        domain.url = new_url
                        domain.save()

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error with domain {domain.name}: {e}"))

            self.stdout.write(self.style.SUCCESS("URL cleaning completed"))
