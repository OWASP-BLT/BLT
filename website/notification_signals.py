from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from website.models import JoinRequest, Kudos, Notification, Points, Post, User, UserBadge


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
