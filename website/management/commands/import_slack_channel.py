import csv
import os

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from website.models import Project, SlackChannel  # CHANGED: import SlackChannel


class Command(BaseCommand):
    help = "Import Slack channels from CSV or Slack API and associate them with projects and SlackChannel objects"

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

    def normalize_project_name(self, channel_name: str) -> str:
        """
        Convert a Slack channel name like 'project-owasp-blt' into
        a project name like 'OWASP BLT'.
        """
        name = channel_name.lower().strip()

        # strip known prefixes
        if name.startswith("project-"):
            name = name[len("project-") :]

        # replace hyphens/underscores with spaces
        name = name.replace("-", " ").replace("_", " ").strip()

        # title-case for comparison with Project.name
        return name.title()

    # helper to normalize channel name into a project-like name
    def match_project_for_channel(self, channel_name: str):
        """
        Try to find a Project instance that corresponds to a given Slack channel name.
        Returns (project, match_type) where match_type is 'exact', 'partial', or None.
        """

        # 1) Try exact match with original channel name
        exact_qs = Project.objects.filter(name__iexact=channel_name)
        if exact_qs.exists():
            return exact_qs.first(), "exact"

        # 2) Try exact match with normalized channel name
        normalized_name = self.normalize_project_name(channel_name)
        exact_normalized_qs = Project.objects.filter(name__iexact=normalized_name)
        if exact_normalized_qs.exists():
            return exact_normalized_qs.first(), "exact"

        # 3) Normalize project names too (handles: project-zap → www-project-zap)
        for project in Project.objects.all():
            if self.normalize_project_name(project.name) == normalized_name:
                return project, "exact"

        # 4) Partial match
        partial_qs = Project.objects.filter(name__icontains=normalized_name.lower())
        if partial_qs.count() == 1:
            return partial_qs.first(), "partial"

        return None, None

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

        # normalize API response into the same structure used by CSV
        channels_data = []
        for ch in channels:
            channels_data.append(
                {
                    "name": ch.get("name", ""),
                    "id": ch.get("id", ""),
                    "url": f"https://OWASP.slack.com/archives/{ch.get('id')}",
                }
            )
        return channels_data

    def import_from_csv(self, csv_path):
        """Import slack channels from CSV file"""
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_path}"))
            return []

        channels_data = []
        with open(csv_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # keep naming consistent with API struct
                channels_data.append(
                    {
                        "name": row.get("slack_channel", "").strip(),
                        "id": row.get("slack_id", "").strip(),
                        "url": row.get("slack_url", "").strip(),
                    }
                )

        return channels_data

    def process_channels(self, channels_data):
        """
        Process channel data:
        - create/update SlackChannel objects
        - link them to Projects
        - maintain backward compatibility with Project.slack fields
        """
        slack_created = 0
        slack_updated = 0
        projects_linked = 0
        unmatched_channels = 0

        for channel in channels_data:
            name = channel.get("name") or ""
            channel_id = channel.get("id") or ""
            url = channel.get("url") or ""

            if not name or not channel_id:
                self.stdout.write(self.style.WARNING(f"Skipping channel with missing name or id: {channel}"))
                continue

            # Default URL if not provided
            if not url:
                url = f"https://OWASP.slack.com/archives/{channel_id}"

            # create or update SlackChannel object
            slack_obj, created = SlackChannel.objects.update_or_create(
                channel_id=channel_id,
                defaults={
                    "name": name,
                    "slack_url": url,
                },
            )

            if created:
                slack_created += 1
            else:
                slack_updated += 1

            # Match project using improved logic
            project, match_type = self.match_project_for_channel(name)

            if project and match_type:
                # Link SlackChannel to Project
                slack_obj.project = project
                slack_obj.save(update_fields=["project"])

                # Backward compatibility: also update Project fields
                project.slack = url
                project.slack_channel = name
                project.slack_id = channel_id
                project.save(update_fields=["slack", "slack_channel", "slack_id"])

                projects_linked += 1

                if match_type == "exact":
                    self.stdout.write(self.style.SUCCESS(f"[EXACT] Linked channel '{name}' → project '{project.name}'"))
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"[PARTIAL] Linked channel '{name}' → project '{project.name}'")
                    )
            else:
                # No reliable match found
                unmatched_channels += 1
                self.stdout.write(
                    self.style.WARNING(f"[UNMATCHED] No project found for channel '{name}' (id: {channel_id})")
                )

        # Summary logging
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Slack channel import summary"))
        self.stdout.write(self.style.SUCCESS(f"  SlackChannel created: {slack_created}"))
        self.stdout.write(self.style.SUCCESS(f"  SlackChannel updated: {slack_updated}"))
        self.stdout.write(self.style.SUCCESS(f"  Projects linked:      {projects_linked}"))
        self.stdout.write(self.style.WARNING(f"  Unmatched channels:   {unmatched_channels}"))

    def handle(self, *args, **options):
        if options["fetch_api"]:
            self.stdout.write("Fetching Slack channels from Slack API...")
            channels_data = self.fetch_from_api()
        else:
            csv_path = options["csv"]
            self.stdout.write(f"Importing Slack channels from CSV: {csv_path}")
            channels_data = self.import_from_csv(csv_path)

        if not channels_data:
            self.stdout.write(self.style.WARNING("No channels to process"))
            return

        self.process_channels(channels_data)
        self.stdout.write(self.style.SUCCESS("Import complete!"))
