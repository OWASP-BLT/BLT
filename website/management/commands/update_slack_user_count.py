import logging
import os

import requests

from website.management.base import LoggedBaseCommand
from website.models import Project

logger = logging.getLogger(__name__)


class Command(LoggedBaseCommand):
    help = "Update projects with Slack member counts"

    def add_arguments(self, parser):
        parser.add_argument(
            "--project_id",
            type=int,
            help="Specify a project ID to update only that project",
        )
        parser.add_argument(
            "--slack_token",
            type=str,
            help="Slack Bot Token (overrides SLACK_BOT_TOKEN environment variable)",
        )

    def handle(self, *args, **kwargs):
        project_id = kwargs.get("project_id")
        slack_token = kwargs.get("slack_token") or os.environ.get("SLACK_BOT_TOKEN")

        if not slack_token:
            self.stdout.write(
                self.style.ERROR(
                    "SLACK_BOT_TOKEN not configured. "
                    "Please set the SLACK_BOT_TOKEN environment variable or pass via --slack_token"
                )
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
                # Use Slack API conversations.members to get accurate member count
                # The conversations.info API's num_members field is unreliable and often returns 0
                url = "https://slack.com/api/conversations.members"
                member_count = 0
                cursor = None
                api_error = False

                # Paginate through all members
                while True:
                    params = {"channel": project.slack_id, "limit": 1000}
                    if cursor:
                        params["cursor"] = cursor

                    response = requests.get(url, headers=headers, params=params, timeout=10)
                    data = response.json()

                    if data.get("ok"):
                        members = data.get("members", [])
                        member_count += len(members)

                        # Check for more pages
                        response_metadata = data.get("response_metadata", {})
                        cursor = response_metadata.get("next_cursor")
                        if not cursor:
                            break
                    else:
                        error_msg = data.get("error", "Unknown error")
                        self.stdout.write(
                            self.style.WARNING(
                                f"Failed to fetch member count for {project.name} (#{project.slack_channel}): {error_msg}"
                            )
                        )
                        failed_count += 1
                        logger.warning(
                            f"Slack API error for project {project.id} ({project.slack_channel}): {error_msg}"
                        )
                        api_error = True
                        break

                if api_error:
                    continue

                # Update the project after successful pagination
                project.slack_user_count = member_count
                project.save(update_fields=["slack_user_count"])

                self.stdout.write(
                    self.style.SUCCESS(f"Updated {project.name} (#{project.slack_channel}): {member_count} members")
                )
                updated_count += 1

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
