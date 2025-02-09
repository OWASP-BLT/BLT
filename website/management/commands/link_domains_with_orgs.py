from django.core.management.base import BaseCommand
from django.db import transaction

from website.models import Domain, Organization


class Command(BaseCommand):
    help = "Link Existing Domain instances to Organizations"

    def handle(self, *args, **options):
        with transaction.atomic():
            domains = Domain.objects.select_for_update().filter(organization__isnull=True)

            if not domains.exists():
                self.stdout.write(self.style.SUCCESS("No unlinked domains found to process"))
                return

            self.stdout.write(f"Found {domains.count()} domains to process")

            for domain in domains:
                try:
                    # Get domain name, clean it up
                    domain_name = domain.name.strip() if domain.name else None
                    if not domain_name:
                        self.stdout.write(self.style.WARNING(f"Skipping domain {domain.id}: Empty name"))
                        continue

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
                            )
                            self.stdout.write(f"Created new organization: {org.name}")
                        except Exception as org_error:
                            self.stdout.write(self.style.ERROR(f"Failed to create org for {domain_name}: {org_error}"))
                            continue

                    # Link domain to organization
                    domain.organization = org
                    domain.save()
                    self.stdout.write(f"Linked domain '{domain_name}' to organization '{org.name}'")

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing domain {domain.id}: {str(e)}"))
                    continue

            self.stdout.write("Domain linking process completed")
