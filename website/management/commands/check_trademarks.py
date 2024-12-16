from datetime import timedelta

import requests
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db import models
from django.utils.timezone import now

from website.models import Company


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


def send_email_alert(company, results_count):
    """
    Send a trademark alert email to the company's registered email.
    """
    subject = f"Trademark Alert for {company.name}"
    message = (
        f"New trademarks have been found for {company.name}.\n\n"
        f"Total trademarks now: {results_count}\n\n"
        "Please log in to the system for more details."
    )
    from_email = settings.DEFAULT_FROM_EMAIL
    print(from_email)
    recipient_list = [company.email]
    print(recipient_list)

    send_mail(subject, message, from_email, recipient_list)


class Command(BaseCommand):
    help = "Check for trademark updates and send notifications if new trademarks are found."

    def handle(self, *args, **options):
        try:
            uninitialized_companies = Company.objects.filter(
                models.Q(trademark_check_date__isnull=True) | models.Q(trademark_count__isnull=True)
            )

            if uninitialized_companies.exists():
                self.stdout.write("Initializing trademark data for all companies...")
                self.initialize_trademark_data(uninitialized_companies)
            else:
                self.stdout.write("All companies initialized. Running rate-limited checks...")
                self.rate_limited_check()

        except Exception as e:
            self.stderr.write(f"Error occurred: {e}")

    def initialize_trademark_data(self, companies):
        """
        Initialize trademark data for all companies missing information.
        """
        for company in companies:
            self.stdout.write(f"Initializing data for {company.name}...")
            response_data = search_uspto_database(company.name)
            if response_data:
                company.trademark_count = response_data.get("count", 0)
                company.trademark_check_date = now()
                self.stdout.write(
                    f"The last trademark check date for {company.name} is updated to {company.trademark_check_date}"
                )
                company.save()
                self.stdout.write(
                    f"Initialized data for {company.name}: Count = {company.trademark_count}"
                )
            else:
                self.stderr.write(f"Failed to fetch trademark data for {company.name}.")

    def rate_limited_check(self):
        """
        Perform trademark checks for companies on a rate-limited basis.
        """
        one_week_ago = now() - timedelta(weeks=1)
        company = (
            Company.objects.filter(models.Q(trademark_check_date__lt=one_week_ago))
            .order_by("trademark_check_date")
            .first()
        )
        if not company:
            self.stdout.write("No companies need a trademark search at this time.")
            return
        self.stdout.write(f"Checking trademarks for {company.name}...")

        response_data = search_uspto_database(company.name)
        if response_data:
            new_trademark_count = response_data.get("count", 0)
            if new_trademark_count > company.trademark_count:
                self.stdout.write(f"New trademarks found for {company.name}: {new_trademark_count}")
                company.trademark_count = new_trademark_count
                company.trademark_check_date = now()
                company.save()
                send_email_alert(company, new_trademark_count)
            else:
                self.stdout.write(
                    f"No new trademarks for {company.name}. Current count: {company.trademark_count}"
                )
                company.trademark_check_date = now()
                company.save()
        else:
            self.stderr.write(
                f"Failed to fetch trademark data for {company.name}. Please check the API or credentials."
            )
