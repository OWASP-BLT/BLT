import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from website.models import GitHubIssue, JoinRequest, Kudos, Notification, Points, Post, User, UserBadge, UserProfile

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


@receiver(post_save, sender=UserProfile)
def verify_github_linkback_on_profile_update(sender, instance, **kwargs):
    """
    Signal to verify GitHub linkback and award tokens when user adds/updates GitHub URL.

    Uses transaction.on_commit() to defer verification until after the profile
    save transaction commits, avoiding nested transaction issues.
    Only runs when github_url field is actually updated to avoid unnecessary API calls.
    Rate limited to prevent abuse and API exhaustion.
    """
    # Skip if no github_url or reward already given
    # NOTE: Only one reward is given per user, even if they change their GitHub profile.
    # Users can update their GitHub URL, but they won't receive duplicate rewards.
    if not instance.github_url or instance.github_linking_reward_given:
        return

    # Only verify if github_url was updated (not on every profile save)
    update_fields = kwargs.get("update_fields")
    if update_fields is not None and "github_url" not in update_fields:
        return

    # Rate limiting: prevent repeated GitHub API calls (5 minutes cooldown)
    from django.core.cache import cache

    rate_key = f"github_verify_rate_{instance.user.id}"
    if not cache.add(rate_key, True, timeout=300):  # 5 minutes
        logger.debug(f"Rate limit: Skipping GitHub verification for {instance.user.username}")
        return

    def perform_verification():
        # Import here to avoid circular imports
        from website.github_verification import (
            award_github_linking_tokens,
            extract_github_username,
            verify_github_linkback,
        )

        logger.info(f"Starting GitHub linkback verification for {instance.user.username}")

        # Extract username from GitHub URL
        github_username = extract_github_username(instance.github_url)
        if not github_username:
            logger.warning(f"Invalid GitHub URL for user {instance.user.username}")
            return

        # Verify linkback
        verification_result = verify_github_linkback(github_username)

        if verification_result["verified"]:
            logger.info(
                f"GitHub linkback verified for {instance.user.username} "
                f"(found in: {verification_result['found_in']})"
            )

            # Award tokens (pass github_username to avoid redundant extraction)
            # Notification is created inside award_github_linking_tokens for atomicity
            success = award_github_linking_tokens(instance.user, github_username)

            if success:
                logger.info(f"Successfully awarded tokens and created notification for {instance.user.username}")
        else:
            logger.debug(
                f"GitHub linkback not verified for {instance.user.username}. "
                "User needs to add BLT link to their GitHub profile."
            )

    # Defer verification until after the current transaction commits
    transaction.on_commit(perform_verification)
