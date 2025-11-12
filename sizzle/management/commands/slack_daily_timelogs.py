from datetime import datetime, timedelta

from sizzle.conf import SIZZLE_SLACK_ENABLED
from sizzle.management.base import SizzleBaseCommand
from sizzle.utils.model_loader import check_slack_dependencies, get_slack_integration_model, get_timelog_model


class Command(SizzleBaseCommand):
    help = "Sends messages to organizations with a Slack integration for Sizzle timelogs to be run every hour."

    def handle(self, *args, **kwargs):
        # Check if Slack is enabled in settings
        if not SIZZLE_SLACK_ENABLED:
            self.log_warning("Slack integration is disabled in settings")
            return

        # Check if slack-bolt is available
        slack_available, slack_error = check_slack_dependencies()
        if not slack_available:
            self.log_error(f"Slack dependencies not available: {slack_error}")
            return

        # Get models dynamically
        SlackIntegration = get_slack_integration_model()
        if SlackIntegration is None:
            self.log_error(
                "SlackIntegration model not configured or available. " "Check SIZZLE_SLACK_INTEGRATION_MODEL setting."
            )
            return

        TimeLog = get_timelog_model()
        if TimeLog is None:
            self.log_error("TimeLog model not available. Ensure sizzle migrations are run.")
            return

        # Import Slack dependencies after validation

        # Get the current hour in UTC
        current_hour_utc = datetime.utcnow().hour

        # Fetch all Slack integrations with related integration data
        try:
            slack_integrations = SlackIntegration.objects.select_related("integration__organization").all()
        except Exception as e:
            self.log_error(f"Error fetching Slack integrations: {e}")
            return

        processed_count = 0
        for integration in slack_integrations:
            try:
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
                        processed_count += 1
                    else:
                        self.log_info(f"No timelogs found for organization: {current_org.name}")

            except Exception as e:
                self.log_error(f"Error processing integration for organization: {e}")
                continue

        self.log_info(f"Processed {processed_count} Slack integrations successfully")

    def format_timedelta(self, td):
        """Convert a timedelta object into a human-readable string."""
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours} hours, {minutes} minutes, {seconds} seconds"

    def send_message(self, channel_id, bot_token, message):
        """Send a message to the Slack channel."""
        try:
            # Import here after dependency validation
            from slack_bolt import App

            app = App(token=bot_token)
            app.client.conversations_join(channel=channel_id)
            response = app.client.chat_postMessage(channel=channel_id, text=message)
            self.log_info(f"Message sent successfully: {response['ts']}")
        except Exception as e:
            self.log_error(f"Error sending message: {e}")
