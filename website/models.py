import hashlib
import urllib

from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from allauth.account.signals import user_signed_up, user_logged_in
from actstream import action
from django.db.models.signals import post_save
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
from PIL import Image
from django.db.models import Count
from colorthief import ColorThief
from django.utils import timezone


class Domain(models.Model):
    name = models.CharField(max_length=255, unique=True)
    url = models.URLField()
    logo = models.ImageField(upload_to="logos", null=True, blank=True)
    webshot = models.ImageField(upload_to="webshots", null=True, blank=True)
    clicks = models.IntegerField(null=True, blank=True)
    email_event = models.CharField(max_length=255, default="", null=True, blank=True)
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
    def open_issues(self):
        return Issue.objects.filter(domain=self).exclude(status="closed")

    @property
    def closed_issues(self):
        return Issue.objects.filter(domain=self).filter(status="closed")


    @property
    def top_tester(self):
        return User.objects.filter(issue__domain=self).annotate(total=Count('issue')).order_by('-total').first()


    @property
    def get_name(self):
        parsed_url = urlparse(self.url)
        return parsed_url.netloc.split(".")[-2:][0].title()

    @property
    def get_logo(self):
        if self.logo:
            return self.logo.url
        image_request = requests.get("https://logo.clearbit.com/"+self.name)
        try:
            if image_request.status_code == 200:
                image_content = ContentFile(image_request.content)
                self.logo.save(self.name +".jpg", image_content)
                return self.logo.url
            
        except:
            favicon_url = self.url + '/favicon.ico'
            return favicon_url

    @property
    def get_color(self):
        if self.color:
            return self.color
        else:
            if not self.logo:
                self.get_logo()
            try:
                color_thief = ColorThief(self.logo)
                self.color = '#%02x%02x%02x' % color_thief.get_color(quality=1)
            except:
                self.color = "#0000ff"
            self.save()
            return self.color

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

    def get_absolute_url(self):
        return "/domain/" + self.name


def validate_image(fieldfile_obj):
        filesize = fieldfile_obj.file.size
        megabyte_limit = 3.0
        if filesize > megabyte_limit*1024*1024:
            raise ValidationError("Max file size is %sMB" % str(megabyte_limit))


class Issue(models.Model):
    labels = (
        (0, 'General'),
        (1, 'Number Error'),
        (2, 'Functional'),
        (3, 'Performance'),
        (4, 'Security'),
        (5, 'Typo'),
        (6, 'Design')        
    )
    user = models.ForeignKey(User, null=True, blank=True)
    domain = models.ForeignKey(Domain, null=True, blank=True)
    url = models.URLField()
    description = models.TextField()
    label = models.PositiveSmallIntegerField(choices=labels, default=0)
    views = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, default="open", null=True, blank=True)
    user_agent = models.CharField(max_length=255, default="", null=True, blank=True)
    ocr = models.TextField(default="", null=True, blank=True)
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
        issue_link = " bugheist.com/issue/"+str(self.id)
        prefix = "Bug found on @"
        spacer = " | "
        msg =  prefix + self.domain_title + spacer + self.description[:140-(len(prefix)+len(self.domain_title)+len(spacer)+len(issue_link))] + issue_link
        return msg

    def get_ocr(self):
        if self.ocr:
            return self.ocr
        else:
            try:
                import pytesseract
                self.ocr = pytesseract.image_to_string(Image.open(self.screenshot))
                self.save()
                return self.ocr
            except:
                return "OCR not installed"

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
            print 'ERROR:', str(ex)
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


class InviteFriend(models.Model):
    sender = models.ForeignKey(User)
    recipient = models.EmailField()
    sent = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ('-sent',)
        verbose_name = 'invitation'
        verbose_name_plural = 'invitations'


def user_images_path(instance, filename):
    from django.template.defaultfilters import slugify
    filename, ext = os.path.splitext(filename)
    return 'avatars/user_{0}/{1}{2}'.format(instance.user.id, slugify(filename), ext)


class UserProfile(models.Model):
    title = (
        (0, 'Unrated'),
        (1, 'Bronze'),
        (2, 'Silver'),
        (3, 'Gold'),
        (4, 'Platinum'),
    )
        

    user = models.OneToOneField(User, related_name="userprofile")
    user_avatar = models.ImageField(upload_to=user_images_path, blank=True, null=True)
    title = models.IntegerField(choices=title,default=0)


    def avatar(self, size=36):
        if self.user_avatar:
            return self.user_avatar.url

        for account in self.user.socialaccount_set.all():
            if 'avatar_url' in account.extra_data:
                return account.extra_data['avatar_url']
            elif 'picture' in account.extra_data:
                return account.extra_data['picture']

    def __unicode__(self):
        return self.user.email


def create_profile(sender, **kwargs):
    user = kwargs["instance"]
    if kwargs["created"]:
        profile = UserProfile(user=user)
        profile.save()

post_save.connect(create_profile, sender=User)
