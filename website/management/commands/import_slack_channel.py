import csv
import os

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from website.models import Project


class Command(BaseCommand):
    help = "Import Slack channels from CSV and associate them with projects"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            default="project_channels.csv",
            help="Path to CSV file containing slack channel data",
        )
        parser.add_argument(
            "--fetch-api",
            action="store_true",
            help="Fetch channels from Slack API instead of CSV",
        )

    def fetch_from_api(self):
        """Fetch Slack channels from API"""
        slack_token = getattr(settings, "SLACK_TOKEN", None)
        if not slack_token:
            self.stdout.write(self.style.ERROR("SLACK_TOKEN not configured in settings"))
            return []

        slack_api_url = "https://slack.com/api/conversations.list"
        headers = {"Authorization": f"Bearer {slack_token}"}
        params = {"limit": 1000, "types": "public_channel"}
        channels = []

        url = slack_api_url
        while url:
            try:
                response = requests.get(url, headers=headers, params=params, timeout=10)
                data = response.json()

                if not data.get("ok"):
                    self.stdout.write(self.style.ERROR(f"Slack API Error: {data.get('error')}"))
                    break

                channels.extend(data.get("channels", []))
                cursor = data.get("response_metadata", {}).get("next_cursor")
                if cursor:
                    params["cursor"] = cursor
                else:
                    url = None
            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f"Request failed: {e}"))
                break

        return channels

    def import_from_csv(self, csv_path):
        """Import slack channels from CSV file"""
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_path}"))
            return

        channels_data = []
        with open(csv_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                channels_data.append(
                    {
                        "name": row["slack_channel"],
                        "id": row["slack_id"],
                        "url": row["slack_url"],
                    }
                )

        self.process_channels(channels_data)

    def process_channels(self, channels_data):
        """Process channel data and update projects"""
        updated_count = 0
        created_count = 0

        for channel in channels_data:
            if channel["name"].startswith("project-"):
                project_name = channel["name"].replace("project-", "").replace("-", " ").title()

                # Try to find existing project by name (case-insensitive match)
                project = None
                # Try exact match first
                projects = Project.objects.filter(name__iexact=project_name)
                if projects.exists():
                    project = projects.first()
                else:
                    # Try partial match
                    projects = Project.objects.filter(name__icontains=project_name.lower())
                    if projects.count() == 1:
                        project = projects.first()

                if project:
                    # Update existing project
                    project.slack = channel.get("url") or f"https://OWASP.slack.com/archives/{channel['id']}"
                    project.slack_channel = channel["name"]
                    project.slack_id = channel["id"]
                    project.save()
                    self.stdout.write(
                        self.style.SUCCESS(f"Updated project '{project.name}' with Slack channel")
                    )
                    updated_count += 1
                else:
                    # Optionally create new project (commented out by default to avoid creating unwanted projects)
                    # project = Project.objects.create(
                    #     name=project_name,
                    #     description=f"Project imported from Slack channel {channel['name']}",
                    #     slack_channel=channel["name"],
                    #     slack_id=channel["id"],
                    #     slack=channel.get("url") or f"https://OWASP.slack.com/archives/{channel['id']}",
                    # )
                    # self.stdout.write(self.style.SUCCESS(f"Created new project: {project_name}"))
                    # created_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"No matching project found for channel '{channel['name']}' (would be: {project_name})"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nProcessed Slack channels: {updated_count} updated, {created_count} created"
            )
        )

    def handle(self, *args, **options):
        if options["fetch_api"]:
            self.stdout.write("Fetching Slack channels from API...")
            channels = self.fetch_from_api()
            if channels:
                channels_data = [
                    {
                        "name": ch["name"],
                        "id": ch["id"],
                        "url": f"https://OWASP.slack.com/archives/{ch['id']}",
                    }
                    for ch in channels
                ]
                self.process_channels(channels_data)
            else:
                self.stdout.write(self.style.WARNING("No channels fetched from API"))
        else:
            csv_path = options["csv"]
            self.stdout.write(f"Importing Slack channels from CSV: {csv_path}")
            self.import_from_csv(csv_path)

        self.stdout.write(self.style.SUCCESS("Import complete!"))
