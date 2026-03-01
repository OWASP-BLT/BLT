from django.utils import timezone

from website.management.base import LoggedBaseCommand
from website.models import Organization, Trademark


class Command(LoggedBaseCommand):
    help = "Check trademarks for a random organization using the local trademark database"

    def handle(self, *args, **kwargs):
        organization = Organization.objects.order_by("?").first()

        if not organization:
            self.stdout.write(self.style.ERROR("No organizations found in the database"))
            return

        name = organization.name

        self.stdout.write(self.style.NOTICE(f"Checking trademarks for organization: {name}"))

        # Search local trademark database
        trademarks = Trademark.objects.filter(keyword__icontains=name).prefetch_related("owners")

        count = trademarks.count()

        # Attach trademarks to organization (optional, depending on model usage)
        for trademark in trademarks:
            if trademark.organization_id is None:
                trademark.organization = organization
                trademark.save(update_fields=["organization"])

        # Update organization metadata
        organization.trademark_check_date = timezone.now()
        organization.trademark_count = count
        organization.save(update_fields=["trademark_check_date", "trademark_count"])

        self.stdout.write(self.style.SUCCESS(f"Found {count} trademark(s) for organization: {name}"))
