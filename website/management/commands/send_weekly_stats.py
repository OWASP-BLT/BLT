import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import Domain, Issue

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send weekly statistics emails to all domains with organization owners"

    def handle(self, *args, **options):
        """
        Main function that runs when command is executed.
        Sends weekly reports to domains that have organizations with owners.
        """
        self.stdout.write(self.style.WARNING("Starting weekly statistics email delivery..."))

        # Filter domains: must have organization AND organization must have owner (admin)
        domains = Domain.objects.filter(
            organization__isnull=False,  
            organization__admin__isnull=False,  
            email__isnull=False, 
        ).exclude(email="") 

        total_domains = domains.count()
        successful_sends = 0
        failed_sends = 0

        self.stdout.write(self.style.NOTICE(f"Found {total_domains} domains to process"))

        # Calculate date range for weekly report
        week_ago = timezone.now() - timedelta(days=7)

        # Process each domain individually
        for domain in domains:
            try:
                # Generate report data for this domain - FILTER BY WEEK
                open_issues = domain.open_issues.filter(created__gte=week_ago)
                closed_issues = domain.closed_issues.filter(created__gte=week_ago)
                
                # Store counts to avoid redundant queries
                open_count = open_issues.count()
                closed_count = closed_issues.count()
                total_issues = open_count + closed_count
                
                issues = Issue.objects.filter(domain=domain, created__gte=week_ago)

                # Build the email message
                report_data = [
                    "Hey! This is a weekly report from OWASP BLT regarding the bugs reported for your organization!\n\n"
                ]

                # Use organization name, not domain name
                report_data.append(
                    f"Organization Name: {domain.organization.name}\n"
                    f"Open issues: {open_count}\n"
                    f"Closed issues: {closed_count}\n"
                    f"Total issues: {total_issues}\n\n"
                )

                # Add individual issue details
                if issues.exists():
                    report_data.append("Issue Details:\n")
                    report_data.append("-" * 50 + "\n")
                    for issue in issues:
                        description = issue.description
                        views = issue.views
                        label = issue.get_label_display()
                        report_data.append(
                            f"\nDescription: {description}\n"
                            f"Views: {views}\n"
                            f"Labels: {label}\n"
                            f"{'-' * 50}\n"
                        )
                else:
                    report_data.append("No issues reported this week.\n")

                report_string = "".join(report_data)

                # Send the email
                send_mail(
                    subject="Weekly Report from OWASP BLT",
                    message=report_string,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[domain.email],
                    fail_silently=False,
                )

                successful_sends += 1
                logger.info(f"Successfully sent weekly stats to {domain.organization.name} ({domain.email})")
                self.stdout.write(self.style.SUCCESS(f"✓ Sent to {domain.organization.name} ({domain.email})"))

            except Exception as e:
                failed_sends += 1
                logger.error(f"Failed to send weekly stats to {domain.organization.name} ({domain.email}): {str(e)}")
                self.stdout.write(self.style.ERROR(f"✗ Failed to send to {domain.organization.name} ({domain.email}): {str(e)}"))

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f"\n📊 Weekly statistics delivery complete!"
                f"\n✓ Successful: {successful_sends}"
                f"\n✗ Failed: {failed_sends}"
                f"\n📧 Total processed: {total_domains}\n"
            )
        )

        logger.info(f"Weekly stats delivery completed. Success: {successful_sends}, Failed: {failed_sends}")