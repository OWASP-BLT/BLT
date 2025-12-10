# Service file: website/services/daily_challenge_service.py

import logging
from datetime import time

import pytz
from django.utils import timezone

from website.models import UserDailyChallenge, UserProfile

logger = logging.getLogger(__name__)


class DailyChallengeService:
    """Service for handling daily challenge logic and validation."""

    @staticmethod
    def get_active_challenges_for_user(user, challenge_date=None):
        """
        Get active challenges for a user on a specific date.
        Also checks if 24 hours have passed and assigns a new challenge if needed.
        """
        if not user or not user.is_authenticated:
            return UserDailyChallenge.objects.none()

        if challenge_date is None:
            challenge_date = timezone.now().date()

        # Check if user needs a new challenge (24 hours have passed)
        DailyChallengeService._check_and_assign_new_challenge_if_needed(user)

        return UserDailyChallenge.objects.filter(
            user=user,
            challenge_date=challenge_date,
            status="assigned",
        ).select_related("challenge")

    @staticmethod
    def _check_and_assign_new_challenge_if_needed(user):
        """
        Check if 24 hours have passed since last check-in submission.
        If so, assign a new random challenge.

        Args:
            user: User instance (must be authenticated)
        """
        from datetime import timedelta

        from website.models import DailyStatusReport

        if not user or not user.is_authenticated:
            return

        try:
            now = timezone.now()

            # Get the most recent check-in
            last_checkin = DailyStatusReport.objects.filter(user=user).order_by("-created").first()

            if not last_checkin:
                # No check-ins yet, assign first challenge
                DailyChallengeService._assign_random_challenge(user, now.date())
                return

            # Check if 24 hours have passed since last check-in
            time_since_checkin = now - last_checkin.created
            if time_since_checkin < timedelta(hours=24):
                # Less than 24 hours, don't assign new challenge yet
                return

            # 24 hours have passed, check if user already has a challenge for today
            today = now.date()
            existing_challenge = UserDailyChallenge.objects.filter(
                user=user,
                challenge_date=today,
                status="assigned",
            ).first()

            if not existing_challenge:
                # No challenge for today, assign a new one
                DailyChallengeService._assign_random_challenge(user, today)
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
        import random

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
        active_challenges = DailyChallenge.objects.filter(
            is_active=True, challenge_type__in=daily_completable_types
        )
        
        if not active_challenges.exists():
            logger.warning(f"No active daily challenges available for user {user.username}")
            return None

        # Randomly select a challenge type from daily-completable challenges
        challenge_list = list(active_challenges)
        if not challenge_list:
            logger.warning(f"Empty challenge list for user {user.username}")
            return None

        selected_challenge = random.choice(challenge_list)

        # Check if challenge already exists for this date
        try:
            with transaction.atomic():
                existing = UserDailyChallenge.objects.filter(
                    user=user,
                    challenge_date=challenge_date,
                ).first()

                if existing:
                    # Update existing challenge
                    existing.challenge = selected_challenge
                    existing.status = "assigned"
                    existing.completed_at = None
                    existing.points_awarded = 0
                    existing.next_challenge_at = None
                    existing.save()
                    return existing
                else:
                    # Create new challenge
                    return UserDailyChallenge.objects.create(
                        user=user,
                        challenge=selected_challenge,
                        challenge_date=challenge_date,
                        status="assigned",
                    )
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
            # Get user's timezone from profile, default to UTC
            try:
                profile = UserProfile.objects.get(user=user)
                user_tz_str = profile.timezone or "UTC"
            except UserProfile.DoesNotExist:
                user_tz_str = "UTC"

            # Get timezone object
            try:
                user_tz = pytz.timezone(user_tz_str)
            except pytz.exceptions.UnknownTimeZoneError:
                logger.warning(
                    f"Unknown timezone '{user_tz_str}' for user {user.username}, using UTC"
                )
                user_tz = pytz.UTC

            # Convert check-in time to user's timezone
            checkin_utc = daily_status_report.created
            if timezone.is_naive(checkin_utc):
                checkin_utc = timezone.make_aware(checkin_utc)

            checkin_user_tz = checkin_utc.astimezone(user_tz)
            checkin_time = checkin_user_tz.time()

            # Check if before 10 AM in user's timezone
            early_threshold = time(10, 0)  # 10:00 AM
            return checkin_time < early_threshold

        except Exception as e:
            logger.error(
                f"Error checking early check-in for user {user.username}: {e}",
                exc_info=True,
            )
            # Fallback to UTC if timezone conversion fails
            checkin_time = daily_status_report.created.time()
            early_threshold = time(10, 0)
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
        positive_emojis = ["😊", "😄"]  # Happy and Smile
        return mood in positive_emojis

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
        Check if user wrote at least 200 words in previous_work field.
        This encourages detailed reporting of work done.
        """
        if not daily_status_report or not daily_status_report.previous_work:
            return False

        previous_work = daily_status_report.previous_work.strip()
        word_count = len(previous_work.split())
        return word_count >= 200

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
        Check if user wrote at least 200 words in next_plan field.
        This encourages detailed planning for upcoming work.
        """
        if not daily_status_report or not daily_status_report.next_plan:
            return False

        next_plan = daily_status_report.next_plan.strip()
        word_count = len(next_plan.split())
        return word_count >= 200
