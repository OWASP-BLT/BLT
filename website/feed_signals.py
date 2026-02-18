import logging

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import (
    Activity,
    BaconEarning,
    Badge,
    Bid,
    Hunt,
    IpReport,
    Issue,
    Organization,
    TimeLog,
    UserBadge,
    UserProfile,
)
from .utils import analyze_contribution

logger = logging.getLogger(__name__)

# Default BACON rewards for different contribution types
DEFAULT_BACON_REWARDS = {
    "Issue": 5,
    "Hunt": 15,
    "IpReport": 3,
    "Organization": 10,
    "Bid": 2,
}


def get_default_bacon_reward(instance, action_type):
    """Get the default BACON reward for a given instance type"""
    model_name = instance._meta.model_name.capitalize()
    base_reward = DEFAULT_BACON_REWARDS.get(model_name, 1)

    # Add bonus for security-related content if applicable
    if hasattr(instance, "is_security") and getattr(instance, "is_security", False):
        base_reward += 3

    return base_reward


def get_default_user():
    """Get or create a default 'anonymous' user."""
    return User.objects.get_or_create(username="anonymous")[0]


# Helper function to assign the badge based on action
def assign_first_action_badge(user, action_title):
    """Assign badges for first-time actions."""
    if user is not None and user.is_authenticated:
        badge, created = Badge.objects.get_or_create(title=action_title, type="automatic")

        if not UserBadge.objects.filter(user=user, badge=badge).exists():
            UserBadge.objects.get_or_create(user=user, badge=badge)


def create_activity(instance, action_type):
    """Generic function to create an activity for a given model instance."""
    model_name = instance._meta.model_name
    user_field = (
        getattr(instance, "user", None) or getattr(instance, "author", None) or getattr(instance, "modified_by", None)
    )
    user = user_field or get_default_user()

    # Get the content type of the instance
    content_type = ContentType.objects.get_for_model(instance)

    # Get instance name or title
    name = getattr(instance, "name", getattr(instance, "title", ""))[:50]
    title = f"{model_name.capitalize()} {action_type.capitalize()} {name}"
    description = getattr(instance, "description", None)
    # Create the activity
    Activity.objects.create(
        user=user,
        action_type=action_type,
        title=title,
        content_type=content_type,
        object_id=instance.id,  # Use object_id for GenericForeignKey
        description=description[:100] if description else "",
        image=getattr(instance, "screenshot", getattr(instance, "image", None)),
    )


def giveBacon(user, instance=None, action_type=None, amt=None):
    """
    Award BACON tokens to a user based on their contribution.

    Args:
        user: User object to award tokens to
        instance: Optional model instance for AI analysis
        action_type: Optional action type for AI analysis
        amt: Optional fixed amount to award (bypasses AI analysis)

    Returns:
        int: Amount of BACON tokens awarded

    Security:
        - Validates user exists and has ID
        - Ensures reward amount is within valid range (1-50)
        - Handles errors gracefully
    """
    if user is None:
        return

    # Security: Validate user has been saved to database
    if not user.id:
        logger.warning("giveBacon: User has no ID yet, skipping reward")
        return

    token_earning, created = BaconEarning.objects.get_or_create(user=user)

    try:
        # If amount is specified, use it
        if amt is not None:
            reward_amount = amt
        # Otherwise analyze the contribution if we have an instance
        elif instance is not None and action_type is not None:
            try:
                reward_amount = analyze_contribution(instance, action_type)
            except Exception as e:
                # Fallback to default reward system
                reward_amount = get_default_bacon_reward(instance, action_type)
        else:
            reward_amount = 1  # Default minimum reward

        # Ensure reward amount is within valid range (1-50)
        reward_amount = max(1, min(50, int(reward_amount)))

        if created:
            token_earning.tokens_earned = reward_amount
        else:
            token_earning.tokens_earned += reward_amount

        token_earning.save()
        return reward_amount

    except Exception as e:
        # If anything fails, ensure at least minimum reward is given
        if created:
            token_earning.tokens_earned = 1
        else:
            token_earning.tokens_earned += 1
        token_earning.save()
        return 1


def _safe_assign_badge(user, badge_name):
    """Safely assign a badge to a user, logging any errors."""
    try:
        assign_first_action_badge(user, badge_name)
    except Exception as e:
        logger.warning(f"Failed to assign badge '{badge_name}' to user: {str(e)}", exc_info=True)


def _safe_create_activity(instance, action_type):
    """Safely create an activity, logging any errors."""
    try:
        create_activity(instance, action_type)
    except Exception as e:
        logger.warning(
            f"Failed to create activity for {instance._meta.model_name}: {str(e)}",
            exc_info=True,
        )


def _safe_give_bacon(user, instance=None, action_type=None):
    """Safely award Bacon, logging any errors."""
    try:
        giveBacon(user, instance=instance, action_type=action_type)
    except Exception as e:
        logger.warning(f"Failed to give Bacon to user: {str(e)}", exc_info=True)


@receiver(post_save)
def handle_post_save(sender, instance, created, **kwargs):
    """Generic handler for post_save signal."""
    try:
        if sender == IpReport and created:  # Track first IP report
            _safe_assign_badge(instance.user, "First IP Reported")
            _safe_give_bacon(instance.user, instance=instance, action_type="created")
            _safe_create_activity(instance, "created")

        elif sender == Issue and created:  # Track first bug report
            _safe_assign_badge(instance.user, "First Bug Reported")
            _safe_create_activity(instance, "created")
            _safe_give_bacon(instance.user, instance=instance, action_type="created")

        elif sender == Hunt and created:  # Track first bug bounty
            # Attempt to get the user from Domain managers or Organization
            user = None
            if instance.domain:
                # Try managers of the domain
                user = instance.domain.managers.first()
                # Optionally, if Organization has a user, fetch it here
                if not user and instance.domain.organization:
                    user = getattr(instance.domain.organization, "user", None)

            # Assign badge and activity if a user is found
            if user:
                _safe_assign_badge(user, "First Bug Bounty")
                _safe_create_activity(instance, "created")
                _safe_give_bacon(user, instance=instance, action_type="created")

        elif sender == Bid and created:  # Track first bid placed
            _safe_assign_badge(instance.user, "First Bid Placed")
            _safe_create_activity(instance, "placed")
            _safe_give_bacon(instance.user, instance=instance, action_type="placed")

        elif sender is User and created:  # Handle user sign-up
            try:
                Activity.objects.create(
                    user=instance,
                    action_type="signup",
                    title=f"New User Signup: {instance.username}",
                    content_type=ContentType.objects.get_for_model(instance),
                    object_id=instance.id,
                    description=f"Welcome to the community {instance.username}!",
                )
            except Exception as e:
                logger.warning(
                    f"Failed to create signup activity for User {instance.username}: {str(e)}",
                    exc_info=True,
                )
    except Exception as e:
        logger.error(f"Unexpected error in handle_post_save signal: {str(e)}", exc_info=True)


@receiver(pre_delete)
def handle_pre_delete(sender, instance, **kwargs):
    """Generic handler for pre_delete signal."""
    if sender in [Issue, Hunt, IpReport]:
        _safe_create_activity(instance, "deleted")


@receiver(post_save, sender=TimeLog)
def update_user_streak(sender, instance, created, **kwargs):
    """
    Automatically update user's streak when a TimeLog is created
    """
    if created and instance.user and instance.user.is_authenticated:
        check_in_date = instance.start_time.date()
        try:
            user_profile = instance.user.userprofile
            user_profile.update_streak_and_award_points(check_in_date)
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(
                user=instance.user, current_streak=1, longest_streak=1, last_check_in=check_in_date
            )


@receiver(post_save, sender=Organization)
def handle_organization_creation(sender, instance, created, **kwargs):
    """Give bacon to user when they create an organization"""
    if created and instance.admin:
        # Create an activity first so it's included in the AI analysis
        _safe_create_activity(instance, "created")
        # Give bacon tokens using AI analysis or fallback to default (10)
        _safe_give_bacon(instance.admin, instance=instance, action_type="created")
        # Give first organization badge
        _safe_assign_badge(instance.admin, "First Organization Created")
