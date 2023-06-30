import os
from urllib.parse import urlparse
import requests
import tweepy
from PIL import Image
from annoying.fields import AutoOneToOneField
from colorthief import ColorThief
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import models
from django.db.models import Count
from django.db.models import signals
from django.db.models.signals import post_save
from unidecode import unidecode
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from mdeditor.fields import MDTextField
from decimal import Decimal
from captcha.fields import CaptchaField
from django.core.files.storage import default_storage
import uuid


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
        Wallet.objects.create(user=instance)

class Subscription(models.Model):
    name = models.CharField(max_length=25, null=False, blank=True)
    charge_per_month = models.IntegerField(null=False, blank=True)
    hunt_per_domain = models.IntegerField(null=False, blank=True)
    number_of_domains = models.IntegerField(null=False, blank=True)
    feature = models.BooleanField(default=True)

def generate_uuid_for_company(apps, schema_editor):
    company_model = apps.get_model('website', 'Company')
    for obj in company_model.objects.all():
        obj.company_id = uuid.uuid4()  # Replace with your desired UUID generation logic
        obj.save()

class Company(models.Model):
    admin = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    managers = models.ManyToManyField(User,related_name="user_companies")
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to="company_logos", null=True, blank=True)
    company_id = models.CharField(max_length=255, unique=True, editable=False) # uuid
    url = models.URLField()
    email = models.EmailField(null=True, blank=True)
    twitter = models.CharField(max_length=30, null=True, blank=True)
    facebook = models.URLField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    subscription = models.ForeignKey(
        Subscription, null=True, blank=True, on_delete=models.CASCADE
    )
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Domain(models.Model):
    company = models.ForeignKey(
        Company, null=True, blank=True, on_delete=models.CASCADE
    )
    managers = models.ManyToManyField(User,related_name="user_domains")
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

    def __str__(self):
        return self.name

    @property
    def open_issues(self):
        return Issue.objects.filter(domain=self).exclude(status="closed")

    @property
    def closed_issues(self):
        return Issue.objects.filter(domain=self).filter(status="closed")

    @property
    def top_tester(self):
        return (
            User.objects.filter(issue__domain=self)
            .annotate(total=Count("issue"))
            .order_by("-total")
            .first()
        )

    @property
    def get_name(self):
        parsed_url = urlparse(self.url)
        return parsed_url.netloc.split(".")[-2:][0].title()

    def get_logo(self):
        if self.logo:
            return self.logo.url
        image_request = requests.get("https://logo.clearbit.com/" + self.name)
        try:
            if image_request.status_code == 200:
                image_content = ContentFile(image_request.content)
                self.logo.save(self.name + ".jpg", image_content)
                return self.logo.url

        except:
            favicon_url = self.url + "/favicon.ico"
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
                self.color = "#%02x%02x%02x" % color_thief.get_color(quality=1)
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
        temp = domain.rsplit(".")
        if len(temp) == 3:
            domain = temp[1] + "." + temp[2]
        return domain

    def get_absolute_url(self):
        return "/domain/" + self.name


def validate_image(fieldfile_obj):
    try:
        filesize = fieldfile_obj.file.size
    except:
        filesize = fieldfile_obj.size
    megabyte_limit = 3.0
    if filesize > megabyte_limit * 1024 * 1024:
        raise ValidationError("Max file size is %sMB" % str(megabyte_limit))


class Hunt(models.Model):
    
    class Meta:
        ordering = ["-id"]

    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    name = models.CharField(max_length=25)
    description = MDTextField(null=True, blank=True)
    url = models.URLField()
    prize = models.IntegerField(null=True, blank=True)
    prize_winner = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    prize_runner = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    prize_second_runner = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    logo = models.ImageField(upload_to="logos", null=True, blank=True)
    plan = models.CharField(max_length=10)
    txn_id = models.CharField(max_length=50, null=True, blank=True)
    color = models.CharField(max_length=10, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    starts_on = models.DateTimeField(null=True, blank=True)
    end_on = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    result_published = models.BooleanField(default=False)
    modified = models.DateTimeField(auto_now=True)

    @property
    def domain_title(self):
        parsed_url = urlparse(self.url)
        return parsed_url.netloc.split(".")[-2:][0].title()


    def __str__(self) -> str:
        return self.name


class Issue(models.Model):
    labels = (
        (0, "General"),
        (1, "Number Error"),
        (2, "Functional"),
        (3, "Performance"),
        (4, "Security"),
        (5, "Typo"),
        (6, "Design"),
        (7, "Server Down"),
    )
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    team_members = models.ManyToManyField(User,related_name="reportmembers")
    hunt = models.ForeignKey(Hunt, null=True, blank=True, on_delete=models.CASCADE)
    domain = models.ForeignKey(Domain, null=True, blank=True, on_delete=models.CASCADE)
    url = models.URLField()
    description = models.TextField()
    markdown_description = models.TextField(null=True,blank=True)
    captcha = CaptchaField()
    label = models.PositiveSmallIntegerField(choices=labels, default=0)
    views = models.IntegerField(null=True, blank=True)
    verified = models.BooleanField(default=False)
    score = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, default="open", null=True, blank=True)
    user_agent = models.CharField(max_length=255, default="", null=True, blank=True)
    ocr = models.TextField(default="", null=True, blank=True)
    screenshot = models.ImageField(upload_to="screenshots", null=True, blank=True, validators=[validate_image])
    closed_by = models.ForeignKey(
        User, null=True, blank=True, related_name="closed_by", on_delete=models.CASCADE
    )
    closed_date = models.DateTimeField(default=None, null=True, blank=True)
    github_url = models.URLField(default="", null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    is_hidden = models.BooleanField(default=False)
    rewarded = models.PositiveIntegerField(default=0) # money rewarded by the company


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
        temp = domain.rsplit(".")
        if len(temp) == 3:
            domain = temp[1] + "." + temp[2]
        return domain

    def get_twitter_message(self):
        issue_link = " " + settings.DOMAIN_NAME + "/issue/" + str(self.id)
        prefix = "Bug found on @"
        spacer = " | "
        msg = (
            prefix
            + self.domain_title
            + spacer
            + self.description[
                : 140
                - (len(prefix) + len(self.domain_title) + len(spacer) + len(issue_link))
            ]
            + issue_link
        )
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
        ordering = ["-created"]
    
    

class IssueScreenshot(models.Model):
    image = models.ImageField(upload_to="screenshots", validators=[validate_image])
    issue = models.ForeignKey(Issue,on_delete=models.CASCADE,related_name="screenshots")


@receiver(post_save, sender=Issue)
def update_issue_image_access(sender, instance, **kwargs):
   
    if instance.is_hidden :
        issue_screenshot_list=IssueScreenshot.objects.filter(issue=instance.id)
        for screenshot in issue_screenshot_list:
                old_name=screenshot.image.name
                if "hidden" not in old_name:
                    filename = screenshot.image.name
                    extension = filename.split(".")[-1] 
                    name = filename[12:99]+"hidden" + str(uuid.uuid4()) + "." + extension
                    default_storage.save(f"screenshots/{name}",screenshot.image)   
                    default_storage.delete(old_name)
                    screenshot.image=f"screenshots/{name}"
                    screenshot.image.name=f"screenshots/{name}"
                    screenshot.save()  

TWITTER_MAXLENGTH = getattr(settings, "TWITTER_MAXLENGTH", 140)


class Winner(models.Model):
    hunt = models.ForeignKey(Hunt, null=True, blank=True, on_delete=models.CASCADE)
    winner = models.ForeignKey(
        User, related_name="winner", null=True, blank=True, on_delete=models.CASCADE
    )
    runner = models.ForeignKey(
        User, related_name="runner", null=True, blank=True, on_delete=models.CASCADE
    )
    second_runner = models.ForeignKey(
        User,
        related_name="second_runner",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    prize_distributed = models.BooleanField(default=False)


def post_to_twitter(sender, instance, *args, **kwargs):
    if not kwargs.get("created"):
        return False
    try:
        consumer_key = os.environ["TWITTER_CONSUMER_KEY"]
        consumer_secret = os.environ["TWITTER_CONSUMER_SECRET"]
        access_key = os.environ["TWITTER_ACCESS_KEY"]
        access_secret = os.environ["TWITTER_ACCESS_SECRET"]
    except KeyError:
        print("WARNING: Twitter account not configured.")
        return False

    try:
        text = instance.get_twitter_message()
    except AttributeError:
        text = str(instance)

    mesg = "%s" % (text)
    if len(mesg) > TWITTER_MAXLENGTH:
        size = len(mesg + "...") - TWITTER_MAXLENGTH
        mesg = "%s..." % (text[:-size])

    import logging

    logger = logging.getLogger("testlogger")

    if not settings.DEBUG:
        try:
            auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
            auth.set_access_token(access_key, access_secret)
            api = tweepy.API(auth)
            file = default_storage.open(instance.screenshot.file.name, "rb")
            
            media_ids = api.media_upload(
                filename=unidecode(instance.screenshot.file.name), file=file
            )
            params = dict(status=mesg, media_ids=[media_ids.media_id_string])
            api.update_status(**params)

        except Exception as ex:
            logger.debug("rem %s" % str(ex))
            return False


class Points(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    issue = models.ForeignKey(Issue, null=True, blank=True, on_delete=models.CASCADE)
    domain = models.ForeignKey(Domain, null=True, blank=True, on_delete=models.CASCADE)
    score = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)


class InviteFriend(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    recipient = models.EmailField()
    sent = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-sent",)
        verbose_name = "invitation"
        verbose_name_plural = "invitations"


def user_images_path(instance, filename):
    from django.template.defaultfilters import slugify

    filename, ext = os.path.splitext(filename)
    return "avatars/user_{0}/{1}{2}".format(instance.user.id, slugify(filename), ext)


class UserProfile(models.Model):
    title = (
        (0, "Unrated"),
        (1, "Bronze"),
        (2, "Silver"),
        (3, "Gold"),
        (4, "Platinum"),
    )
    follows = models.ManyToManyField(
        "self", related_name="follower", symmetrical=False, blank=True
    )
    user = AutoOneToOneField(
        "auth.user", related_name="userprofile", on_delete=models.CASCADE
    )
    user_avatar = models.ImageField(upload_to=user_images_path, blank=True, null=True)
    title = models.IntegerField(choices=title, default=0)
    description = models.TextField(blank=True, null=True)
    winnings = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    issue_upvoted = models.ManyToManyField(Issue, blank=True, related_name="upvoted")
    issue_saved = models.ManyToManyField(Issue, blank=True, related_name="saved")
    issue_flaged = models.ManyToManyField(Issue,blank=True,related_name="flaged") 
    issues_hidden = models.BooleanField(default=False)

    def avatar(self, size=36):
        if self.user_avatar:
            return self.user_avatar.url

        for account in self.user.socialaccount_set.all():
            if "avatar_url" in account.extra_data:
                return account.extra_data["avatar_url"]
            elif "picture" in account.extra_data:
                return account.extra_data["picture"]

    def __unicode__(self):
        return self.user.email


def create_profile(sender, **kwargs):
    user = kwargs["instance"]
    if kwargs["created"]:
        profile = UserProfile(user=user)
        profile.save()


post_save.connect(create_profile, sender=User)


class IP(models.Model):
    address = models.CharField(max_length=25, null=True, blank=True)
    user = models.CharField(max_length=25, null=True, blank=True)
    issuenumber = models.IntegerField(null=True, blank=True)

    def ipaddress(self):
        return self.ipaddress

    def user_name(self):
        return self.user

    def issue_number(self):
        return self.issuenumber


class CompanyAdmin(models.Model):
    role = (
        (0, "Admin"),
        (1, "Moderator"),
    )
    role = models.IntegerField(choices=role, default=0)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    company = models.ForeignKey(
        Company, null=True, blank=True, on_delete=models.CASCADE
    )
    domain = models.ForeignKey(Domain, null=True, blank=True, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)


class Wallet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account_id = models.TextField(null=True, blank=True)
    current_balance = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def deposit(self, value):
        self.transaction_set.create(
            value=value, running_balance=self.current_balance + Decimal(value)
        )
        self.current_balance += Decimal(value)
        self.save()

    def withdraw(self, value):
        if value > self.current_balance:
            raise InsufficientBalance("This wallet has insufficient balance.")

        self.transaction_set.create(
            value=-value, running_balance=self.current_balance - Decimal(value)
        )
        self.current_balance -= Decimal(value)
        self.save()

    def transfer(self, wallet, value):
        self.withdraw(value)
        wallet.deposit(value)


class Transaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=6, decimal_places=2)
    running_balance = models.DecimalField(max_digits=6, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)


class Payment(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=6, decimal_places=2)
    active = models.BooleanField(default=True)
