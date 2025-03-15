import time

import requests
from django.conf import settings
from django.utils import timezone

from website.management.base import LoggedBaseCommand
from website.models import Organization, Trademark, TrademarkOwner


class Command(LoggedBaseCommand):
    help = "Fetch trademark information for organizations and store it in the database"

    def handle(self, *args, **kwargs):
        organizations = Organization.objects.all()

        for organization in organizations:
            name = organization.name
            retries = 3  # Number of retries
            while retries > 0:
                try:
                    # Logging start of data fetching
                    self.stdout.write(self.style.NOTICE(f"Starting data fetch for organization: {name}"))

                    # Fetch trademark data
                    url = "https://uspto-trademark.p.rapidapi.com/v1/batchTrademarkSearch/"
                    initial_payload = {
                        "keywords": f' ["{name}"]',
                        "start_index": "0",
                    }
                    headers = {
                        "x-rapidapi-key": f"{settings.USPTO_API}",
                        "x-rapidapi-host": "uspto-trademark.p.rapidapi.com",
                        "Content-Type": "application/x-www-form-urlencoded",
                    }
                    response = requests.post(url, data=initial_payload, headers=headers)
                    response.raise_for_status()
                    response_json = response.json()

                    # The initial call returns a scroll_id, which is then used to obtain pagination results
                    scroll_id = response_json.get("scroll_id")
                    pagination_payload = {
                        "keywords": f' ["{name}"]',
                        "start_index": "0",
                        "scroll_id": scroll_id,
                    }
                    response = requests.post(url, data=pagination_payload, headers=headers)
                    response.raise_for_status()
                    results = response.json().get("results")

                    print(results)

                    # Store trademark data in the database
                    if results:
                        for item in results:
                            trademark, created = Trademark.objects.update_or_create(
                                keyword=item["keyword"],
                                registration_number=item.get("registration_number"),
                                serial_number=item.get("serial_number"),
                                status_label=item.get("status_label"),
                                status_code=item.get("status_code"),
                                status_date=item.get("status_date"),
                                status_definition=item.get("status_definition"),
                                filing_date=item.get("filing_date"),
                                registration_date=item.get("registration_date"),
                                abandonment_date=item.get("abandonment_date"),
                                expiration_date=item.get("expiration_date"),
                                description=item.get("description"),
                                organization=organization,
                            )

                            # Update or create owners
                            if item.get("owners"):
                                for owner_data in item["owners"]:
                                    owner, owner_created = TrademarkOwner.objects.update_or_create(
                                        name=owner_data.get("name"),
                                        address1=owner_data.get("address1"),
                                        address2=owner_data.get("address2"),
                                        city=owner_data.get("city"),
                                        state=owner_data.get("state"),
                                        country=owner_data.get("country"),
                                        postcode=owner_data.get("postcode"),
                                        owner_type=owner_data.get("owner_type"),
                                        owner_label=owner_data.get("owner_label"),
                                        legal_entity_type=owner_data.get("legal_entity_type"),
                                        legal_entity_type_label=owner_data.get("legal_entity_type_label"),
                                    )
                                    trademark.owners.add(owner)

                    organization.trademark_check_date = timezone.now()
                    organization.trademark_count = results and len(results) or 0
                    organization.save()

                    self.stdout.write(self.style.SUCCESS(f"Successfully stored data for organization: {name}"))

                    # Introduced delay between requests to avoid rate limiting
                    time.sleep(2)

                    break
                except requests.exceptions.RequestException as e:
                    retries -= 1
                    if retries == 0:
                        self.stdout.write(self.style.ERROR(f"Failed to fetch data for {name}: {e}"))
                    else:
                        # Retry after a delay if rate limited
                        self.stdout.write(
                            self.style.WARNING(f"Retrying for {name} due to {e}. Retries left: {retries}")
                        )
                        time.sleep(5)

        self.stdout.write(self.style.SUCCESS("Successfully fetched and stored trademark data for all organizations"))

