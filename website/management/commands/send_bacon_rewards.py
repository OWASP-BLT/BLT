"""
Management command to send bacon coin rewards to top users.

This command identifies the top users based on their contributions and awards them
bacon tokens. It integrates with the existing BaconEarning model to allocate rewards.

Usage:
    python manage.py send_bacon_rewards --top N --reward AMOUNT
    python manage.py send_bacon_rewards --dry-run
"""

import logging
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils import timezone

from website.models import BaconEarning, Points

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send bacon coin rewards to top users based on their contributions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--top",
            type=int,
            default=10,
            help="Number of top users to reward (default: 10)",
        )
        parser.add_argument(
            "--reward",
            type=float,
            default=50.0,
            help="Bacon token reward amount for the top user, decreasing for lower ranks (default: 50.0)",
        )
        parser.add_argument(
            "--period",
            type=str,
            choices=["all", "month", "week"],
            default="month",
            help="Time period to consider for top users (default: month)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without actually awarding tokens",
        )

    def handle(self, *args, **options):
        top_count = options["top"]
        base_reward = Decimal(str(options["reward"]))
        period = options["period"]
        dry_run = options["dry_run"]

        self.stdout.write(self.style.SUCCESS(f"Starting bacon rewards process at {timezone.now()}"))
        self.stdout.write(f"Configuration: Top {top_count} users, Base reward: {base_reward} BACON, Period: {period}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No tokens will be awarded"))

        try:
            # Get top users based on points for the specified period
            top_users = self.get_top_users(top_count, period)

            if not top_users:
                self.stdout.write(self.style.WARNING("No eligible users found for rewards"))
                return

            # Award tokens to top users
            total_awarded = Decimal("0.00")
            for rank, user_data in enumerate(top_users, start=1):
                user = user_data["user"]
                score = user_data["score"]

                # Calculate reward: decreasing by rank (e.g., 50, 45, 40, 35, 30, 25, 20, 15, 10, 5)
                reward_amount = base_reward - (Decimal(str(rank - 1)) * (base_reward / Decimal(str(top_count))))
                reward_amount = max(Decimal("5.00"), reward_amount)  # Minimum 5 BACON

                if not dry_run:
                    # Get or create BaconEarning for the user
                    bacon_earning, created = BaconEarning.objects.get_or_create(
                        user=user,
                        defaults={"tokens_earned": Decimal("0.00")},
                    )
                    
                    # Add reward to existing tokens
                    bacon_earning.tokens_earned += reward_amount
                    bacon_earning.save()

                    logger.info(
                        f"Awarded {reward_amount} BACON to {user.username} (Rank: {rank}, Score: {score})"
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"#{rank} {user.username} - Score: {score} - Reward: {reward_amount} BACON"
                    )
                )
                total_awarded += reward_amount

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"\nDRY RUN: Would award {total_awarded} BACON tokens to {len(top_users)} users")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"\nSuccessfully awarded {total_awarded} BACON tokens to {len(top_users)} users")
                )
                logger.info(f"Bacon rewards completed: {total_awarded} BACON awarded to {len(top_users)} users")

        except Exception as e:
            error_msg = f"Error sending bacon rewards: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.stdout.write(self.style.ERROR(error_msg))
            raise

    def get_top_users(self, count, period):
        """
        Get top users based on their points for the specified period.

        Args:
            count: Number of top users to retrieve
            period: Time period ('all', 'month', 'week')

        Returns:
            List of dicts with user and score information
        """
        # Start with all users who have points
        queryset = User.objects.filter(points__score__gt=0)

        # Filter by time period
        now = timezone.now()
        if period == "month":
            queryset = queryset.filter(points__created__year=now.year, points__created__month=now.month)
        elif period == "week":
            week_ago = now - timezone.timedelta(days=7)
            queryset = queryset.filter(points__created__gte=week_ago)
        # 'all' period means no additional filtering

        # Aggregate points and order by total score
        top_users = (
            queryset.annotate(total_score=Sum("points__score"))
            .filter(total_score__gt=0, username__isnull=False)
            .exclude(username="")
            .order_by("-total_score")[:count]
        )

        # Convert to list of dicts for easier handling
        result = []
        for user in top_users:
            result.append({
                "user": user,
                "score": user.total_score,
            })

        return result
