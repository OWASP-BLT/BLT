from datetime import timedelta

import requests
from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.utils.timezone import now

from website.management.base import LoggedBaseCommand
from website.models import Organization


def search_uspto_database(term):
    """
    Search the USPTO trademark database using RapidAPI.
    """
    if not term or not term.strip():
        print(f"Error: Empty or invalid term {term} provided for USPTO search.")
        return None

    url = "https://uspto-trademark.p.rapidapi.com/v1/batchTrademarkSearch/"
    payload = {"keywords": f'["{term}"]', "start_index": "0"}
    print(payload)
    headers = {
        "x-rapidapi-key": f"{settings.USPTO_API}",
        "x-rapidapi-host": "uspto-trademark.p.rapidapi.com",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    response = requests.post(url, data=payload, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: Received status code {response.status_code} - {response.reason}")
        print(response.json())
    return None


def send_email_alert(organization, results_count):
    """
    Send a trademark alert email to the organization's registered email.
    """
    subject = f"Trademark Alert for {organization.name}"
    message = (
        f"New trademarks have been found for {organization.name}.\n\n"
        f"Total trademarks now: {results_count}\n\n"
        "Please log in to the system for more details."
    )
    from_email = settings.DEFAULT_FROM_EMAIL
    print(from_email)
    recipient_list = [organization.email]
    print(recipient_list)

    send_mail(subject, message, from_email, recipient_list)


class Command(LoggedBaseCommand):
    help = "Check for trademark updates and send notifications if new trademarks are found."

    def handle(self, *args, **options):
        try:
            uninitialized_organizations = Organization.objects.filter(
                models.Q(trademark_check_date__isnull=True) | models.Q(trademark_count__isnull=True)
            )

            if uninitialized_organizations.exists():
                self.stdout.write("Initializing trademark data for all organizations...")
                self.initialize_trademark_data(uninitialized_organizations)
            else:
                self.stdout.write("All organizations initialized. Running rate-limited checks...")
                self.rate_limited_check()

        except Exception as e:
            self.stderr.write(f"Error occurred: {e}")

    def initialize_trademark_data(self, organizations):
        """
        Initialize trademark data for all organizations missing information.
        """
        for organization in organizations:
            self.stdout.write(f"Initializing data for {organization.name}...")
            response_data = search_uspto_database(organization.name)
            if response_data:
                organization.trademark_count = response_data.get("count", 0)
                organization.trademark_check_date = now()
                self.stdout.write(
                    f"The last trademark check date for {organization.name} is updated to {organization.trademark_check_date}"
                )
                organization.save()
                self.stdout.write(f"Initialized data for {organization.name}: Count = {organization.trademark_count}")
            else:
                self.stderr.write(f"Failed to fetch trademark data for {organization.name}.")

    def rate_limited_check(self):
        """
        Perform trademark checks for organizations on a rate-limited basis.
        """
        one_week_ago = now() - timedelta(weeks=1)
        organization = (
            Organization.objects.filter(models.Q(trademark_check_date__lt=one_week_ago))
            .order_by("trademark_check_date")
            .first()
        )
        if not organization:
            self.stdout.write("No organizations need a trademark search at this time.")
            return
        self.stdout.write(f"Checking trademarks for {organization.name}...")

        response_data = search_uspto_database(organization.name)
        if response_data:
            new_trademark_count = response_data.get("count", 0)
            if new_trademark_count > organization.trademark_count:
                self.stdout.write(f"New trademarks found for {organization.name}: {new_trademark_count}")
                organization.trademark_count = new_trademark_count
                organization.trademark_check_date = now()
                organization.save()
                send_email_alert(organization, new_trademark_count)
            else:
                self.stdout.write(
                    f"No new trademarks for {organization.name}. Current count: {organization.trademark_count}"
                )
                organization.trademark_check_date = now()
                organization.save()
        else:
            self.stderr.write(
                f"Failed to fetch trademark data for {organization.name}. Please check the API or credentials."
            )

