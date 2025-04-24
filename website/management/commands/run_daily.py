import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs commands scheduled to execute daily"

    def handle(self, *args, **options):
        try:
            logger.info(f"Starting daily scheduled tasks at {timezone.now()}")
            try:
                call_command("update_github_issues")
            except Exception as e:
                logger.error("Error updating GitHub issues", exc_info=True)
            try:
                call_command("fetch_contributor_stats")
            except Exception as e:
                logger.error("Error fetching contributor stats", exc_info=True)
            try:
                call_command("check_keywords")
            except Exception as e:
                logger.error("Error checking keywords", exc_info=True)
            try:
                call_command("check_owasp_projects")
            except Exception as e:
                logger.error("Error checking OWASP projects", exc_info=True)
            try:
                call_command("check_trademarks")
            except Exception as e:
                logger.error("Error checking trademarks", exc_info=True)
            try:
                call_command("update_repo_stars")
            except Exception as e:
                logger.error("Error updating repo stars", exc_info=True)
            try:
                call_command("fetch_gsoc_prs")
            except Exception as e:
                logger.error("Error fetching GSoC PRs", exc_info=True)
            try:
                call_command("daily_checkin_reminder")
            except Exception as e:
                logger.error("Error sending daily checkin reminders", exc_info=True)
            try:
                call_command("cron_send_reminders")
            except Exception as e:
                logger.error("Error sending user reminders", exc_info=True)
        except Exception as e:
            logger.error("Error in daily tasks", exc_info=True)
            raise
