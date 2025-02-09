import re
from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.db import transaction

from website.models import Domain, Organization


class Command(BaseCommand):
    help = "Link Domains with Organizations and clean up URLs"

    def clean_url(self, url):
        if not url:
            return ""

        # Fix double protocol issues
        url = re.sub(r"https?://https?://", "https://", url)
        url = re.sub(r"https?://", "https://", url)

        try:
            # Parse the URL
            parsed = urlparse(url)

            # Ensure there's a protocol
            if not parsed.scheme:
                parsed = urlparse("https://" + url)

            # Get just the domain
            domain = parsed.netloc

            # Remove www. if present
            domain = re.sub(r"^www\.", "", domain)

            # Return cleaned URL with https protocol
            return f"https://{domain}"
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Error cleaning URL {url}: {str(e)}"))
            return url

    def handle(self, *args, **options):
        with transaction.atomic():
            # Process all organizations
            organizations = Organization.objects.select_for_update().all()

            if not organizations.exists():
                self.stdout.write(self.style.SUCCESS("No organizations found to process"))
                return

            self.stdout.write(f"Found {organizations.count()} organizations to process")

            for org in organizations:
                try:
                    # Clean up the organization's URL
                    original_url = org.url
                    cleaned_url = self.clean_url(original_url)

                    if original_url != cleaned_url:
                        self.stdout.write(f"Cleaning URL for {org.name}: {original_url} -> {cleaned_url}")
                        org.url = cleaned_url

                    # Set organization to active
                    if not org.is_active:
                        self.stdout.write(f"Setting {org.name} to active")
                        org.is_active = True

                    org.save()

                    # Process associated domains
                    domains = Domain.objects.filter(organization=org)
                    for domain in domains:
                        try:
                            # Clean up domain URL
                            original_domain_url = domain.url
                            cleaned_domain_url = self.clean_url(original_domain_url)

                            if original_domain_url != cleaned_domain_url:
                                self.stdout.write(f"Cleaning domain URL: {original_domain_url} -> {cleaned_domain_url}")
                                domain.url = cleaned_domain_url
                                domain.save()

                        except Exception as domain_error:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"Error processing domain {domain.id} for org {org.name}: {str(domain_error)}"
                                )
                            )
                            continue

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing organization {org.name}: {str(e)}"))
                    continue

            # Process any unlinked domains
            unlinked_domains = Domain.objects.select_for_update().filter(organization__isnull=True)
            if unlinked_domains.exists():
                self.stdout.write(f"Processing {unlinked_domains.count()} unlinked domains")

                for domain in unlinked_domains:
                    try:
                        # Clean up domain name and URL
                        domain_name = domain.name.strip() if domain.name else None
                        if not domain_name:
                            self.stdout.write(self.style.WARNING(f"Skipping domain {domain.id}: Empty name"))
                            continue

                        # Clean the domain URL
                        domain.url = self.clean_url(domain.url)

                        # Try to find existing organization by exact domain name
                        org = Organization.objects.filter(name__iexact=domain_name).first()

                        if org:
                            self.stdout.write(f"Found existing organization: {org.name}")
                        else:
                            # Create new organization from domain
                            try:
                                org = Organization.objects.create(
                                    name=domain_name,
                                    url=domain.url or "",
                                    logo=domain.logo if hasattr(domain, "logo") else None,
                                    description=f"Organization for {domain_name}",
                                    is_active=True,  # Set new organizations to active
                                )
                                self.stdout.write(f"Created new organization: {org.name}")
                            except Exception as org_error:
                                self.stdout.write(
                                    self.style.ERROR(f"Failed to create org for {domain_name}: {org_error}")
                                )
                                continue

                        # Link domain to organization
                        domain.organization = org
                        domain.save()
                        self.stdout.write(f"Linked domain '{domain_name}' to organization '{org.name}'")

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error processing domain {domain.id}: {str(e)}"))
                        continue

            self.stdout.write(self.style.SUCCESS("Organization and domain processing completed"))
