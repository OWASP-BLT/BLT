from django.contrib.auth.models import User
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from blog.models import Post

from .models import Activity, Hunt, IpReport, Issue


@receiver(post_save, sender=Issue)
def create_activity_for_issue(sender, instance, created, **kwargs):
    if created:
        user = (
            instance.user if instance.user else User.objects.get_or_create(username="anonymous")[0]
        )

        activity = Activity.objects.create(
            user=user,
            action_type="create",
            title=f"Issue Created: {instance.description[:50]}",
            related_object_id=instance.id,
            related_object_type="Issue",
            description=instance.description,
            image=getattr(instance, "screenshot", None),
        )
        # Removed URL logic
        activity.save()


@receiver(post_save, sender=Hunt)
def create_or_update_hunt_activity(sender, instance, created, **kwargs):
    action_type = "create" if created else "update"
    activity = Activity.objects.create(
        user=instance.modified_by,  # Assuming you have a user field for modified_by
        action_type=action_type,
        title=f"Hunt '{instance.name}' has been {action_type}.",
        related_object_id=instance.id,
        related_object_type="Hunt",
        description=f"Hunt '{instance.name}' has been {action_type}.",
        image=instance.logo,
    )
    # Removed URL logic
    activity.save()


@receiver(post_delete, sender=Hunt)
def delete_hunt_activity(sender, instance, **kwargs):
    activity = Activity.objects.create(
        user=instance.modified_by,  # Assuming you have a user field for modified_by
        action_type="delete",
        title=f"Hunt '{instance.name}' has been deleted.",
        related_object_id=instance.id,
        related_object_type="Hunt",
        description=f"Hunt '{instance.name}' has been deleted.",
        image=instance.logo,
    )
    # Removed URL logic
    activity.save()


@receiver(post_save, sender=Post)
def create_activity_for_post(sender, instance, created, **kwargs):
    user = (
        instance.author if instance.author else User.objects.get_or_create(username="anonymous")[0]
    )

    activity = Activity(
        user=user,
        action_type="create" if created else "update",
        title=f"Blog Post {'Created' if created else 'Updated'}: {instance.title[:50]}",
        related_object_id=instance.id,
        related_object_type="Post",
        description=instance.content[:100],
        image=instance.image,
    )
    # Removed URL logic
    activity.save()


@receiver(post_delete, sender=Post)
def delete_activity_for_post(sender, instance, **kwargs):
    activity = Activity.objects.create(
        user=instance.author,
        action_type="delete",
        title=f"Blog Post Deleted: {instance.title[:50]}",
        related_object_id=instance.id,
        related_object_type="Post",
        description=f"The post '{instance.title}' was deleted.",
        image=instance.image,
    )
    # Removed URL logic
    activity.save()


@receiver(post_save, sender=IpReport)
def create_activity_for_ipreport(sender, instance, created, **kwargs):
    user = instance.user if instance.user else User.objects.get_or_create(username="anonymous")[0]
    activity = Activity.objects.create(
        user=user,
        action_type="create" if created else "update",
        title=f"IP Report {'Created' if created else 'Updated'}: {instance.ip_address}",
        related_object_id=instance.id,
        related_object_type="IpReport",
        description=instance.description[:100],
        image=None,
    )
    # Removed URL logic
    activity.save()


@receiver(post_delete, sender=IpReport)
def delete_activity_for_ipreport(sender, instance, **kwargs):
    activity = Activity.objects.create(
        user=instance.user,
        action_type="delete",
        title=f"IP Report Deleted: {instance.ip_address}",
        related_object_id=instance.id,
        related_object_type="IpReport",
        description=f"The report for IP {instance.ip_address} has been deleted.",
        image=None,
    )
    # Removed URL logic
    activity.save()
