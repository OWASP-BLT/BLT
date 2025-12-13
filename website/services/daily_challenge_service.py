# Service file: website/services/daily_challenge_service.py

import logging
import random
import re
from datetime import time

import pytz
from django.utils import timezone

from website.models import UserDailyChallenge, UserProfile

logger = logging.getLogger(__name__)

# Constants for challenge validation
MIN_WORD_COUNT_FOR_DETAILED = 200
EARLY_CHECKIN_THRESHOLD_HOUR = 10
CHALLENGE_RESET_HOURS = 24


class DailyChallengeService:
    """Service for handling daily challenge logic and validation."""

    @staticmethod
    def get_active_challenges_for_user(user, challenge_date=None, skip_assignment_check=False):
        """
        Get active challenges for a user on a specific date.
        Also checks if 24 hours have passed and assigns a new challenge if needed.

        Args:
            user: User instance
            challenge_date: Date for which to get challenges (defaults to today)
            skip_assignment_check: If True, skip the assignment check to prevent recursion
        """
        if not user or not user.is_authenticated:
            return UserDailyChallenge.objects.none()

        if challenge_date is None:
            challenge_date = timezone.now().date()

        # Check if user needs a new challenge (24 hours have passed)
        # Skip this check if called from within assignment logic to prevent recursion
        if not skip_assignment_check:
            DailyChallengeService._check_and_assign_new_challenge_if_needed(user)

        return UserDailyChallenge.objects.filter(
            user=user,
            challenge_date=challenge_date,
            status="assigned",
        ).select_related("challenge")

    @staticmethod
    def _check_and_assign_new_challenge_if_needed(user):
        """
        Check if a new challenge should be assigned for today.
        Assigns a new challenge if:
        1. User has no check-ins yet, OR
        2. User's last check-in was on a different date (new day), OR
        3. User's last check-in was more than 24 hours ago

        Args:
            user: User instance (must be authenticated)
        """
        from website.models import DailyStatusReport

        if not user or not user.is_authenticated:
            return

        try:
            now = timezone.now()
            today = now.date()

            # Get the most recent check-in
            last_checkin = DailyStatusReport.objects.filter(user=user).order_by("-created").first()

            if not last_checkin:
                # No check-ins yet, assign first challenge
                DailyChallengeService._assign_random_challenge(user, today)
                return

            # Check if 24-hour cooldown period has passed by checking next_challenge_at
            # Get the most recent challenge with next_challenge_at set
            recent_challenge = (
                UserDailyChallenge.objects.filter(
                    user=user,
                    next_challenge_at__isnull=False,
                )
                .order_by("-next_challenge_at")
                .first()
            )

            if recent_challenge and recent_challenge.next_challenge_at > now:
                # 24-hour cooldown period has not passed yet, don't assign new challenge
                return

            # Check if last check-in was on a different date (new day)
            last_checkin_date = last_checkin.date
            if last_checkin_date < today:
                # Last check-in was on a previous day, assign new challenge for today
                existing_challenge = UserDailyChallenge.objects.filter(
                    user=user,
                    challenge_date=today,
                    status="assigned",
                ).first()

                if not existing_challenge:
                    DailyChallengeService._assign_random_challenge(user, today)
                return

            # If last check-in was today, don't assign new challenge
            # The challenge assignment happens when the check-in is submitted
            if last_checkin_date == today:
                # Already have a check-in for today, don't assign new challenge
                return
        except Exception as e:
            logger.error(
                f"Error checking and assigning new challenge for user {user.username}: {e}",
                exc_info=True,
            )

    @staticmethod
    def _assign_random_challenge(user, challenge_date):
        """
        Assign a random challenge to the user for the given date.
        Uses random.choice() to select from all active challenges.

        Args:
            user: User instance
            challenge_date: Date for which to assign the challenge

        Returns:
            UserDailyChallenge instance or None if no active challenges exist
        """
        from django.db import transaction

        from website.models import DailyChallenge, UserDailyChallenge

        # Get all active challenge types, excluding streak_milestone (not a true daily challenge)
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
        active_challenges = DailyChallenge.objects.filter(is_active=True, challenge_type__in=daily_completable_types)

        if not active_challenges.exists():
            logger.warning(f"No active daily challenges available for user {user.username}")
            return None

        # Randomly select a challenge type from daily-completable challenges
        challenge_list = list(active_challenges)
        if not challenge_list:
            logger.warning(f"Empty challenge list for user {user.username}")
            return None

        selected_challenge = random.choice(challenge_list)

        # Use get_or_create to handle race conditions atomically
        try:
            with transaction.atomic():
                user_challenge, created = UserDailyChallenge.objects.get_or_create(
                    user=user,
                    challenge_date=challenge_date,
                    defaults={
                        "challenge": selected_challenge,
                        "status": "assigned",
                    },
                )

                if not created:
                    # Update existing challenge
                    user_challenge.challenge = selected_challenge
                    user_challenge.status = "assigned"
                    user_challenge.completed_at = None
                    user_challenge.points_awarded = 0
                    user_challenge.next_challenge_at = None
                    user_challenge.save()

                return user_challenge
        except Exception as e:
            logger.error(
                f"Error assigning challenge to user {user.username} for date {challenge_date}: {e}",
                exc_info=True,
            )
            return None

    @staticmethod
    def check_and_complete_challenges(user, daily_status_report):
        """
        Check if any active challenges are completed based on the check-in data
        and mark them as completed.

        Args:
            user: User instance (must be authenticated)
            daily_status_report: DailyStatusReport instance that was just created/updated

        Returns:
            list: List of completed challenge titles
        """
        if not user or not user.is_authenticated:
            return []

        if not daily_status_report:
            logger.warning(
                f"check_and_complete_challenges called with None daily_status_report for user {user.username}",
            )
            return []

        try:
            challenge_date = daily_status_report.date
            if not challenge_date:
                logger.warning(f"daily_status_report has no date for user {user.username}")
                return []

            active_challenges = DailyChallengeService.get_active_challenges_for_user(
                user,
                challenge_date,
                skip_assignment_check=True,  # Prevent recursion
            )

            completed_challenges = []

            for user_challenge in active_challenges:
                if not user_challenge or not user_challenge.challenge:
                    logger.warning(f"Invalid user_challenge found for user {user.username}")
                    continue

                challenge_type = user_challenge.challenge.challenge_type
                is_completed = False

                # Check completion based on challenge type
                try:
                    if challenge_type == "early_checkin":
                        is_completed = DailyChallengeService._check_early_checkin(
                            user,
                            daily_status_report,
                        )
                    elif challenge_type == "positive_mood":
                        is_completed = DailyChallengeService._check_positive_mood(
                            daily_status_report,
                        )
                    elif challenge_type == "complete_all_fields":
                        is_completed = DailyChallengeService._check_complete_all_fields(
                            daily_status_report,
                        )
                    elif challenge_type == "streak_milestone":
                        is_completed = DailyChallengeService._check_streak_milestone(
                            user,
                            daily_status_report,
                        )
                    elif challenge_type == "no_blockers":
                        is_completed = DailyChallengeService._check_no_blockers(
                            daily_status_report,
                        )
                    elif challenge_type == "detailed_reporter":
                        is_completed = DailyChallengeService._check_detailed_reporter(
                            daily_status_report,
                        )
                    elif challenge_type == "goal_achiever":
                        is_completed = DailyChallengeService._check_goal_achiever(
                            daily_status_report,
                        )
                    elif challenge_type == "detailed_planner":
                        is_completed = DailyChallengeService._check_detailed_planner(
                            daily_status_report,
                        )
                    else:
                        logger.warning(
                            f"Unknown challenge type {challenge_type} for user {user.username}",
                        )
                        continue

                    if is_completed:
                        if user_challenge.mark_completed():
                            completed_challenges.append(user_challenge.challenge.title)
                except Exception as e:
                    logger.error(
                        f"Error checking challenge {challenge_type} for user {user.username}: {e}",
                        exc_info=True,
                    )
                    continue

            return completed_challenges
        except Exception as e:
            logger.error(
                f"Error in check_and_complete_challenges for user {user.username}: {e}",
                exc_info=True,
            )
            return []

    @staticmethod
    def _check_early_checkin(user, daily_status_report):
        """
        Check if check-in was submitted before 10 AM in the user's timezone.
        Uses the created timestamp and converts it to the user's timezone.
        """
        if not daily_status_report or not daily_status_report.created:
            return False

        try:
            # Get user's timezone from profile, create profile if it doesn't exist
            # UserProfile uses AutoOneToOneField, but handle edge cases where it might not exist
            # (e.g., legacy users, profile creation failures, or race conditions)
            profile, created = UserProfile.objects.get_or_create(user=user, defaults={"timezone": "UTC"})
            user_tz_str = profile.timezone or "UTC"

            if created:
                logger.info(
                    f"Created UserProfile for user {user.username} with UTC timezone default. "
                    f"User should update their timezone in profile settings for accurate challenge validation."
                )

            # Get timezone object
            try:
                user_tz = pytz.timezone(user_tz_str)
            except pytz.exceptions.UnknownTimeZoneError:
                logger.warning(f"Unknown timezone '{user_tz_str}' for user {user.username}, using UTC")
                user_tz = pytz.UTC

            # Convert check-in time to user's timezone
            checkin_utc = daily_status_report.created
            if timezone.is_naive(checkin_utc):
                checkin_utc = timezone.make_aware(checkin_utc)

            checkin_user_tz = checkin_utc.astimezone(user_tz)
            checkin_time = checkin_user_tz.time()

            # Check if before threshold hour in user's timezone
            early_threshold = time(EARLY_CHECKIN_THRESHOLD_HOUR, 0)
            return checkin_time < early_threshold

        except Exception as e:
            logger.error(
                f"Error checking early check-in for user {user.username}: {e}",
                exc_info=True,
            )
            # Fallback to UTC if timezone conversion fails
            # Log warning that we're using UTC fallback, which may be incorrect for user's timezone
            logger.warning(
                f"Using UTC fallback for early check-in validation for user {user.username}. "
                f"This may cause incorrect challenge validation if user is not in UTC timezone. "
                f"Check-in time will be evaluated against 10:00 AM UTC instead of user's local timezone."
            )
            checkin_utc = daily_status_report.created
            if timezone.is_naive(checkin_utc):
                checkin_utc = timezone.make_aware(checkin_utc)
            checkin_time = checkin_utc.astimezone(pytz.UTC).time()
            early_threshold = time(EARLY_CHECKIN_THRESHOLD_HOUR, 0)
            return checkin_time < early_threshold

    @staticmethod
    def _check_positive_mood(daily_status_report):
        """
        Check if mood is positive (emoji rating 1 or 2).
        Rating 1 = 😊 Happy, Rating 2 = 😄 Smile
        """
        if not daily_status_report or not daily_status_report.current_mood:
            return False

        mood = daily_status_report.current_mood.strip()

        # Check for positive emojis (ratings 1 and 2)
        # The stored value may be "Happy 😊" or just "😊", so check if emoji is in the string
        positive_emojis = ("😊", "😄")  # Happy and Smile
        return any(emoji in mood for emoji in positive_emojis)

    @staticmethod
    def _check_complete_all_fields(daily_status_report):
        """Check if all required fields are filled."""
        if not daily_status_report:
            return False

        # Handle None values safely
        previous_work = daily_status_report.previous_work or ""
        next_plan = daily_status_report.next_plan or ""
        blockers = daily_status_report.blockers or ""
        current_mood = daily_status_report.current_mood or ""

        return (
            bool(previous_work.strip())
            and bool(next_plan.strip())
            and bool(blockers.strip())
            and bool(current_mood.strip())
        )

    @staticmethod
    def _check_streak_milestone(user, daily_status_report):
        """Check if user reached a streak milestone (7, 15, 30 days)."""
        try:
            profile = UserProfile.objects.get(user=user)
            streak = profile.current_streak

            # Check for milestone streaks
            milestone_streaks = [7, 15, 30, 100, 180, 365]
            return streak in milestone_streaks
        except UserProfile.DoesNotExist:
            return False

    @staticmethod
    def _check_no_blockers(daily_status_report):
        """Check if user reported no blockers."""
        if not daily_status_report or not daily_status_report.blockers:
            return False

        blockers = daily_status_report.blockers.strip().lower()

        # Check for exact match with "no blockers" or "no_blockers"
        return blockers in ["no blockers", "no_blockers"]

    @staticmethod
    def _check_detailed_reporter(daily_status_report):
        """
        Check if user wrote at least MIN_WORD_COUNT_FOR_DETAILED words in previous_work field.
        This encourages detailed reporting of work done.
        Uses regex to properly count words (handles punctuation correctly).
        """
        if not daily_status_report or not daily_status_report.previous_work:
            return False

        previous_work = daily_status_report.previous_work.strip()
        # Use regex to count words properly (handles punctuation, multiple spaces, etc.)
        words = re.findall(r"\b\w+\b", previous_work)
        word_count = len(words)
        return word_count >= MIN_WORD_COUNT_FOR_DETAILED

    @staticmethod
    def _check_goal_achiever(daily_status_report):
        """
        Check if user accomplished their goals from yesterday.
        This encourages goal completion and accountability.
        """
        if not daily_status_report:
            return False

        return daily_status_report.goal_accomplished is True

    @staticmethod
    def _check_detailed_planner(daily_status_report):
        """
        Check if user wrote at least MIN_WORD_COUNT_FOR_DETAILED words in next_plan field.
        This encourages detailed planning for upcoming work.
        Uses regex to properly count words (handles punctuation correctly).
        """
        if not daily_status_report or not daily_status_report.next_plan:
            return False

        next_plan = daily_status_report.next_plan.strip()
        # Use regex to count words properly (handles punctuation, multiple spaces, etc.)
        words = re.findall(r"\b\w+\b", next_plan)
        word_count = len(words)
        return word_count >= MIN_WORD_COUNT_FOR_DETAILED
