from datetime import datetime, timedelta

from slack_bolt import App

from sizzle.management.base import SizzleBaseCommand
# Import from website app since models haven't been migrated yet
from website.models import SlackIntegration, TimeLog


class Command(SizzleBaseCommand):
    help = "Sends messages to organizations with a Slack integration for Sizzle timelogs to be run every hour."

    def handle(self, *args, **kwargs):
        # Get the current hour in UTC
        current_hour_utc = datetime.utcnow().hour

        # Fetch all Slack integrations with related integration data
        slack_integrations = SlackIntegration.objects.select_related("integration__organization").all()

        for integration in slack_integrations:
            current_org = integration.integration.organization
            if (
                integration.default_channel_id
                and current_org
                and integration.daily_updates
                # Ensure it's the correct hour
                and integration.daily_update_time == current_hour_utc
            ):
                self.log_info(f"Processing updates for organization: {current_org.name}")

                last_24_hours = datetime.utcnow() - timedelta(hours=24)

                timelog_history = TimeLog.objects.filter(
                    organization=current_org,
                    start_time__isnull=False,
                    end_time__isnull=False,
                    end_time__gte=last_24_hours,  # Ended in the last 24 hours
                )

                if timelog_history.exists():
                    total_time = timedelta()
                    summary_message = "### Time Log Summary ###\n\n"

                    for timelog in timelog_history:
                        st = timelog.start_time
                        et = timelog.end_time
                        issue_url = timelog.github_issue_url if timelog.github_issue_url else "No issue URL"
                        summary_message += (
                            f"Task: {timelog}\n" f"Start: {st}\n" f"End: {et}\n" f"Issue URL: {issue_url}\n\n"
                        )
                        total_time += et - st

                    human_friendly_total_time = self.format_timedelta(total_time)
                    summary_message += f"Total Time: {human_friendly_total_time}"

                    self.send_message(
                        integration.default_channel_id,
                        integration.bot_access_token,
                        summary_message,
                    )

    def format_timedelta(self, td):
        """Convert a timedelta object into a human-readable string."""
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours} hours, {minutes} minutes, {seconds} seconds"

    def send_message(self, channel_id, bot_token, message):
        """Send a message to the Slack channel."""
        try:
            app = App(token=bot_token)
            app.client.conversations_join(channel=channel_id)
            response = app.client.chat_postMessage(channel=channel_id, text=message)
            self.log_info(f"Message sent successfully: {response['ts']}")
        except Exception as e:
            self.log_error(f"Error sending message: {e}")