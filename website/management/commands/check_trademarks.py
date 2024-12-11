# management/commands/check_trademarks.py
import requests
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from website.models import Company


def search_uspto_database(term):
    """
    Search the USPTO trademark database using RapidAPI.
    """
    url = "https://uspto-trademark.p.rapidapi.com/v1/batchTrademarkSearch/"
    payload = {"keywords": f'["{term}"]', "start_index": "0"}
    headers = {
        "x-rapidapi-key": f"{settings.USPTO_API}",  # Ensure this is set in settings.py
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
    recipient_list = [company.email]

    send_mail(subject, message, from_email, recipient_list)


class Command(BaseCommand):
    help = "Check for trademark updates and send notifications if new trademarks are found."

    def handle(self, *args, **options):
        try:
            companies = Company.objects.all()
            self.stdout.write(f"Found {companies.count()} companies.")
            # Rest of the logic
        except Exception as e:
            self.stderr.write(f"Error occurred: {e}")

        self.stdout.write("Command completed.")

        # Query for all companies
        companies = Company.objects.all()

        for company in companies:
            self.stdout.write(f"Checking trademarks for {company.name}...")

            # Call the USPTO search function
            response_data = search_uspto_database(company.name)

            if response_data:
                new_trademark_count = response_data.get("count", 0)

                # Compare and update database if there's a change
                if new_trademark_count > company.trademark:
                    self.stdout.write(
                        f"New trademarks found for {company.name}: {new_trademark_count}"
                    )

                    # Update the database
                    company.trademark = new_trademark_count
                    company.save()

                    # Send the email alert
                    send_email_alert(company, new_trademark_count)

                else:
                    self.stdout.write(
                        f"No new trademarks for {company.name}. Current count: {company.trademark}"
                    )
            else:
                self.stderr.write(
                    f"Failed to fetch trademark data for {company.name}. Please check the API or credentials."
                )
