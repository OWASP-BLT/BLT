import logging
import os
from datetime import datetime
from datetime import timezone as dt_timezone

import requests
from django.db.models import Q

from website.management.base import LoggedBaseCommand
from website.models import Project, SlackChannel

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

    def fetch_all_channels(self, headers):
        """Fetch all public channels from Slack to build a name->id mapping and save to database."""
        channels_map = {}
        url = "https://slack.com/api/conversations.list"
        cursor = None
        channels_saved = 0

        while True:
            params = {"limit": 1000, "types": "public_channel"}
            if cursor:
                params["cursor"] = cursor

            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                data = response.json()

                if data.get("ok"):
                    for channel in data.get("channels", []):
                        channel_id = channel.get("id")
                        channel_name = channel.get("name")
                        channels_map[channel_name] = channel_id

                        # Extract topic and purpose values
                        topic = channel.get("topic", {}).get("value", "") or ""
                        purpose = channel.get("purpose", {}).get("value", "") or ""

                        # Convert created timestamp to datetime
                        created_timestamp = channel.get("created")
                        created_at = None
                        if created_timestamp:
                            created_at = datetime.fromtimestamp(created_timestamp, tz=dt_timezone.utc)

                        # Save or update channel in database
                        SlackChannel.objects.update_or_create(
                            channel_id=channel_id,
                            defaults={
                                "name": channel_name,
                                "topic": topic,
                                "purpose": purpose,
                                "num_members": channel.get("num_members", 0),
                                "is_private": channel.get("is_private", False),
                                "is_archived": channel.get("is_archived", False),
                                "is_general": channel.get("is_general", False),
                                "creator": channel.get("creator", ""),
                                "created_at": created_at,
                                "slack_url": f"https://owasp.slack.com/archives/{channel_id}",
                            },
                        )
                        channels_saved += 1

                    # Check for more pages
                    response_metadata = data.get("response_metadata", {})
                    cursor = response_metadata.get("next_cursor")
                    if not cursor:
                        break
                else:
                    error_msg = data.get("error", "Unknown error")
                    self.stdout.write(self.style.WARNING(f"Failed to fetch channels list: {error_msg}"))
                    logger.warning(f"Slack API error fetching channels: {error_msg}")
                    break
            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f"Request failed fetching channels: {str(e)}"))
                logger.error(f"Request exception fetching channels: {str(e)}", exc_info=True)
                break

        if channels_saved > 0:
            self.stdout.write(self.style.SUCCESS(f"Saved/updated {channels_saved} Slack channels to database"))

        return channels_map

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

        # Filter projects that have a slack_id OR have a slack_channel name (to resolve)
        # Projects with slack_id can have member count updated directly
        # Projects with slack_channel but no slack_id need channel lookup first
        if project_id:
            projects = Project.objects.filter(
                Q(id=project_id)
                & (
                    (Q(slack_id__isnull=False) & ~Q(slack_id=""))
                    | (Q(slack_channel__isnull=False) & ~Q(slack_channel=""))
                )
            )
        else:
            projects = Project.objects.filter(
                (Q(slack_id__isnull=False) & ~Q(slack_id="")) | (Q(slack_channel__isnull=False) & ~Q(slack_channel=""))
            )

        if not projects.exists():
            self.stdout.write(self.style.WARNING("No projects with Slack channels found"))
            return

        headers = {"Authorization": f"Bearer {slack_token}", "Content-Type": "application/json"}

        # Check if we need to fetch channel list (for projects missing slack_id)
        channels_map = None
        needs_channel_lookup = projects.filter(
            Q(slack_id__isnull=True) | Q(slack_id=""), slack_channel__isnull=False
        ).exclude(slack_channel="")
        if needs_channel_lookup.exists():
            self.stdout.write("Fetching Slack channels list for channel name resolution...")
            channels_map = self.fetch_all_channels(headers)

        updated_count = 0
        resolved_count = 0
        failed_count = 0

        for project in projects:
            try:
                channel_id = project.slack_id

                # If project has slack_channel but no slack_id, try to resolve it
                if (not channel_id or channel_id == "") and project.slack_channel:
                    if channels_map is None:
                        self.stdout.write(
                            self.style.WARNING(f"Skipping {project.name}: has channel name but channel lookup failed")
                        )
                        failed_count += 1
                        continue

                    # Normalize channel name (remove # prefix if present)
                    channel_name = project.slack_channel.lstrip("#")

                    if channel_name in channels_map:
                        channel_id = channels_map[channel_name]
                        # Update project with resolved slack_id and slack URL
                        project.slack_id = channel_id
                        project.slack = f"https://owasp.slack.com/archives/{channel_id}"
                        # Link the SlackChannel to the project
                        try:
                            slack_channel_obj = SlackChannel.objects.get(channel_id=channel_id)
                            slack_channel_obj.project = project
                            slack_channel_obj.save(update_fields=["project"])
                        except SlackChannel.DoesNotExist:
                            pass
                        project.save(update_fields=["slack_id", "slack"])
                        self.stdout.write(
                            self.style.SUCCESS(f"Resolved channel for {project.name}: #{channel_name} -> {channel_id}")
                        )
                        resolved_count += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"Could not find channel '{channel_name}' for {project.name}")
                        )
                        failed_count += 1
                        continue

                # Skip if we still don't have a channel_id
                if not channel_id:
                    self.stdout.write(self.style.WARNING(f"Skipping {project.name}: no slack channel ID available"))
                    failed_count += 1
                    continue

                # Use Slack API conversations.members to get accurate member count
                # The conversations.info API's num_members field is unreliable and often returns 0
                url = "https://slack.com/api/conversations.members"
                member_count = 0
                cursor = None
                api_error = False

                # Paginate through all members
                while True:
                    params = {"channel": channel_id, "limit": 1000}
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

                # Also link SlackChannel to project if not already linked
                try:
                    slack_channel_obj = SlackChannel.objects.get(channel_id=channel_id)
                    if not slack_channel_obj.project:
                        slack_channel_obj.project = project
                        slack_channel_obj.save(update_fields=["project"])
                except SlackChannel.DoesNotExist:
                    pass

                # Also update the SlackChannel table with accurate member count
                SlackChannel.objects.filter(channel_id=channel_id).update(num_members=member_count)

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

        self.stdout.write(
            self.style.SUCCESS(
                f"\nCompleted: {updated_count} projects updated, {resolved_count} channels resolved, {failed_count} failed"
            )
        )
