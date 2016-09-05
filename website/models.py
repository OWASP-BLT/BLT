from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from allauth.account.signals import user_signed_up, user_logged_in
from actstream import action
from django.dispatch import receiver
from urlparse import urlparse

class Issue(models.Model):
    user = models.ForeignKey(User)
    url = models.URLField()
    description = models.TextField()
    screenshot = models.ImageField(null=True, blank=True, upload_to="screenshots")
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.description

    @property
    def domain(self):
        parsed_url = urlparse(self.url)
        return parsed_url.netloc.split(".")[-2:][0].title()

    @property
    def hostname_domain(self):
        parsed_url = urlparse(self.url)
        return parsed_url.hostname

    @property
    def domain_name(self):
        parsed_url = urlparse(self.url)
        domain = parsed_url.hostname
        temp = domain.rsplit('.')
        if(len(temp) == 3):
            domain = temp[1] + '.' + temp[2]
        return domain

    @property
    def get_absolute_url(self):
        return "/issue/" + str(self.id)
    
    class Meta:
        ordering = ['-created']


class Hunt(models.Model):
    user = models.ForeignKey(User)
    url = models.URLField()
    prize = models.IntegerField()
    logo = models.ImageField(upload_to="logos")
    plan = models.CharField(max_length=10)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

class Points(models.Model):
    user = models.ForeignKey(User)
    issue = models.ForeignKey(Issue)
    score = models.IntegerField()


#class Domain(models.Model):
#    name = models.TextField()
#    logo = models.URLField()
#    hunt_url = models.URLField()


@receiver(user_logged_in, dispatch_uid="some.unique.string.id.for.allauth.user_logged_in")
def user_logged_in_(request, user, **kwargs):
    if not settings.TESTING:
    	action.send(user, verb='logged in')
