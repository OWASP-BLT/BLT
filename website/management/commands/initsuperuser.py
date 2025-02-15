from django.conf import settings
from django.contrib.auth.models import User

from website.management.base import LoggedBaseCommand


class Command(LoggedBaseCommand):
    def handle(self, *args, **options):
        for user in settings.SUPERUSERS:
            USERNAME = user[0]
            EMAIL = user[1]
            PASSWORD = user[2]
            print("Creating superuser for %s (%s)" % (USERNAME, EMAIL))
            superuser = User.objects.create_superuser(username=USERNAME, email=EMAIL, password=PASSWORD)
            superuser.save()
