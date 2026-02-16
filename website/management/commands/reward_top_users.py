import logging
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from website.feed_signals import giveBacon
from website.management.base import LoggedBaseCommand
from website.models import Points, UserProfile

logger = logging.getLogger(__name__)

# Reward tiers: (rank_range, bacon_amount)
REWARD_TIERS = [
    (1, 50),  # 1st place
    (2, 40),  # 2nd place
    (3, 30),  # 3rd place
    (5, 20),  # 4th-5th place
    (10, 10),  # 6th-10th place
]


def get_bacon_reward(rank):
    """Return the BACON reward amount for a given rank."""
    for max_rank, amount in REWARD_TIERS:
        if rank <= max_rank:
            return amount
    return 0


class Command(LoggedBaseCommand):
    help = "Award BACON tokens to the top users based on monthly points leaderboard"

    def add_arguments(self, parser):
        parser.add_argument(
            "--top",
            type=int,
            default=10,
            help="Number of top users to reward (default: 10)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be rewarded without actually awarding",
        )
        parser.add_argument(
            "--period",
            type=str,
            default="month",
            choices=["week", "month"],
            help="Time period for the leaderboard (default: month)",
        )

    def handle(self, *args, **options):
        top_n = options["top"]
        dry_run = options["dry_run"]
        period = options["period"]

        now = timezone.now()
        if period == "month":
            # Default to previous month so a monthly cron on the 1st rewards last month
            first_of_current = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_of_prev = first_of_current - timedelta(days=1)
            start_date = last_of_prev.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = first_of_current
            period_label = last_of_prev.strftime("%B %Y")
        else:
            start_date = now - timedelta(days=7)
            end_date = now
            period_label = f"week of {start_date.strftime('%b %d')} - {now.strftime('%b %d, %Y')}"

        self.stdout.write(f"Calculating top {top_n} users for {period_label}...")

        # Get top users by total points earned in the period
        top_users = (
            Points.objects.filter(created__gte=start_date, created__lt=end_date)
            .values("user__id", "user__username")
            .annotate(total_points=Sum("score"))
            .order_by("-total_points")[:top_n]
        )

        if not top_users:
            self.stdout.write(self.style.WARNING("No users found with points in this period."))
            return

        total_bacon_awarded = 0
        rewarded_count = 0

        for rank, user_data in enumerate(top_users, start=1):
            username = user_data["user__username"]
            total_points = user_data["total_points"]
            bacon_amount = get_bacon_reward(rank)

            if bacon_amount <= 0:
                continue

            if dry_run:
                self.stdout.write(f"  [DRY RUN] #{rank} {username}: {total_points} points -> {bacon_amount} BACON")
                total_bacon_awarded += bacon_amount
                rewarded_count += 1
            else:
                try:
                    user_profile = UserProfile.objects.get(user__id=user_data["user__id"])
                    giveBacon(user_profile.user, amt=bacon_amount)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  #{rank} {username}: {total_points} points -> {bacon_amount} BACON awarded"
                        )
                    )
                    rewarded_count += 1
                    total_bacon_awarded += bacon_amount
                except UserProfile.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"  #{rank} {username}: UserProfile not found, skipping"))
                    continue
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  #{rank} {username}: Error awarding BACON - {e}"))
                    continue

        action = "Would award" if dry_run else "Awarded"
        self.stdout.write(
            self.style.SUCCESS(f"\n{action} {total_bacon_awarded} BACON to {rewarded_count} users for {period_label}")
        )
