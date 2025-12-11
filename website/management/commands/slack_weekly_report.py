import logging
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from slack_bolt import App

from website.models import SlackIntegration, Issue, User, Project

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send weekly Slack report every Saturday at 1pm EST"

    def handle(self, *args, **kwargs):
        now = datetime.utcnow()
        last_week = now - timedelta(days=7)

        # Pull weekly stats
        new_issues = Issue.objects.filter(created__gte=last_week).count()
        closed_issues = Issue.objects.filter(status="closed", closed_date__gte=last_week).count()
        new_users = User.objects.filter(date_joined__gte=last_week).count()
        total_projects = Project.objects.count()

        summary = (
            "*📊 Weekly OWASP BLT Report*\n\n"
            f"*🆕 New Issues:* {new_issues}\n"
            f"*✔️ Closed Issues:* {closed_issues}\n"
            f"*👤 New Users:* {new_users}\n"
            f"*📁 Total Projects:* {total_projects}\n\n"
            "_Report generated automatically._"
        )

        # Send to all Slack integrations
        slack_integrations = SlackIntegration.objects.all()

        for integration in slack_integrations:
            if not integration.default_channel_id or not integration.bot_access_token:
                continue

            self.send_message(
                integration.default_channel_id,
                integration.bot_access_token,
                summary,
            )

        logger.info("Weekly Slack report sent successfully.")

    def send_message(self, channel_id, bot_token, message):
        """Send a message to the Slack channel."""
        try:
            app = App(token=bot_token)
            app.client.conversations_join(channel=channel_id)
            app.client.chat_postMessage(channel=channel_id, text=message)
        except Exception as e:
            logger.error(f"Failed to send weekly report: {e}")
