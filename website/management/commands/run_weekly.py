import logging

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import Domain, Issue

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs commands scheduled to execute weekly"

    def handle(self, *args, **options):
        try:
            logger.info(f"Starting weekly scheduled tasks at {timezone.now()}")

            # Send weekly statistics reports
            self.stdout.write("Sending weekly statistics reports...")
            sent, failed = self.send_weekly_stats()
            self.stdout.write(self.style.SUCCESS(f"Weekly stats sent: {sent} successful, {failed} failed"))

            logger.info("Weekly scheduled tasks completed successfully")
        except Exception as e:
            logger.error(f"Error in weekly tasks: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
            raise

    def send_weekly_stats(self):
        """
        Send weekly statistics report to all registered organizations.
        Returns tuple of (reports_sent, reports_failed).
        """
        domains = Domain.objects.all()
        reports_sent = 0
        reports_failed = 0

        for domain in domains:
            try:
                if not domain.email:
                    logger.warning(f"Skipping domain {domain.name} - no email configured")
                    continue

                open_issues = domain.open_issues
                closed_issues = domain.closed_issues
                total_issues = open_issues.count() + closed_issues.count()

                # Get most recent issues ordered by creation date
                issues = Issue.objects.filter(domain=domain).order_by("-created")[:10]

                # Build the report
                report_lines = [
                    "Hey! This is a weekly report from OWASP BLT regarding the bugs reported for your organization!\n\n",
                    f"Organization Name: {domain.name}\n",
                    f"Open issues: {open_issues.count()}\n",
                    f"Closed issues: {closed_issues.count()}\n",
                    f"Total issues: {total_issues}\n\n",
                    "Recent Issues:\n",
                ]

                for issue in issues:
                    description = issue.description[:100] if issue.description else "No description"
                    label = issue.get_label_display()
                    report_lines.append(f"- Description: {description}...\n  Views: {issue.views} | Label: {label}\n")

                report_string = "".join(report_lines)

                # Send email
                send_mail(
                    "OWASP BLT Weekly Report",
                    report_string,
                    settings.DEFAULT_FROM_EMAIL,
                    [domain.email],
                    fail_silently=False,
                )

                reports_sent += 1
                logger.info(f"Weekly report sent successfully to {domain.email} for {domain.name}")

            except Exception as e:
                reports_failed += 1
                logger.error(
                    f"Failed to send weekly report to {domain.email} for {domain.name}: {str(e)}",
                    exc_info=True,
                )

        return reports_sent, reports_failed
