import logging
import random
import time
from itertools import islice

import pytz
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import ReminderSettings, UserProfile

logger = logging.getLogger("reminder_emails")
handler = logging.FileHandler("logs/reminder_emails.log")
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def batch(iterable, size):
    """Helper function to create batches from an iterable"""
    iterator = iter(iterable)
    return iter(lambda: list(islice(iterator, size)), [])


class Command(BaseCommand):
    help = "Sends daily check-in reminders to users who haven't checked in today"

    def handle(self, *args, **options):
        now = timezone.now()
        logger.info(f"Starting reminder process at {now}")

        # Get all active reminder settings
        # Exclude users who already received a reminder today
        active_settings = ReminderSettings.objects.filter(is_active=True).exclude(last_reminder_sent__date=now.date())
        users_needing_reminders = []

        for reminder_settings in active_settings:
            try:
                # Convert reminder time to user's timezone
                user_tz = pytz.timezone(reminder_settings.timezone)
                user_now = now.astimezone(user_tz)
                reminder_time = reminder_settings.reminder_time

                # Check if current time matches reminder time (within 5 minutes)
                time_diff = abs(
                    (user_now.hour * 60 + user_now.minute) - (reminder_time.hour * 60 + reminder_time.minute)
                )

                if time_diff <= 5:  # 5-minute window
                    # Check if user has checked in today
                    try:
                        profile = UserProfile.objects.get(user=reminder_settings.user)
                        last_checkin = profile.last_check_in
                        if last_checkin:
                            # Check if user has checked in today
                            if last_checkin == user_now.date():
                                continue
                    except UserProfile.DoesNotExist:
                        pass

                    users_needing_reminders.append(reminder_settings.user)

            except Exception as e:
                logger.error(f"Error processing user {reminder_settings.user.username}: {str(e)}")
                continue

        if not users_needing_reminders:
            logger.info("No users need reminders at this time")
            return

        # Process users in batches of 50
        batch_size = 50
        successful_batches = 0
        failed_batches = 0
        total_users = len(users_needing_reminders)

        for i, user_batch in enumerate(batch(users_needing_reminders, batch_size), 1):
            try:
                # Add random delay between batches (1-5 seconds)
                if i > 1:
                    time.sleep(random.uniform(1, 5))

                # Create email message
                email = EmailMessage(
                    subject="Daily Check-in Reminder",
                    body="It's time for your daily check-in! Please log in to update your status.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[settings.DEFAULT_FROM_EMAIL],  # Send to a single recipient
                    bcc=[user.email for user in user_batch],  # BCC all users in batch
                )

                # Send email
                email.send()

                # Update last_reminder_sent for successful batch
                ReminderSettings.objects.filter(user_id__in=[user.id for user in user_batch]).update(
                    last_reminder_sent=now
                )

                successful_batches += 1
                logger.info(f"Successfully sent batch {i} to {len(user_batch)} users")

            except Exception as e:
                failed_batches += 1
                logger.error(f"Error sending batch {i}: {str(e)}")

        # Log summary
        logger.info(
            f"""
        Reminder Summary:
        - Total users processed: {total_users}
        - Successful batches: {successful_batches}
        - Failed batches: {failed_batches}
        - Batch size: {batch_size}
        """
        )
