import logging
import os
import random
import time
from datetime import time as dt_time

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from sizzle.management.base import SizzleBaseCommand
from sizzle.utils.model_loader import get_reminder_settings_model, get_userprofile_model
from sizzle.conf import SIZZLE_EMAIL_REMINDERS_ENABLED

logger = logging.getLogger(__name__)


class Command(SizzleBaseCommand):
    help = "Sends daily check-in reminders to users who haven't checked in today"

    def setup_logging(self):
        logs_dir = os.path.join(settings.BASE_DIR, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, "reminder_emails.log")
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return handler

    def handle(self, *args, **options):
        # Check if email reminders are enabled
        if not SIZZLE_EMAIL_REMINDERS_ENABLED:
            self.log_warning('Email reminders are disabled in settings')
            return

        # Get models dynamically
        ReminderSettings = get_reminder_settings_model()
        if ReminderSettings is None:
            self.log_error('ReminderSettings model not available. Ensure sizzle migrations are run.')
            return

        UserProfile = get_userprofile_model()
        if UserProfile is None:
            self.log_warning(
                'UserProfile model not configured. Check-in status verification will be skipped. '
                'Check SIZZLE_USERPROFILE_MODEL setting.'
            )

        handler = self.setup_logging()
        try:
            now = timezone.now()
            logger.info(f"Starting reminder process at {now} (UTC)")

            # Calculate the current 15-minute window in UTC
            current_hour = now.hour
            current_minute = now.minute
            window_start_minute = (current_minute // 15) * 15
            window_end_minute = window_start_minute + 15

            # Handle minute overflow
            window_end_hour = current_hour
            if window_end_minute >= 60:
                window_end_minute = window_end_minute - 60
                window_end_hour = current_hour + 1
                if window_end_hour >= 24:
                    window_end_hour = 0

            # Convert to time objects for database filtering
            window_start_time = dt_time(hour=current_hour, minute=window_start_minute)
            window_end_time = dt_time(hour=window_end_hour, minute=window_end_minute)

            logger.info(f"Current UTC time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(
                f"Processing reminders for UTC time window: {window_start_time.strftime('%H:%M')} - {window_end_time.strftime('%H:%M')}"
            )
            logger.info(f"Time window in minutes: {window_start_minute} - {window_end_minute}")

            # Get active reminder settings within the current UTC time window
            # Exclude users who already received a reminder today
            active_settings = ReminderSettings.objects.filter(
                is_active=True, reminder_time_utc__gte=window_start_time, reminder_time_utc__lt=window_end_time
            ).exclude(last_reminder_sent__date=now.date())

            logger.info(f"Found {active_settings.count()} users with reminders in current UTC time window")

            # Prefetch user profiles if UserProfile model is available
            user_ids = [rs.user_id for rs in active_settings]
            profile_map = {}
            if UserProfile:
                try:
                    profile_map = {profile.user_id: profile for profile in UserProfile.objects.filter(user_id__in=user_ids)}
                except Exception as e:
                    logger.warning(f"Could not fetch user profiles: {e}")

            reminders_to_send = []

            for reminder_settings in active_settings:
                try:
                    # Check if user has checked in today using prefetched profiles (if available)
                    if UserProfile and profile_map:
                        profile = profile_map.get(reminder_settings.user_id)
                        if profile and hasattr(profile, 'last_check_in') and profile.last_check_in and profile.last_check_in == now.date():
                            continue

                    reminders_to_send.append((reminder_settings, profile_map.get(reminder_settings.user_id) if profile_map else None))
                    logger.info(
                        f"User {reminder_settings.user.username} added to reminder list for time {reminder_settings.reminder_time} ({reminder_settings.timezone})"
                    )

                except Exception as e:
                    logger.error(f"Error processing user {reminder_settings.user.username}: {str(e)}")
                    continue

            if not reminders_to_send:
                logger.info("No users need reminders at this time")
                return

            # Process reminders individually for personalization
            successful_count = 0
            failed_count = 0
            total_users = len(reminders_to_send)

            for i, (reminder_settings, profile) in enumerate(reminders_to_send, 1):
                try:
                    # Add small delay between emails to avoid overwhelming the server
                    if i > 1:
                        # Small delay between each email
                        delay = random.uniform(0.1, 0.3)
                        time.sleep(delay)
                        # Larger delay every 10 emails
                        if i % 10 == 0:
                            extra_delay = random.uniform(1, 2)
                            logger.info(f"Processed {i} emails, waiting {extra_delay:.2f} seconds")
                            time.sleep(extra_delay)

                    user = reminder_settings.user

                    # Get organization info
                    org_name = ""
                    org_info_html = ""
                    if profile and hasattr(profile, 'team') and profile.team:
                        org_name = profile.team.name
                        org_info_html = f"""
                            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin: 20px 0; border-left: 4px solid #e74c3c;">
                                <p style="margin: 0; color: #666; font-size: 14px;"><strong>Organization:</strong> {org_name}</p>
                            </div>
                        """

                    # Format reminder time in user's timezone
                    reminder_time_str = reminder_settings.reminder_time.strftime("%I:%M %p")
                    timezone_str = reminder_settings.timezone

                    # Create email message
                    plain_body = f"""Hello {user.username},

This is your daily check-in reminder{f" for {org_name}" if org_name else ""}.

Reminder Time: {reminder_time_str} ({timezone_str})

Click here to check in: https://{settings.PRODUCTION_DOMAIN}/add-sizzle-checkin/

You can manage your reminder settings at: https://{settings.PRODUCTION_DOMAIN}/reminder-settings/

Regular check-ins help keep your team informed about your progress and any challenges you might be facing.

Thank you for keeping your team updated!

Best regards,
The BLT Team"""

                    email = EmailMultiAlternatives(
                        subject="Daily Check-in Reminder",
                        body=plain_body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[user.email],
                    )

                    # Add HTML content
                    html_content = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; color: #333;">
                        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
                            <h2 style="color: #333; margin-bottom: 20px;">Daily Check-in Reminder</h2>
                            <p>Hello <strong>{user.username}</strong>,</p>
                            <p>It's time for your daily check-in{f" for <strong>{org_name}</strong>" if org_name else ""}! Please log in to update your status.</p>
                            {org_info_html}
                            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin: 20px 0;">
                                <p style="margin: 0; color: #666; font-size: 14px;"><strong>Your Reminder Time:</strong> {reminder_time_str} ({timezone_str})</p>
                            </div>
                            <div style="margin: 30px 0; text-align: center;">
                                <a href="https://{settings.PRODUCTION_DOMAIN}/add-sizzle-checkin/" 
                                   style="display: inline-block; background-color: #e74c3c; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold; text-align: center; min-width: 200px;">
                                   Check In Now
                                </a>
                            </div>
                            <p>Regular check-ins help keep your team informed about your progress and any challenges you might be facing.</p>
                            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; text-align: center;">
                                <p style="font-size: 13px; color: #666;">
                                    <a href="https://{settings.PRODUCTION_DOMAIN}/reminder-settings/" style="color: #e74c3c; text-decoration: none;">Manage your reminder settings</a>
                                </p>
                            </div>
                            <p style="margin-top: 20px;">Thank you for keeping your team updated!</p>
                            <p style="color: #666; font-size: 14px;">Best regards,<br>The BLT Team</p>
                        </div>
                    </body>
                    </html>
                    """
                    email.attach_alternative(html_content, "text/html")

                    # Send email
                    email.send()

                    # Update last_reminder_sent
                    reminder_settings.last_reminder_sent = now
                    reminder_settings.save(update_fields=["last_reminder_sent"])

                    successful_count += 1
                    logger.info(f"Successfully sent reminder to {user.username} ({user.email})")

                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error sending reminder to {reminder_settings.user.username}: {str(e)}")

            # Log summary
            logger.info(
                f"""
            Reminder Summary:
            - Total users processed: {total_users}
            - Successfully sent: {successful_count}
            - Failed: {failed_count}
            """
            )

            return f"Processed {total_users} users, {successful_count} sent successfully, {failed_count} failed"
        except Exception as e:
            logger.error(f"Critical error in reminder process: {str(e)}")
            raise
        finally:
            logger.removeHandler(handler)
            handler.close()