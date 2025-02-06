import logging
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.timezone import now

from website.models import Notification

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send reminder notifications to users who haven't checked in the last 24 hours."

    def handle(self, *args, **options):
        cutoff_date = now().date() - timedelta(days=1)

        users_without_checkin = User.objects.exclude(dailystatusreport__date__gte=cutoff_date)

        # Create the reminder notifications for these users
        for user in users_without_checkin:
            Notification.objects.create(
                user=user,
                message="Don't forget to complete your daily check-in!",
                notification_type="reminder",
                link="/add-sizzle-checkin",
            )

        count = users_without_checkin.count()
        logger.info(f"Sent reminder notifications to {count} users.")
