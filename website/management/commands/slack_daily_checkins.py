from datetime import datetime, timedelta

from slack_bolt import App

from website.management.base import LoggedBaseCommand
from website.models import DailyStatusReport, SlackIntegration


class Command(LoggedBaseCommand):
    help = "Sends messages to organizations with a Slack integration for daily check-ins to be run every hour."

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
                and current_org.check_ins_enabled
                and integration.daily_updates
                # Ensure it's the correct hour
                and integration.daily_update_time == current_hour_utc
            ):
                print(f"Processing daily check-ins for organization: {current_org.name}")

                last_24_hours = datetime.utcnow() - timedelta(hours=24)

                checkins = DailyStatusReport.objects.filter(
                    organization=current_org,
                    created__gte=last_24_hours,  # Created in the last 24 hours
                )

                if checkins.exists():
                    summary_message = f"### Daily Check-in Summary for {current_org.name} ###\n\n"

                    for checkin in checkins:
                        summary_message += (
                            f"*{checkin.user.username}* - {checkin.date}\n"
                            f"Previous Work: {checkin.previous_work[:100]}...\n"
                            f"Next Plan: {checkin.next_plan[:100]}...\n"
                            f"Blockers: {checkin.blockers[:100] if checkin.blockers else 'None'}...\n"
                            f"Goal Accomplished: {'✅ Yes' if checkin.goal_accomplished else '❌ No'}\n"
                            f"Mood: {checkin.current_mood}\n\n"
                        )

                    self.send_message(
                        integration.default_channel_id,
                        integration.bot_access_token,
                        summary_message,
                    )
                else:
                    print(f"No check-ins found for organization: {current_org.name}")

    def send_message(self, channel_id, bot_token, message):
        """Send a message to the Slack channel."""
        try:
            app = App(token=bot_token)
            app.client.conversations_join(channel=channel_id)
            response = app.client.chat_postMessage(channel=channel_id, text=message)
            print(f"Message sent successfully: {response['ts']}")
        except Exception as e:
            print(f"Error sending message: {e}")
