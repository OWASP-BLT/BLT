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
            call_command("update_github_issues")
            call_command("fetch_contributor_stats")
            call_command("check_keywords")
            call_command("check_owasp_projects")
            call_command("check_trademarks")
        except Exception as e:
            logger.error(f"Error in daily tasks: {str(e)}")
            raise
