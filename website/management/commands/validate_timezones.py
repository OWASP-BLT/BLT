# Management command: website/management/commands/validate_timezones.py

import logging

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from website.models import ReminderSettings, UserProfile, validate_iana_timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Validate and optionally fix timezone values in UserProfile and ReminderSettings models"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Fix invalid timezones by setting them to UTC (default: only report issues)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without making any changes",
        )

    def handle(self, *args, **options):
        fix = options["fix"]
        dry_run = options["dry_run"]

        if fix and dry_run:
            self.stdout.write(self.style.WARNING("Cannot use --fix and --dry-run together. Using --dry-run mode."))
            fix = False

        self.stdout.write(self.style.SUCCESS("Validating timezone values..."))
        self.stdout.write("")

        # Validate UserProfile timezones
        self.stdout.write(self.style.HTTP_INFO("Checking UserProfile records..."))
        user_profiles = UserProfile.objects.all()
        invalid_user_profiles = []
        valid_count = 0

        for profile in user_profiles:
            try:
                validate_iana_timezone(profile.timezone)
                valid_count += 1
            except ValidationError as e:
                invalid_user_profiles.append((profile, profile.timezone, str(e)))

        self.stdout.write(f"  Valid timezones: {valid_count}")
        self.stdout.write(f"  Invalid timezones: {len(invalid_user_profiles)}")

        if invalid_user_profiles:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Invalid UserProfile timezones:"))
            for profile, tz_value, error in invalid_user_profiles:
                self.stdout.write(
                    f"  User: {profile.user.username} (ID: {profile.id}), Timezone: '{tz_value}', Error: {error}"
                )

        # Validate ReminderSettings timezones
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("Checking ReminderSettings records..."))
        reminder_settings = ReminderSettings.objects.all()
        invalid_reminders = []
        valid_reminder_count = 0

        for reminder in reminder_settings:
            try:
                validate_iana_timezone(reminder.timezone)
                valid_reminder_count += 1
            except ValidationError as e:
                invalid_reminders.append((reminder, reminder.timezone, str(e)))

        self.stdout.write(f"  Valid timezones: {valid_reminder_count}")
        self.stdout.write(f"  Invalid timezones: {len(invalid_reminders)}")

        if invalid_reminders:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Invalid ReminderSettings timezones:"))
            for reminder, tz_value, error in invalid_reminders:
                self.stdout.write(
                    f"  User: {reminder.user.username} (ID: {reminder.id}), Timezone: '{tz_value}', Error: {error}"
                )

        # Summary
        total_invalid = len(invalid_user_profiles) + len(invalid_reminders)
        self.stdout.write("")
        if total_invalid == 0:
            self.stdout.write(self.style.SUCCESS("✓ All timezones are valid!"))
        else:
            self.stdout.write(self.style.WARNING(f"Found {total_invalid} invalid timezone(s)"))

        # Fix invalid timezones if requested
        if fix and total_invalid > 0:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("Fixing invalid timezones..."))

            fixed_count = 0
            for profile, tz_value, error in invalid_user_profiles:
                self.stdout.write(f"  Fixing UserProfile for {profile.user.username}: '{tz_value}' -> 'UTC'")
                profile.timezone = "UTC"
                profile.save(update_fields=["timezone"])
                fixed_count += 1

            for reminder, tz_value, error in invalid_reminders:
                self.stdout.write(f"  Fixing ReminderSettings for {reminder.user.username}: '{tz_value}' -> 'UTC'")
                reminder.timezone = "UTC"
                reminder.save(update_fields=["timezone"])
                fixed_count += 1

            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(f"✓ Fixed {fixed_count} invalid timezone(s)"))
        elif dry_run and total_invalid > 0:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Dry run mode: No changes made. Use --fix to apply changes."))
