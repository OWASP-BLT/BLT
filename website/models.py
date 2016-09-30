from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from allauth.account.signals import user_signed_up, user_logged_in
from actstream import action
from django.dispatch import receiver
from urlparse import urlparse


class Domain(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True, unique=True)
    url = models.URLField()
    logo = models.ImageField(upload_to="logos", null=True, blank=True)
    webshot = models.ImageField(upload_to="webshots", null=True, blank=True)
    clicks = models.IntegerField(null=True, blank=True)
    color = models.CharField(max_length=10, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    twitter = models.CharField(max_length=30, null=True, blank=True)
    facebook = models.URLField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
   

    def __unicode__(self):
        return self.name

    @property
    def get_name(self):
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
        return "/domain/" + str(self.domain_name)


class Issue(models.Model):
    user = models.ForeignKey(User)
    domain = models.ForeignKey(Domain, null=True, blank=True)
    url = models.URLField()
    description = models.TextField()
    screenshot = models.ImageField(null=True, blank=True, upload_to="screenshots")
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.description

    @property
    def domain_title(self):
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
    logo = models.ImageField(upload_to="logos", null=True, blank=True)
    plan = models.CharField(max_length=10)
    color = models.CharField(max_length=10, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    @property
    def domain_title(self):
        parsed_url = urlparse(self.url)
        return parsed_url.netloc.split(".")[-2:][0].title()

    class Meta:
        ordering = ['-id']

class Points(models.Model):
    user = models.ForeignKey(User)
    issue = models.ForeignKey(Issue, null=True, blank=True)
    domain = models.ForeignKey(Domain, null=True, blank=True)
    score = models.IntegerField()





#@receiver(user_logged_in, dispatch_uid="some.unique.string.id.for.allauth.user_logged_in")
#def user_logged_in_(request, user, **kwargs):
#    if not settings.TESTING:
#    	action.send(user, verb='logged in')
