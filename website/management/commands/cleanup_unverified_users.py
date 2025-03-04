import json
import logging
import os
from datetime import timedelta

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

User = get_user_model()
logger = logging.getLogger(__name__)

VERIFICATION_REMINDER_TEMPLATE = """
Hello {{ username }},

This is a reminder that your BLT account is still unverified. You have {{ hours_remaining }} hours remaining to verify your email address before your account is automatically deleted.

Please check your email for the verification link or request a new one by logging in.

If you did not create this account, no action is needed - the account will be removed automatically.

Best regards,
The {{ site_name }} Team
"""


class Command(BaseCommand):
    help = (
        "Handles unverified user accounts cleanup:\n"
        "1. Sends reminder emails after 24 hours\n"
        "2. Deletes accounts unverified after 48 hours\n"
        "3. Only affects new signups with no activity"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Run without making any actual changes",
        )

    def handle(self, *args, **options):
        try:
            now = timezone.now()
            reminder_cutoff = now - timedelta(hours=24)
            delete_cutoff = now - timedelta(hours=48)
            dry_run = options.get("dry_run", False)

            self.stdout.write(self.style.SUCCESS(f"Starting cleanup process (dry-run: {dry_run})"))

            # Send reminders to users who signed up 24-48 hours ago
            reminder_count = self.send_reminders(reminder_cutoff, delete_cutoff, dry_run)
            self.stdout.write(self.style.SUCCESS(f"Reminder emails sent: {reminder_count}"))

            deleted_count = self.delete_unverified(delete_cutoff, dry_run)
            self.stdout.write(self.style.SUCCESS(f"Unverified users deleted: {deleted_count}"))

        except Exception as e:
            logger.error(f"Error in cleanup_unverified_users: {str(e)}")
            self.stderr.write(self.style.ERROR(f"Command failed: {str(e)}"))

    def send_reminders(self, reminder_cutoff, delete_cutoff, dry_run):
        """Send reminder emails to unverified users"""
        reminder_users = User.objects.filter(
            date_joined__lte=reminder_cutoff,
            date_joined__gt=delete_cutoff,
            last_login=None,
            is_staff=False,
            is_superuser=False,
            is_active=True,
        ).exclude(emailaddress__verified=True)

        reminder_count = 0
        for user in reminder_users:
            try:
                if not dry_run:
                    subject = "Reminder: Verify your BLT Account"
                    message = (
                        VERIFICATION_REMINDER_TEMPLATE.replace("{{ username }}", user.username)
                        .replace("{{ hours_remaining }}", "24")
                        .replace("{{ site_name }}", settings.PROJECT_NAME)
                    )
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
                    reminder_count += 1
                    logger.info(f"Sent verification reminder to: {user.username}")
                else:
                    self.stdout.write(self.style.WARNING(f"Would send reminder to: {user.username}"))
            except Exception as e:
                logger.error(f"Failed to send reminder to {user.username}: {str(e)}")

        return reminder_count

    def delete_unverified(self, delete_cutoff, dry_run):
        """Delete unverified users after cutoff period"""
        delete_users = User.objects.filter(
            date_joined__lt=delete_cutoff, last_login=None, is_staff=False, is_superuser=False, is_active=True
        ).exclude(emailaddress__verified=True)

        deleted_count = 0
        for user in delete_users:
            if self.is_safe_to_delete(user):
                try:
                    with transaction.atomic():
                        if not dry_run:
                            # Backup user data before deletion
                            self._backup_user_data(user)
                            username = user.username

                            # Deactivate first instead of immediate deletion
                            user.is_active = False
                            user.save()

                            logger.info(
                                f"Deactivated unverified user: {username} ({email})" f"Joined: {user.date_joined}"
                            )

                            # Actual deletion
                            user.delete()
                            deleted_count += 1
                            logger.info(f"Deleted unverified user: {username}")
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Would delete user: {user.username}" f"(joined: {user.date_joined})"
                                )
                            )
                except Exception as e:
                    logger.error(f"Failed to delete {user.username}: {str(e)}")

        return deleted_count

    @staticmethod
    def _backup_user_data(user):
        """Backup critical user data before deletion"""
        try:
            backup_data = {
                "username": user.username,
                "email": user.email,
                "date_joined": user.date_joined.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
            }

            # Add profile data if exists
            if hasattr(user, "userprofile"):
                backup_data["profile"] = {
                    "github_url": user.userprofile.github_url,
                    "linkedin_url": user.userprofile.linkedin_url,
                    "website_url": user.userprofile.website_url,
                }

                # Use settings configuration
                if not settings.USER_CLEANUP_SETTINGS.get("BACKUP_ENABLED", True):
                    return

                backup_path = settings.USER_CLEANUP_SETTINGS.get(
                    "BACKUP_PATH", os.path.join(settings.MEDIA_ROOT, "user_backups")
                )
                os.makedirs(backup_path, exist_ok=True)

                filename = f"user_{user.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(os.path.join(backup_path, filename), "w") as f:
                    json.dump(backup_data, f, indent=2)

                logger.info(f"Backed up data for user: {user.username}")

        except Exception as e:
            logger.error(f"Failed to backup user data for {user.username}: {str(e)}")

    def is_safe_to_delete(self, user):
        """Check if it's safe to delete the user"""
        try:
            # 1. Critical Role Checks
            if any(
                [
                    user.is_staff,
                    user.is_superuser,
                    user.groups.exists(),
                    hasattr(user, "organizationadmin") and user.organizationadmin.is_active,
                ]
            ):
                logger.info(f"Protected user {user.username} - has critical role")
                return False

            # Verification Status Check
            if EmailAddress.objects.filter(user=user, verified=True).exists():
                logger.info(f"Protected user {user.username} - verified email")
                return False

            # Account Age Check - Don't delete accounts older than 48 hours
            age_threshold = timezone.now() - timedelta(hours=48)
            if user.date_joined < age_threshold:
                logger.info(f"Protected user {user.username} - account too old")
                return False

            # Check for any user activity
            activity_checks = [
                (hasattr(user, "points") and user.points.exists()),
                (hasattr(user, "issue_set") and user.issue_set.exists()),
                (hasattr(user, "userprofile") and user.userprofile.follows.exists()),
                (hasattr(user, "winner") and user.winner.exists()),
                (hasattr(user, "domain_set") and user.domain_set.exists()),
                (hasattr(user, "sent_invites") and user.sent_invites.exists()),
                (hasattr(user, "userprofile") and user.userprofile.team is not None),
                (hasattr(user, "organization_set") and user.organization_set.exists()),
                user.last_login is not None,
            ]

            if any(activity_checks):
                logger.info(f"Protected user {user.username} - has activity")
                return False

            # Check if email is from allowed domains
            if self._is_protected_email_domain(user.email):
                logger.info(f"Protected user {user.username} - protected email domain")
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking delete safety for {user.username}: {str(e)}")
            return False

    @staticmethod
    def _is_protected_email_domain(email):
        """Check if email is from protected domains"""
        try:
            protected_domains = settings.USER_CLEANUP_SETTINGS.get(
                "PROTECTED_EMAIL_DOMAINS", ["owasp.org", settings.DOMAIN_NAME]
            )
            domain = email.split("@")[-1].lower()
            return domain in protected_domains
        except Exception as e:
            logger.error(f"Error checking protected domain: {str(e)}")
            return True
