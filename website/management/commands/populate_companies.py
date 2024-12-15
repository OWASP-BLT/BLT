from django.core.management.base import BaseCommand

from website.models import Company


class Command(BaseCommand):
    help = "Populate test data with popular companies"

    def handle(self, *args, **options):
        # Test data for popular companies
        test_data = [
            {
                "name": "Google",
                "email": "hyoyenkyuma@gmail.com",
                "trademark": 0,
                "url": "https://www.google.com",
            },
            {
                "name": "Microsoft",
                "email": "hyoyenkyuma@gmail.com",
                "trademark": 0,
                "url": "https://www.microsoft.com",
            },
        ]

        for company_data in test_data:
            company, created = Company.objects.update_or_create(
                name=company_data["name"],
                defaults=company_data,
            )
            if created:
                self.stdout.write(f"Created company: {company.name}")
            else:
                self.stdout.write(f"Updated company: {company.name}")

        self.stdout.write("Test data populated successfully.")
