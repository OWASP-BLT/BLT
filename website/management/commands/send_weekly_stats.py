import logging

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

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
        # This follows DonnieBLT's requirement
        domains = Domain.objects.filter(
            organization__isnull=False,  # Must have an organization
            organization__admin__isnull=False,  # Organization must have an owner
            email__isnull=False,  # Must have an email address
        ).exclude(email="")  # Exclude empty email strings

        total_domains = domains.count()
        successful_sends = 0
        failed_sends = 0

        self.stdout.write(self.style.NOTICE(f"Found {total_domains} domains to process"))

        # Process each domain individually
        for domain in domains:
            try:
                # Generate report data for this domain
                open_issues = domain.open_issues
                closed_issues = domain.closed_issues
                total_issues = open_issues.count() + closed_issues.count()
                issues = Issue.objects.filter(domain=domain)

                # Build the email message
                report_data = [
                    "Hey! This is a weekly report from OWASP BLT regarding the bugs reported for your organization!\n\n"
                ]

                report_data.append(
                    f"Organization Name: {domain.name}\n"
                    f"Open issues: {open_issues.count()}\n"
                    f"Closed issues: {closed_issues.count()}\n"
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
                            f"\nDescription: {description}\n" f"Views: {views}\n" f"Labels: {label}\n" f"{'-' * 50}\n"
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
                logger.info(f"Successfully sent weekly stats to {domain.name} ({domain.email})")
                self.stdout.write(self.style.SUCCESS(f"✓ Sent to {domain.name} ({domain.email})"))

            except Exception as e:
                failed_sends += 1
                logger.error(f"Failed to send weekly stats to {domain.name} ({domain.email}): {str(e)}")
                self.stdout.write(self.style.ERROR(f"✗ Failed to send to {domain.name} ({domain.email}): {str(e)}"))

        # Print summary
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
