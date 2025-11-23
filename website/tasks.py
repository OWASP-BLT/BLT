import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task(name="website.tasks.send_weekly_stats")
def send_weekly_stats():
    """
    Celery task to send weekly statistics report to all registered organizations.
    This task is scheduled to run weekly via Celery Beat.
    """
    from website.models import Domain, Issue

    logger.info("Starting weekly stats delivery task")

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

            # Get most recent issues ordered by creation date, optimized to avoid N+1 queries
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

            for issue in issues:  # Already limited to 10 most recent
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
            logger.error(f"Failed to send weekly report to {domain.email} for {domain.name}: {str(e)}", exc_info=True)

    logger.info(f"Weekly stats delivery completed. Sent: {reports_sent}, Failed: {reports_failed}")
    return {"sent": reports_sent, "failed": reports_failed}
