from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from blog.models import Post

from .models import Activity, Hunt, IpReport, Issue


def get_default_user():
    """Get or create a default 'anonymous' user."""
    return User.objects.get_or_create(username="anonymous")[0]


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
    if sender in [Issue, Hunt, IpReport, Post]:  # Add any model you want to track
        if created:
            create_activity(instance, "created")
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
