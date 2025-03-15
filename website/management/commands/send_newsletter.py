import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from website.models import Newsletter, NewsletterSubscriber

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send published newsletter to subscribers"

    def add_arguments(self, parser):
        parser.add_argument("--newsletter_id", type=int, help="ID of the specific newsletter to send")
        parser.add_argument("--test", action="store_true", help="Send a test email to the admin")

    def handle(self, *args, **options):
        newsletter_id = options.get("newsletter_id")
        test_mode = options.get("test", False)

        if newsletter_id:
            # Send specific newsletter
            try:
                newsletter = Newsletter.objects.get(id=newsletter_id, status="published")
                self.stdout.write(f"Preparing to send newsletter: {newsletter.title}")
                self.send_newsletter(newsletter, test_mode)
            except Newsletter.DoesNotExist:
                self.stderr.write(f"Newsletter with ID {newsletter_id} does not exist or is not published")
        else:
            # Find newsletters that are published but not sent yet
            newsletters = Newsletter.objects.filter(
                status="published", email_sent=False, published_at__lte=timezone.now()
            )

            self.stdout.write(f"Found {newsletters.count()} newsletters to send")

            for newsletter in newsletters:
                self.send_newsletter(newsletter, test_mode)

    def send_newsletter(self, newsletter, test_mode):
        """Send a specific newsletter to subscribers"""
        if test_mode:
            # Send only to admin email for testing
            self.stdout.write(f"Sending test email for '{newsletter.title}' to admin")
            self.send_to_subscriber(settings.ADMINS[0][1], newsletter, is_test=True)
            return

        # Get active, confirmed subscribers
        subscribers = NewsletterSubscriber.objects.filter(is_active=True, confirmed=True)

        if subscribers.exists():
            self.stdout.write(f"Sending '{newsletter.title}' to {subscribers.count()} subscribers")

            successful_sends = 0
            for subscriber in subscribers:
                try:
                    self.send_to_subscriber(subscriber.email, newsletter, subscriber=subscriber)
                    successful_sends += 1
                except Exception as e:
                    logger.error(f"Failed to send newsletter to {subscriber.email}: {str(e)}")

            # Mark as sent if there were any successful sends
            if successful_sends > 0:
                newsletter.email_sent = True
                newsletter.email_sent_at = timezone.now()
                newsletter.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully sent newsletter '{newsletter.title}' to {successful_sends} subscribers"
                    )
                )
        else:
            self.stdout.write(self.style.WARNING("No active subscribers found"))

    def send_to_subscriber(self, email, newsletter, subscriber=None, is_test=False):
        """Send the newsletter to a specific subscriber"""
        subject = newsletter.email_subject or f"{settings.PROJECT_NAME} Newsletter: {newsletter.title}"

        if is_test:
            subject = f"[TEST] {subject}"

        # Newsletter context
        context = {
            "newsletter": newsletter,
            "subscriber": subscriber,
            "unsubscribe_url": "https://"
            + settings.DOMAIN_NAME
            + reverse("newsletter_unsubscribe", args=[subscriber.confirmation_token])
            if subscriber
            else "#",
            "view_in_browser_url": "https://" + settings.DOMAIN_NAME + newsletter.get_absolute_url(),
            "project_name": settings.PROJECT_NAME,
            "recent_bugs": newsletter.get_recent_bugs(),
            "leaderboard": newsletter.get_leaderboard_updates(),
            "reported_ips": newsletter.get_reported_ips(),
        }

        # Create HTML and plain text versions
        html_content = render_to_string("newsletter/email/newsletter_email.html", context)
        text_content = f"View this newsletter in your browser: {context['view_in_browser_url']}\n\n"
        text_content += newsletter.content

        # Create email message
        email_message = EmailMultiAlternatives(
            subject=subject, body=text_content, from_email=settings.DEFAULT_FROM_EMAIL, to=[email]
        )

        email_message.attach_alternative(html_content, "text/html")
        email_message.send()
