from django.core.management.base import BaseCommand
from django.db import transaction

from website.models import Domain, Organization


class Command(BaseCommand):
    help = "Link Existing Domain instances to Organizations"

    def handle(self, *args, **options):
        with transaction.atomic():
            domains = Domain.objects.select_for_update()

            for domain in domains:
                try:
                    org_name = domain.get_name
                    if not org_name:
                        self.stdout.write(self.style.WARNING(f"Skipping domain {domain.id}: Empty name"))
                        continue

                    # Try to find existing organizations by name or URL
                    matching_orgs = Organization.objects.filter(name__iexact=org_name) | Organization.objects.filter(
                        url=domain.url
                    )

                    if matching_orgs.exists():
                        organization = matching_orgs.first()  # Use the first matching organization
                        created = False
                        matcher = (
                            f"name: {organization.name}"
                            if organization.name == domain.name
                            else f"url: {organization.url}"
                        )
                        self.stdout.write(self.style.SUCCESS(f"Found match based on {matcher}"))
                    else:
                        # Create a new organization if none exists
                        organization = Organization.objects.create(
                            name=org_name,
                            url=domain.url,
                            logo=domain.logo,
                            description=f"Organization for {org_name}",
                        )
                        created = True

                    domain.organization = organization
                    domain.save()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{'Created' if created else 'Linked'} organization '{organization.name}' with domain '{domain.name}'"
                        )
                    )

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing domain {domain.name}: {str(e)}"))
                    continue
