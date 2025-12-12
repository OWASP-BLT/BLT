# Management command: website/management/commands/generate_daily_challenges.py

import logging
import random
from datetime import date

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from website.models import DailyChallenge, UserDailyChallenge

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate daily challenges for all active users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="Date to generate challenges for (YYYY-MM-DD). Defaults to today.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force regeneration even if challenges already exist for the date",
        )

    def handle(self, *args, **options):
        # Get target date
        if options["date"]:
            try:
                target_date = date.fromisoformat(options["date"])
            except ValueError:
                self.stdout.write(
                    self.style.ERROR(
                        f"Invalid date format: {options['date']}. Use YYYY-MM-DD.",
                    ),
                )
                return
        else:
            target_date = timezone.now().date()

        # Get active challenge types, excluding streak_milestone
        # Streak milestones should be handled separately as they only complete on specific days
        # Only include challenges that can be completed on any day
        daily_completable_types = [
            "early_checkin",
            "positive_mood",
            "complete_all_fields",
            "no_blockers",
            "detailed_reporter",
            "goal_achiever",
            "detailed_planner",
        ]
        challenge_list = list(DailyChallenge.objects.filter(is_active=True, challenge_type__in=daily_completable_types))
        if not challenge_list:
            self.stdout.write(
                self.style.WARNING(
                    "No active daily-completable challenge types found. Create challenge types in admin first.",
                ),
            )
            return

        # Get all active users
        users_list = list(User.objects.filter(is_active=True))
        if not users_list:
            self.stdout.write(self.style.WARNING("No active users found."))
            return
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0

        for user in users_list:
            # Check if challenge already exists
            existing = UserDailyChallenge.objects.filter(
                user=user,
                challenge_date=target_date,
            ).first()

            if existing and not options["force"]:
                skipped_count += 1
                continue

            # Randomly select a challenge type for this user
            selected_challenge = random.choice(challenge_list)

            try:
                with transaction.atomic():
                    if existing:
                        # Update existing challenge
                        existing.challenge = selected_challenge
                        existing.status = "assigned"
                        existing.completed_at = None
                        existing.points_awarded = 0
                        existing.save()
                        updated_count += 1
                    else:
                        # Create new challenge
                        UserDailyChallenge.objects.create(
                            user=user,
                            challenge=selected_challenge,
                            challenge_date=target_date,
                            status="assigned",
                        )
                        created_count += 1
            except Exception as e:
                error_count += 1
                logger.error(
                    f"Error creating challenge for user {user.username}: {e}",
                )
                self.stdout.write(
                    self.style.ERROR(
                        f"Error for user {user.username}: {str(e)}",
                    ),
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {created_count} challenges, "
                f"updated {updated_count} challenges. "
                f"Skipped: {skipped_count}, Errors: {error_count}",
            ),
        )
