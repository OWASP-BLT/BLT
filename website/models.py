import os
import uuid
from decimal import Decimal
from urllib.parse import urlparse

import requests
from annoying.fields import AutoOneToOneField
from captcha.fields import CaptchaField
from colorthief import ColorThief
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.validators import URLValidator
from django.db import models
from django.db.models import Count
from django.db.models.signals import post_save
from django.dispatch import receiver
from google.cloud import storage
from mdeditor.fields import MDTextField
from PIL import Image
from rest_framework.authtoken.models import Token


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
    company_model = apps.get_model("website", "Company")
    for obj in company_model.objects.all():
        obj.company_id = uuid.uuid4()  # Replace with your desired UUID generation logic
        obj.save()


class Company(models.Model):
    admin = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    managers = models.ManyToManyField(User, related_name="user_companies")
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to="company_logos", null=True, blank=True)
    company_id = models.CharField(max_length=255, unique=True, editable=False)  # uuid
    url = models.URLField()
    email = models.EmailField(null=True, blank=True)
    twitter = models.CharField(max_length=30, null=True, blank=True)
    facebook = models.URLField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    subscription = models.ForeignKey(Subscription, null=True, blank=True, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Domain(models.Model):
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.CASCADE)
    managers = models.ManyToManyField(User, related_name="user_domains")
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
        domain = parsed_url.path
        if domain is not None:
            temp = domain.rsplit(".")
            if len(temp) == 3:
                domain = temp[1] + "." + temp[2]
        return domain

    def get_absolute_url(self):
        return "/domain/" + self.name

    def get_or_set_x_url(self, name):
        if self.twitter:
            return self.twitter

        validate = URLValidator(schemes=["https"])  # Only allow HTTPS URLs
        try:
            twitter_url = "https://twitter.com/%s" % (name)
            validate(twitter_url)
            self.twitter = name
            self.save()
            return name
        except ValidationError:
            pass


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
    banner = models.ImageField(upload_to="banners", null=True, blank=True)
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


class HuntPrize(models.Model):
    hunt = models.ForeignKey(Hunt, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    value = models.PositiveIntegerField(default=0)
    no_of_eligible_projects = models.PositiveIntegerField(default=1)  # no of winner in this prize
    valid_submissions_eligible = models.BooleanField(
        default=False
    )  # all valid submissions are winners in this prize
    prize_in_crypto = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return self.hunt.name + self.name


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
    team_members = models.ManyToManyField(User, related_name="reportmembers", blank=True)
    hunt = models.ForeignKey(Hunt, null=True, blank=True, on_delete=models.CASCADE)
    domain = models.ForeignKey(Domain, null=True, blank=True, on_delete=models.CASCADE)
    url = models.URLField()
    description = models.TextField()
    markdown_description = models.TextField(null=True, blank=True)
    captcha = CaptchaField()
    label = models.PositiveSmallIntegerField(choices=labels, default=0)
    views = models.IntegerField(null=True, blank=True)
    verified = models.BooleanField(default=False)
    score = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, default="open", null=True, blank=True)
    user_agent = models.CharField(max_length=255, default="", null=True, blank=True)
    ocr = models.TextField(default="", null=True, blank=True)
    screenshot = models.ImageField(
        upload_to="screenshots", null=True, blank=True, validators=[validate_image]
    )
    closed_by = models.ForeignKey(
        User, null=True, blank=True, related_name="closed_by", on_delete=models.CASCADE
    )
    closed_date = models.DateTimeField(default=None, null=True, blank=True)
    github_url = models.URLField(default="", null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    is_hidden = models.BooleanField(default=False)
    rewarded = models.PositiveIntegerField(default=0)  # money rewarded by the company
    reporter_ip_address = models.GenericIPAddressField(null=True, blank=True)
    cve_id = models.CharField(max_length=16, null=True, blank=True)
    cve_score = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)

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
                : 140 - (len(prefix) + len(self.domain_title) + len(spacer) + len(issue_link))
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

    def remove_user(self):
        self.user = None
        self.save()

    def get_absolute_url(self):
        return "/issue/" + str(self.id)

    def get_cve_score(self):
        if self.cve_id is None:
            return None
        try:
            url = "https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=%s" % (self.cve_id)
            response = requests.get(url).json()
            results = response["resultsPerPage"]
            if results != 0:
                metrics = response["vulnerabilities"][0]["cve"]["metrics"]
                if metrics:
                    cvss_metric_v = next(iter(metrics))
                    return metrics[cvss_metric_v][0]["cvssData"]["baseScore"]
        except (requests.exceptions.HTTPError, requests.exceptions.ReadTimeout) as e:
            print(e)
            return None

    class Meta:
        ordering = ["-created"]


class IssueScreenshot(models.Model):
    image = models.ImageField(upload_to="screenshots", validators=[validate_image])
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="screenshots")

    # def delete(self, *args, **kwargs):
    #     if self.image:
    #         # Delete the image file
    #         storage = self.image.storage
    #         name = (
    #             self.image.name
    #         )  # Use .name to get the relative file path in the storage system
    #         storage.delete(name)
    #     super(IssueScreenshot, self).delete(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.image:
            client = storage.Client()
            bucket = client.bucket(settings.GS_BUCKET_NAME)
            blob = bucket.blob(self.image.name)
            blob.delete()

        super().delete(*args, **kwargs)


@receiver(post_save, sender=Issue)
def update_issue_image_access(sender, instance, **kwargs):
    if instance.is_hidden:
        issue_screenshot_list = IssueScreenshot.objects.filter(issue=instance.id)
        for screenshot in issue_screenshot_list:
            old_name = screenshot.image.name
            if "hidden" not in old_name:
                filename = screenshot.image.name
                extension = filename.split(".")[-1]
                name = filename[:20] + "hidden" + str(uuid.uuid4())[:40] + "." + extension
                default_storage.save(f"screenshots/{name}", screenshot.image)
                default_storage.delete(old_name)
                screenshot.image = f"screenshots/{name}"
                screenshot.image.name = f"screenshots/{name}"
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


class Points(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    issue = models.ForeignKey(Issue, null=True, blank=True, on_delete=models.CASCADE)
    domain = models.ForeignKey(Domain, null=True, blank=True, on_delete=models.CASCADE)
    score = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)


class InviteFriend(models.Model):
    sender = models.ForeignKey(User, related_name="sent_invites", on_delete=models.CASCADE)
    recipients = models.ManyToManyField(User, related_name="received_invites", blank=True)
    referral_code = models.CharField(max_length=100, default=uuid.uuid4, editable=False)
    point_by_referral = models.IntegerField(default=0)

    def __str__(self):
        return f"Invite from {self.sender}"


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
    follows = models.ManyToManyField("self", related_name="follower", symmetrical=False, blank=True)
    user = AutoOneToOneField("auth.user", related_name="userprofile", on_delete=models.CASCADE)
    user_avatar = models.ImageField(upload_to=user_images_path, blank=True, null=True)
    title = models.IntegerField(choices=title, default=0)
    description = models.TextField(blank=True, null=True)
    winnings = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    issue_upvoted = models.ManyToManyField(Issue, blank=True, related_name="upvoted")
    issue_downvoted = models.ManyToManyField(Issue, blank=True, related_name="downvoted")
    issue_saved = models.ManyToManyField(Issue, blank=True, related_name="saved")
    issue_flaged = models.ManyToManyField(Issue, blank=True, related_name="flaged")
    issues_hidden = models.BooleanField(default=False)

    subscribed_domains = models.ManyToManyField(Domain, related_name="user_subscribed_domains")
    subscribed_users = models.ManyToManyField(User, related_name="user_subscribed_users")
    btc_address = models.CharField(max_length=100, blank=True, null=True)
    bch_address = models.CharField(max_length=100, blank=True, null=True)
    eth_address = models.CharField(max_length=100, blank=True, null=True)

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
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.CASCADE)
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


class ContributorStats(models.Model):
    username = models.CharField(max_length=255, unique=True)
    commits = models.IntegerField(default=0)
    issues_opened = models.IntegerField(default=0)
    issues_closed = models.IntegerField(default=0)
    prs = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    assigned_issues = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username


class Monitor(models.Model):
    url = models.URLField()
    keyword = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    last_checked_time = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("UP", "Up"),
            ("DOWN", "Down"),
        ],
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Monitor for {self.url} by {self.user}"
