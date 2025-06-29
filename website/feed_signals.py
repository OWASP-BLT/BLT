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
    ForumPost,
    Hunt,
    IpReport,
    Issue,
    Organization,
    Post,
    TimeLog,
    UserBadge,
    UserProfile,
)
from .utils import analyze_contribution

# Default BACON rewards for different contribution types
DEFAULT_BACON_REWARDS = {
    "Issue": 5,
    "Post": 10,
    "Hunt": 15,
    "IpReport": 3,
    "Organization": 10,
    "ForumPost": 2,
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
    If amt is provided, use that amount directly.
    Otherwise, analyze the contribution using AI to determine the amount.
    Falls back to default rewards if AI analysis fails.
    """
    if user is None or user.is_authenticated is False:
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
                logging.error(f"AI analysis failed for {instance._meta.model_name}: {str(e)}")
                # Fallback to default reward system
                reward_amount = get_default_bacon_reward(instance, action_type)
                logging.info(f"Using default reward amount: {reward_amount} BACON")
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
        logging.error(f"Error in giveBacon: {str(e)}")
        # If anything fails, ensure at least minimum reward is given
        if created:
            token_earning.tokens_earned = 1
        else:
            token_earning.tokens_earned += 1
        token_earning.save()
        return 1


@receiver(post_save)
def handle_post_save(sender, instance, created, **kwargs):
    """Generic handler for post_save signal."""
    if sender == IpReport and created:  # Track first IP report
        assign_first_action_badge(instance.user, "First IP Reported")
        giveBacon(instance.user, instance=instance, action_type="created")
        create_activity(instance, "created")

    elif sender == Post and created:  # Track first blog post
        assign_first_action_badge(instance.author, "First Blog Posted")
        create_activity(instance, "created")
        giveBacon(instance.author, instance=instance, action_type="created")

    elif sender == Issue and created:  # Track first bug report
        assign_first_action_badge(instance.user, "First Bug Reported")
        create_activity(instance, "created")
        giveBacon(instance.user, instance=instance, action_type="created")

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
            assign_first_action_badge(user, "First Bug Bounty")
            create_activity(instance, "created")
            giveBacon(user, instance=instance, action_type="created")

    elif sender == ForumPost and created:  # Track first forum post
        assign_first_action_badge(instance.user, "First Forum Post")
        create_activity(instance, "created")
        giveBacon(instance.user, instance=instance, action_type="created")

    elif sender == Bid and created:  # Track first bid placed
        assign_first_action_badge(instance.user, "First Bid Placed")
        create_activity(instance, "placed")
        giveBacon(instance.user, instance=instance, action_type="placed")

    elif sender is User and created:  # Handle user sign-up
        Activity.objects.create(
            user=instance,
            action_type="signup",
            title=f"New User Signup: {instance.username}",
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.id,
            description=f"Welcome to the community {instance.username}!",
        )


@receiver(pre_delete)
def handle_pre_delete(sender, instance, **kwargs):
    """Generic handler for pre_delete signal."""
    if sender in [Issue, Hunt, IpReport, Post]:
        create_activity(instance, "deleted")


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
        create_activity(instance, "created")
        # Give bacon tokens using AI analysis or fallback to default (10)
        giveBacon(instance.admin, instance=instance, action_type="created")
        # Give first organization badge
        assign_first_action_badge(instance.admin, "First Organization Created")
