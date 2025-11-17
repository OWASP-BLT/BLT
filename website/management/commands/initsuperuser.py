import logging

from django.conf import settings
from django.contrib.auth.models import User

from website.management.base import LoggedBaseCommand

logger = logging.getLogger(__name__)


class Command(LoggedBaseCommand):
    def handle(self, *args, **options):
        for user in settings.SUPERUSERS:
            USERNAME = user[0]
            EMAIL = user[1]
            PASSWORD = user[2]
            logger.info("Creating superuser for %s (%s)" % (USERNAME, EMAIL))
            if settings.DEBUG:
                superuser = User.objects.create_superuser(username=USERNAME, email=EMAIL, password=PASSWORD)
                superuser.save()
            else:
                logger.info("Skipping superuser creation in non-debug mode")
