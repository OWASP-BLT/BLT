from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from allauth.account.signals import user_signed_up, user_logged_in
from actstream import action
from django.dispatch import receiver
from urlparse import urlparse
from django.db.models import signals
import os
import urllib2
import tweepy
import tempfile
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError
from unidecode import unidecode
from django.core.files.base import ContentFile
import requests

class Domain(models.Model):
    name = models.CharField(max_length=255, unique=True)
    url = models.URLField()
    logo = models.ImageField(upload_to="logos", null=True, blank=True)
    webshot = models.ImageField(upload_to="webshots", null=True, blank=True)
    clicks = models.IntegerField(null=True, blank=True)
    color = models.CharField(max_length=10, null=True, blank=True)
    github = models.CharField(max_length=255, null=True, blank=True)
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
    def get_logo(self):
        if self.logo:
            return self.logo.url
        else:
            image_content = ContentFile(requests.get("https://logo.clearbit.com/"+self.name).content)
            self.logo.save(self.name +".jpg", image_content)
            return self.logo.url

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

def validate_image(fieldfile_obj):
        filesize = fieldfile_obj.file.size
        megabyte_limit = 3.0
        if filesize > megabyte_limit*1024*1024:
            raise ValidationError("Max file size is %sMB" % str(megabyte_limit))

class Issue(models.Model):
    user = models.ForeignKey(User)
    domain = models.ForeignKey(Domain, null=True, blank=True)
    url = models.URLField()
    description = models.TextField()
    screenshot = models.ImageField(upload_to="screenshots", validators=[validate_image])
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

    def get_twitter_message(self):
        issue_link = " http://bugheist.com/issue/"+str(self.id)
        prefix = "Bug found on @"
        spacer = " | "
        msg =  prefix + self.domain_title + spacer + self.description[:140-(len(prefix)+len(self.domain_title)+len(spacer)+len(issue_link))] + issue_link
        return msg

    @property
    def get_absolute_url(self):
        return "/issue/" + str(self.id)
    
    class Meta:
        ordering = ['-created']


TWITTER_MAXLENGTH = getattr(settings, 'TWITTER_MAXLENGTH', 140)

def post_to_twitter(sender, instance, *args, **kwargs):

    if not kwargs.get('created'):
        return False

    try:
        consumer_key = os.environ['TWITTER_CONSUMER_KEY']
        consumer_secret = os.environ['TWITTER_CONSUMER_SECRET']
        access_key = os.environ['TWITTER_ACCESS_KEY']
        access_secret = os.environ['TWITTER_ACCESS_SECRET']
    except KeyError:
        print 'WARNING: Twitter account not configured.'
        return False

    try:
        text = instance.get_twitter_message()
    except AttributeError:
        text = unicode(instance)

    mesg = u'%s' % (text)
    if len(mesg) > TWITTER_MAXLENGTH:
        size = len(mesg + '...') - TWITTER_MAXLENGTH
        mesg = u'%s...' % (text[:-size])

    import logging
    logger = logging.getLogger('testlogger')
    

    if not settings.DEBUG:
        try:
            auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
            auth.set_access_token(access_key, access_secret)
            api = tweepy.API(auth)
            file = default_storage.open(instance.screenshot.file.name, 'rb')
            media_ids = api.media_upload(filename=unidecode(instance.screenshot.file.name), file=file)
            params = dict(status=mesg, media_ids=[media_ids.media_id_string])
            api.update_status(**params)

        except Exception, ex:
            print 'ERROR:', str(ex), params
            logger.debug('rem %s'%str(ex))
            return False

signals.post_save.connect(post_to_twitter, sender=Issue)

class Hunt(models.Model):
    user = models.ForeignKey(User)
    url = models.URLField()
    prize = models.IntegerField()
    logo = models.ImageField(upload_to="logos", null=True, blank=True)
    plan = models.CharField(max_length=10)
    txn_id = models.CharField(max_length=50, null=True, blank=True)
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
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)


#@receiver(user_logged_in, dispatch_uid="some.unique.string.id.for.allauth.user_logged_in")
#def user_logged_in_(request, user, **kwargs):
#    if not settings.TESTING:
#    	action.send(user, verb='logged in')
