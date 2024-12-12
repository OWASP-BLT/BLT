from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from blog.models import Post

from .models import (
    Activity,
    Badge,
    Bid,
    Hunt,
    IpReport,
    Issue,
    Suggestion,
    TimeLog,
    UserBadge,
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
            print(f"Assigned '{action_title}' badge to {user.username}")


def create_activity(instance, action_type):
    """Generic function to create an activity for a given model instance."""
    model_name = instance._meta.model_name
    user_field = (
        getattr(instance, "user", None)
        or getattr(instance, "author", None)
        or getattr(instance, "modified_by", None)
    )
    user = user_field or get_default_user()

    # Get the content type of the instance
    content_type = ContentType.objects.get_for_model(instance)

    # Create the activity
    Activity.objects.create(
        user=user,
        action_type=action_type,
        title=f"{model_name.capitalize()} {action_type.capitalize()} {getattr(instance, 'name', getattr(instance, 'title', ''))[:50]}",
        content_type=content_type,
        object_id=instance.id,  # Use object_id for GenericForeignKey
        description=getattr(instance, "description", getattr(instance, "content", ""))[:100],
        image=getattr(instance, "screenshot", getattr(instance, "image", None)),
    )


@receiver(post_save)
def handle_post_save(sender, instance, created, **kwargs):
    """Generic handler for post_save signal."""
    if sender == IpReport and created:  # Track first IP report
        assign_first_action_badge(instance.user, "First IP Reported")
        create_activity(instance, "created")

    elif sender == Post and created:  # Track first blog post
        assign_first_action_badge(instance.user, "First Blog Posted")
        create_activity(instance, "created")

    elif sender == Issue and created:  # Track first bug report
        assign_first_action_badge(instance.user, "First Bug Reported")
        create_activity(instance, "created")

    elif sender == Hunt and created:  # Track first bid placed
        assign_first_action_badge(instance.user, "First Bug Bounty")
        create_activity(instance, "created")

    elif sender == Suggestion and created:  # Track first suggestion
        assign_first_action_badge(instance.user, "First Suggestion")
        create_activity(instance, "suggested")

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
    if sender in [Issue, Hunt, IpReport, Post]:  # Add any model you want to track
        create_activity(instance, "deleted")


@receiver(post_save, sender=TimeLog)
def update_user_streak(sender, instance, created, **kwargs):
    """
    Automatically update user's streak when a TimeLog is created
    """
    if created:
        # Use the date of the start_time for streak tracking
        check_in_date = instance.start_time.date()
        # Get the user's profile and update streak
        try:
            user_profile = instance.user.userprofile
            user_profile.update_streak_and_award_points(check_in_date)
        except UserProfile.DoesNotExist:
            # Fallback: create profile if it doesn't exist
            UserProfile.objects.create(
                user=instance.user, current_streak=1, longest_streak=1, last_check_in=check_in_date
            )
