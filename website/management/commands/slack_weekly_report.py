import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from slack_bolt import App

from website.models import Issue, Project, SlackIntegration, User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate and send weekly project statistics to configured Slack integrations"

    def handle(self, *args, **kwargs):
        now = timezone.now()
        last_week = now - timedelta(days=7)

        # Weekly Stats
        new_issues = Issue.objects.filter(created__gte=last_week).count()
        closed_issues = Issue.objects.filter(
            status="closed", closed_date__isnull=False, closed_date__gte=last_week
        ).count()
        new_users = User.objects.filter(date_joined__gte=last_week).count()
        total_projects = Project.objects.count()

        summary = (
            "* Weekly OWASP BLT Report*\n\n"
            f"*New Issues:* {new_issues}\n"
            f"*Closed Issues:* {closed_issues}\n"
            f"*New Users:* {new_users}\n"
            f"*Total Projects:* {total_projects}\n\n"
            "_Report generated automatically._"
        )

        success = 0
        fail = 0

        for integration in SlackIntegration.objects.all():
            if not integration.default_channel_id or not integration.bot_access_token:
                continue

            if self.send_message(integration.default_channel_id, integration.bot_access_token, summary):
                success += 1
            else:
                fail += 1

        logger.info(f"Weekly Slack report: {success} sent, {fail} failed.")

    def send_message(self, channel_id, bot_token, message):
        try:
            app = App(token=bot_token)
            app.client.conversations_join(channel=channel_id)
            app.client.chat_postMessage(channel=channel_id, text=message)
            return True
        except Exception as e:
            logger.error(f"Failed to send weekly report: {e}")
            return False
