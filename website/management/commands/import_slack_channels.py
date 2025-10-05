import csv
import os

from django.core.management.base import BaseCommand

from website.models import Project


class Command(BaseCommand):
    help = "Import slack channels from CSV file and associate them with projects"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="project_channels.csv",
            help="Path to the CSV file containing the slack channel data",
        )

    def handle(self, *args, **kwargs):
        csv_file_path = kwargs["csv_file"]

        self.stdout.write(f"Importing slack channels from CSV file: {csv_file_path}")

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_file_path}"))
            return

        updated_count = 0

        with open(csv_file_path, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                slack_channel = row.get("slack_channel", "").strip()
                slack_id = row.get("slack_id", "").strip()
                slack_url = row.get("slack_url", "").strip()

                if not slack_channel or not slack_channel.startswith("project-"):
                    continue

                project_name = slack_channel.replace("project-", "").replace("-", " ").title()

                project = Project.objects.filter(name__iexact=project_name).first()

                if project:
                    updated = False
                    if project.slack_channel != slack_channel:
                        project.slack_channel = slack_channel
                        updated = True

                    if project.slack_id != slack_id:
                        project.slack_id = slack_id
                        updated = True

                    if project.slack != slack_url:
                        project.slack = slack_url
                        updated = True

                    if updated:
                        project.save()
                        updated_count += 1
                        self.stdout.write(f"Updated project: {project_name}")
                else:
                    self.stdout.write(self.style.WARNING(f"No project found with name: {project_name}"))

        self.stdout.write(self.style.SUCCESS(f"Successfully processed CSV. Updated {updated_count} projects."))
