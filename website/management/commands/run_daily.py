import logging

from django.core import management
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)

# Commands to run daily, in order
DAILY_COMMANDS = [
    ("update_github_issues", "updating GitHub issues"),
    ("fetch_contributor_stats", "fetching contributor stats"),
    ("check_keywords", "checking keywords"),
    ("check_owasp_projects", "checking OWASP projects"),
    ("check_trademarks", "checking trademarks"),
    ("update_repo_stars", "updating repo stars"),
    ("fetch_gsoc_prs", "fetching GSoC PRs"),
    ("fetch_pr_reviews", "fetching PR reviews"),
    ("cron_send_reminders", "sending user reminders"),
]


class Command(BaseCommand):
    help = "Runs commands scheduled to execute daily"

    def handle(self, *args, **options):
        logger.info(f"Starting daily scheduled tasks at {timezone.now()}")

        succeeded = 0
        failed = 0

        for command_name, description in DAILY_COMMANDS:
            try:
                management.call_command(command_name)
                succeeded += 1
            except Exception:
                logger.exception(f"Error {description}")
                failed += 1

        logger.info(f"Daily tasks complete: {succeeded} succeeded, {failed} failed")
