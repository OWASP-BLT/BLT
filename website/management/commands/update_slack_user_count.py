import logging

import requests
from django.conf import settings

from website.management.base import LoggedBaseCommand
from website.models import Project

logger = logging.getLogger(__name__)


class Command(LoggedBaseCommand):
    help = "Update projects with Slack channel member counts"

    def add_arguments(self, parser):
        parser.add_argument(
            "--project_id",
            type=int,
            help="Specify a project ID to update only that project",
        )
        parser.add_argument(
            "--slack_token",
            type=str,
            help="Slack Bot Token (overrides settings.SLACK_BOT_TOKEN)",
        )

    def handle(self, *args, **kwargs):
        project_id = kwargs.get("project_id")
        slack_token = kwargs.get("slack_token") or getattr(settings, "SLACK_BOT_TOKEN", None)

        if not slack_token:
            self.stdout.write(
                self.style.ERROR("SLACK_BOT_TOKEN not configured. Please set it in settings or pass via --slack_token")
            )
            return

        # Filter projects that have a slack_id
        if project_id:
            projects = Project.objects.filter(id=project_id, slack_id__isnull=False).exclude(slack_id="")
        else:
            projects = Project.objects.filter(slack_id__isnull=False).exclude(slack_id="")

        if not projects.exists():
            self.stdout.write(self.style.WARNING("No projects with Slack channels found"))
            return

        headers = {"Authorization": f"Bearer {slack_token}", "Content-Type": "application/json"}

        updated_count = 0
        failed_count = 0

        for project in projects:
            try:
                # Use Slack API conversations.info to get channel information including member count
                url = "https://slack.com/api/conversations.info"
                params = {"channel": project.slack_id}

                response = requests.get(url, headers=headers, params=params, timeout=10)
                data = response.json()

                if data.get("ok"):
                    channel = data.get("channel", {})
                    member_count = channel.get("num_members", 0)

                    # Update the project
                    project.slack_user_count = member_count
                    project.save(update_fields=["slack_user_count"])

                    self.stdout.write(
                        self.style.SUCCESS(f"Updated {project.name} (#{project.slack_channel}): {member_count} members")
                    )
                    updated_count += 1
                else:
                    error_msg = data.get("error", "Unknown error")
                    self.stdout.write(
                        self.style.WARNING(
                            f"Failed to fetch member count for {project.name} (#{project.slack_channel}): {error_msg}"
                        )
                    )
                    failed_count += 1
                    logger.warning(f"Slack API error for project {project.id} ({project.slack_channel}): {error_msg}")

            except requests.exceptions.RequestException as e:
                self.stdout.write(
                    self.style.ERROR(f"Request failed for {project.name} (#{project.slack_channel}): {str(e)}")
                )
                failed_count += 1
                logger.error(f"Request exception for project {project.id}: {str(e)}", exc_info=True)

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Unexpected error for {project.name} (#{project.slack_channel}): {str(e)}")
                )
                failed_count += 1
                logger.error(f"Unexpected exception for project {project.id}: {str(e)}", exc_info=True)

        self.stdout.write(self.style.SUCCESS(f"\nCompleted: {updated_count} projects updated, {failed_count} failed"))
