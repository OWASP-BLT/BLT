import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import Monitor


class Command(BaseCommand):
    help = "Checks for keywords in monitored URLs"

    def handle(self, *args, **options):
        monitors = Monitor.objects.all()
        for monitor in monitors:
            try:
                response = requests.get(monitor.url)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "html.parser")
                page_content = soup.get_text()

                if monitor.keyword in page_content:
                    new_status = "UP"
                else:
                    new_status = "DOWN"

                if monitor.status != new_status:
                    monitor.status = new_status

                monitor.last_checked_time = timezone.now()
                monitor.save()

                self.stdout.write(
                    self.style.SUCCESS(f"Monitoring {monitor.url}: status {monitor.status}")
                )
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error monitoring {monitor.url}: {str(e)}"))
