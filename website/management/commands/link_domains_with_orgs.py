import re

from django.db import transaction

from website.management.base import LoggedBaseCommand
from website.models import Domain, Organization


class Command(LoggedBaseCommand):
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
            # Basic domain validation
            if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", domain):
                return f"https://{domain}"
        return ""

    def clean_name(self, name):
        # Extract domain from URL-like names
        domain_match = re.search(r"(?:https?://)?([^/\s]+)", name)
        if domain_match:
            name = domain_match.group(1)
        # Remove www and common TLDs
        name = re.sub(r"^www\.", "", name)
        name = re.sub(r"\.(com|org|net|edu)$", "", name)
        # Convert to title case and limit length
        return name.title()[:50]

    def handle(self, *args, **options):
        # Process all organizations
        orgs = Organization.objects.all()
        self.stdout.write(f"Processing {orgs.count()} organizations")

        for org in orgs:
            try:
                with transaction.atomic():
                    # Clean URL
                    old_url = org.url
                    new_url = self.clean_url(old_url)

                    # Only update if we got a valid URL
                    if new_url:
                        if old_url != new_url:
                            self.stdout.write(self.style.SUCCESS(f"Org: {old_url} -> {new_url}"))
                            org.url = new_url

                        # Clean name if it looks like a URL
                        if "/" in org.name or "." in org.name:
                            old_name = org.name
                            new_name = self.clean_name(old_name)
                            if old_name != new_name:
                                self.stdout.write(self.style.SUCCESS(f"Name: {old_name} -> {new_name}"))
                                org.name = new_name

                        # Set active
                        if not org.is_active:
                            org.is_active = True
                            self.stdout.write(f"Set {org.name} active")

                        org.save()

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error with org: {str(e)}"))

        # Process all domains
        domains = Domain.objects.all()
        self.stdout.write(f"Processing {domains.count()} domains")

        for domain in domains:
            try:
                with transaction.atomic():
                    # Clean URL
                    old_url = domain.url
                    new_url = self.clean_url(old_url)

                    # Only update if we got a valid URL
                    if new_url and old_url != new_url:
                        self.stdout.write(self.style.SUCCESS(f"Domain: {old_url} -> {new_url}"))
                        domain.url = new_url
                        domain.save()

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error with domain: {str(e)}"))

        self.stdout.write(self.style.SUCCESS("URL cleaning completed"))
