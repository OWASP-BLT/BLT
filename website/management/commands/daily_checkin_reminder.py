import logging
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from slack_sdk.errors import SlackApiError
from slack_sdk.web import WebClient

from website.models import Notification, ReminderSettings, UserProfile

if os.getenv("ENV") != "production":
    from dotenv import load_dotenv

    load_dotenv()

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sends daily check-in reminders to users in organizations with check-ins enabled"

    def handle(self, *args, **options):
        userprofiles_with_checkins = UserProfile.objects.filter(team__check_ins_enabled=True)

        # Send in-app notifications
        notifications = [
            Notification(
                user=userprofile.user,
                message=f"This is a reminder to add your daily check-in for {userprofile.team.name}",
                notification_type="reminder",
                link="/add-sizzle-checkin/",
            )
            for userprofile in userprofiles_with_checkins
        ]
        Notification.objects.bulk_create(notifications)
        self.stdout.write(
            self.style.SUCCESS(f"Sent check-in reminder notifications to {len(userprofiles_with_checkins)} users.")
        )

        # Send Slack DM reminders for users who have it enabled
        if SLACK_BOT_TOKEN:
            slack_reminders_sent = 0
            client = WebClient(token=SLACK_BOT_TOKEN)

            # Get the base URL from settings or use a default
            base_url = getattr(settings, "BASE_URL", "https://www.owasp.org")
            checkin_url = f"{base_url}/add-sizzle-checkin/"

            for userprofile in userprofiles_with_checkins:
                try:
                    # Check if user has reminder settings with Slack enabled
                    reminder_settings = ReminderSettings.objects.filter(
                        user=userprofile.user, is_active=True, slack_notifications_enabled=True
                    ).first()

                    if reminder_settings and userprofile.slack_user_id:
                        # Send Slack DM
                        message = (
                            f"Hello {userprofile.user.username}! 👋\n\n"
                            f"This is your daily reminder to complete your check-in for {userprofile.team.name}.\n\n"
                            f"Complete your check-in here: {checkin_url}"
                        )

                        response = client.chat_postMessage(channel=userprofile.slack_user_id, text=message)

                        if response.get("ok"):
                            slack_reminders_sent += 1
                        else:
                            logger.warning(
                                f"Failed to send Slack reminder to {userprofile.user.username}: {response.get('error')}"
                            )

                except SlackApiError:
                    logger.error(
                        f"Slack API error when sending reminder to {userprofile.user.username}. "
                        "Please verify the bot token and user's Slack connection."
                    )
                except Exception:
                    logger.error(
                        f"Unexpected error sending Slack reminder to {userprofile.user.username}. "
                        "Please check the logs for more details."
                    )

            if slack_reminders_sent > 0:
                self.stdout.write(self.style.SUCCESS(f"Sent Slack reminders to {slack_reminders_sent} users."))
        else:
            logger.warning("SLACK_BOT_TOKEN not configured. Skipping Slack reminders.")
