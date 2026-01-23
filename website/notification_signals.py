import logging

from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from website.models import (
    FlaggedContent,
    GitHubIssue,
    JoinRequest,
    Kudos,
    ModerationAction,
    Notification,
    Points,
    Post,
    User,
    UserBadge,
)

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Points)
def create_notification_on_points_reward(sender, instance, created, **kwargs):
    """
    Signal to create a notification whenever points are rewarded.
    """
    if created:
        message = f"You have been awarded {instance.score} points!"
        if instance.reason:
            message += f" Reason: {instance.reason}"

        link = f"/profile/{instance.user.username}"

        Notification.objects.create(user=instance.user, message=message, notification_type="reward", link=link)


@receiver(post_save, sender=JoinRequest)
def notify_admins_on_join_request(sender, instance, created, **kwargs):
    """
    Signal to notify team admins/managers when a new join request is submitted.
    """
    if created:
        team = instance.team
        recipients = list(team.managers.all())
        if team.admin:
            recipients.append(team.admin)

        recipients = list(set(recipients))

        message = f"New join request for team '{team.name}' from {instance.user.username}."
        link = reverse("/teams/join-requests/")

        for user in recipients:
            Notification.objects.create(user=user, message=message, notification_type="alert", link=link)


@receiver(post_save, sender=Kudos)
def notify_receiver_on_kudos(sender, instance, created, **kwargs):
    """
    Signal to notify the receiver when they receive a Kudos.
    """
    if created:
        message = f"You have received kudos from {instance.sender.username}."
        if instance.comment:
            message += f" Comment: {instance.comment}"

        Notification.objects.create(user=instance.receiver, message=message, notification_type="reward", link=None)


@receiver(post_save, sender=Post)
def notify_users_on_post_creation(sender, instance, created, **kwargs):
    """
    Signal to notify users when a new Post is created.
    """
    if created:
        message = f"Checkout a new post '{instance.title}' by {instance.author.username}!"
        link = instance.get_absolute_url()

        users = User.objects.exclude(username=instance.author.username)
        for user in users:
            Notification.objects.create(user=user, message=message, notification_type="promo", link=link)


@receiver(post_save, sender=UserBadge)
def notify_user_on_badge_recieved(sender, instance, created, **kwargs):
    """
    Signal to notify users when they receive a new badge.
    """
    if created:
        message = f"You have just earned a new badge: {instance.badge.title}!"

        link = f"/profile/{instance.user.username}"

        Notification.objects.create(user=instance.user, message=message, notification_type="reward", link=link)


@receiver(post_save, sender=GitHubIssue)
def notify_on_payment_processed(sender, instance, created, update_fields, **kwargs):
    """
    Signal to notify users and admins when a payment is processed.
    This triggers whenever a GitHubIssue with payment information is saved.
    """
    # Check if this is a payment update (either sponsors_tx_id or bch_tx_id is updated)
    if instance.p2p_payment_created_at and (instance.sponsors_tx_id or instance.bch_tx_id):
        payment_type = "GitHub Sponsors" if instance.sponsors_tx_id else "Bitcoin Cash"
        tx_id = instance.sponsors_tx_id or instance.bch_tx_id

        # Only send notifications if the payment was just added/updated
        if created or (
            update_fields
            and (
                "sponsors_tx_id" in update_fields
                or "bch_tx_id" in update_fields
                or "p2p_payment_created_at" in update_fields
            )
        ):
            logger.info(
                f"Payment notification processing: Issue #{instance.issue_id}, " f"Type: {payment_type}, TX: {tx_id}"
            )

            # Create notification for the issue reporter
            if instance.user:
                message = (
                    f"Your bounty for issue #{instance.issue_id} has been paid via {payment_type}. "
                    f"Transaction ID: {tx_id}"
                )
                link = instance.html_url

                Notification.objects.create(user=instance.user, message=message, notification_type="reward", link=link)
                logger.info(f"Created payment notification for issue reporter: {instance.user.username}")

            # Notify superusers (admin team) about the payment
            superusers = User.objects.filter(is_superuser=True)
            for admin in superusers:
                # Don't notify the admin who made the payment
                if instance.sent_by_user and admin.id == instance.sent_by_user.id:
                    continue

                message = (
                    f"Payment processed for issue #{instance.issue_id} via {payment_type}. " f"Transaction ID: {tx_id}"
                )
                if instance.sent_by_user:
                    message += f" (by {instance.sent_by_user.username})"

                link = instance.html_url

                Notification.objects.create(user=admin, message=message, notification_type="alert", link=link)
                logger.info(f"Created payment notification for admin: {admin.username}")


@receiver(post_save, sender=FlaggedContent)
def notify_moderators_on_content_flagged(sender, instance, created, **kwargs):
    """
    Signal to notify moderators when content is flagged by AI spam detection.
    Only sends notifications for newly created flagged content with pending status.
    """
    if created and instance.status == "pending":
        # Get all staff users and superusers who can moderate
        moderators = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).distinct()
        moderators = moderators.distinct()

        # Get content preview
        content_preview = instance.get_content_preview()
        content_type = instance.content_type.model.title()

        # Build admin review link
        admin_link = f"/admin/website/flaggedcontent/{instance.id}/change/"

        # Create notification message
        message = (
            f"🚨 Spam Alert: {content_type} flagged with {instance.spam_score:.0%} confidence. "
            f"Reason: {instance.get_reason_display()}. "
            f"Preview: {content_preview[:50]}..."
        )

        # Create notifications for all moderators
        notification_count = 0
        for moderator in moderators:
            # Don't notify the reporter if they're a moderator
            if instance.reporter and moderator.id == instance.reporter.id:
                continue

            Notification.objects.create(
                user=moderator,
                message=message,
                notification_type="alert",
                link=admin_link,
            )
            notification_count += 1

        # Create audit record for the flagging
        ModerationAction.objects.create(
            flagged_content=instance,
            action="flagged",
            performed_by=instance.reporter,
            notes=f"Auto-detected by AI with {instance.spam_score:.2%} confidence. Category: {instance.get_reason_display()}",
        )

        logger.info(
            f"Spam detection notification: {content_type} #{instance.object_id} flagged. "
            f"Score: {instance.spam_score:.2%}. Notified {notification_count} moderators."
        )
