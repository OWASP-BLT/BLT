import requests
from django.core.management.base import BaseCommand
from website.models import SlackChannel
from django.conf import settings
SLACK_TOKEN = settings.SLACK_TOKEN
SLACK_API_URL = "https://slack.com/api/conversations.list"
HEADERS = {"Authorization": f"Bearer {SLACK_TOKEN}"}

class Command(BaseCommand):
    help = "Fetch Slack channels and save them to the database"

    def fetch_channels(self):
        url = SLACK_API_URL
        params = {"limit": 1000, "types": "public_channel"}  # Fetch only public channels
        channels = []

        while url:
            response = requests.get(url, headers=HEADERS, params=params)
            data = response.json()

            if not data.get("ok"):
                self.stdout.write(f"Error: {data.get('error')}")
                break

            channels.extend(data.get("channels", []))
            cursor = data.get("response_metadata", {}).get("next_cursor")
            if cursor:
                url = SLACK_API_URL + f"?cursor={cursor}"
            else:
                url = None

        return channels

    def handle(self, *args, **kwargs):
        self.stdout.write("Fetching Slack channels...")

        channels = self.fetch_channels()
        for channel in channels:
            if channel["name"].startswith("project-"):
                SlackChannel.objects.update_or_create(
                    slack_id=channel["id"],
                    defaults={
                        "slack_channel": channel["name"],
                        "slack_url": f"https://OWASP.slack.com/archives/{channel['id']}"
                    }
                )

        self.stdout.write(f"Imported {len(channels)} Slack channels.")
