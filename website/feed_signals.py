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
    Post,
    TimeLog,
    UserBadge,
    Organization,
    UserProfile,
)


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

    # Create the activity
    Activity.objects.create(
        user=user,
        action_type=action_type,
        title=title,
        content_type=content_type,
        object_id=instance.id,  # Use object_id for GenericForeignKey
        description=getattr(instance, "description", getattr(instance, "content", ""))[:100],
        image=getattr(instance, "screenshot", getattr(instance, "image", None)),
    )


def giveBacon(user, amt=1):
    # Check if the user already has a token record
    if user is None or user.is_authenticated is False:
        return
    token_earning, created = BaconEarning.objects.get_or_create(user=user)

    if created:
        token_earning.tokens_earned = amt  # Reward 10 tokens for completing the action (adjust as needed)
    else:
        token_earning.tokens_earned += amt  # Add 10 tokens if the user already exists in the system

    token_earning.save()  # Save the updated record


@receiver(post_save)
def handle_post_save(sender, instance, created, **kwargs):
    """Generic handler for post_save signal."""
    if sender == IpReport and created:  # Track first IP report
        assign_first_action_badge(instance.user, "First IP Reported")
        giveBacon(instance.user)
        create_activity(instance, "created")

    elif sender == Post and created:  # Track first blog post
        assign_first_action_badge(instance.author, "First Blog Posted")
        create_activity(instance, "created")

    elif sender == Issue and created:  # Track first bug report
        assign_first_action_badge(instance.user, "First Bug Reported")
        create_activity(instance, "created")

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

    elif sender == ForumPost and created:  # Track first forum post
        assign_first_action_badge(instance.user, "First Forum Post")
        create_activity(instance, "created")

    elif sender == Bid and created:  # Track first bid placed
        assign_first_action_badge(instance.user, "First Bid Placed")
        create_activity(instance, "placed")

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
        # Give 10 bacon tokens for creating an organization
        giveBacon(instance.admin, 10)
        # Create an activity for the organization creation
        create_activity(instance, "created")
        # Give first organization badge
        assign_first_action_badge(instance.admin, "First Organization Created")