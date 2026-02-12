import logging

from django.conf import settings
from django.contrib.auth.models import User

from website.management.base import LoggedBaseCommand

logger = logging.getLogger(__name__)


class Command(LoggedBaseCommand):
    def handle(self, *args, **options):
        for user in settings.SUPERUSERS:
            username = user[0]
            email = user[1]
            password = user[2]
            logger.info(f"Creating superuser for {username} ({email})")
            if settings.DEBUG:
                User.objects.create_superuser(username=username, email=email, password=password)
            else:
                logger.info("Skipping superuser creation in non-debug mode")
