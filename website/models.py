from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from allauth.account.signals import user_signed_up, user_logged_in
from actstream import action
from django.dispatch import receiver

class Issue(models.Model):
    user = models.ForeignKey(User)
    url = models.URLField()
    description = models.TextField()
    screenshot = models.ImageField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)


@receiver(user_logged_in, dispatch_uid="some.unique.string.id.for.allauth.user_logged_in")
def user_logged_in_(request, user, **kwargs):
    if not settings.TESTING:
    	action.send(user, verb='logged in')
