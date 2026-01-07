import logging
import os
import re
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from urllib.parse import parse_qs, urlparse

import pytz
import requests
from annoying.fields import AutoOneToOneField
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.validators import MaxValueValidator, MinValueValidator, URLValidator
from django.db import models, transaction
from django.db.models import Count, F
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from google.api_core.exceptions import NotFound
from google.cloud import storage
from mdeditor.fields import MDTextField
from rest_framework.authtoken.models import Token

logger = logging.getLogger(__name__)

# --- Validators ---
def validate_bch_address(value):
    if not value.startswith("bitcoincash:"):
        raise ValidationError('BCH address must be in the new CashAddr format starting with "bitcoincash:"')

def validate_btc_address(value):
    if not (value.startswith("bc1") or value.startswith("3") or value.startswith("1")):
        raise ValidationError('BTC address must be in a valid format (SegWit addresses start with "bc1")')

def validate_image(fieldfile_obj):
    try:
        filesize = fieldfile_obj.file.size
    except:
        filesize = fieldfile_obj.size
    megabyte_limit = 3.0
    if filesize > megabyte_limit * 1024 * 1024:
        raise ValidationError("Max file size is %sMB" % str(megabyte_limit))

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)

# --- Models ---

class Subscription(models.Model):
    name = models.CharField(max_length=25, null=False, blank=True)
    charge_per_month = models.IntegerField(null=False, blank=True)
    hunt_per_domain = models.IntegerField(null=False, blank=True)
    number_of_domains = models.IntegerField(null=False, blank=True)
    feature = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

class Tag(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super(Tag, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

class IntegrationServices(Enum):
    SLACK = "slack"

class Integration(models.Model):
    service_name = models.CharField(
        max_length=20,
        choices=[(tag.value, tag.name) for tag in IntegrationServices],
        null=True,
        blank=True,
    )
    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        related_name="organization_integrations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.organization.name} - {self.service_name} Integration"

class SlackIntegration(models.Model):
    integration = models.OneToOneField(Integration, on_delete=models.CASCADE, related_name="slack_integration")
    bot_access_token = models.CharField(max_length=255, null=True, blank=True)
    workspace_name = models.CharField(max_length=255, null=True, blank=True)
    default_channel_name = models.CharField(max_length=255, null=True, blank=True)
    default_channel_id = models.CharField(max_length=255, null=True, blank=True)
    daily_updates = models.BooleanField(default=False)
    daily_update_time = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(23)],
    )
    welcome_message = models.TextField(null=True, blank=True)

class SlackChannel(models.Model):
    channel_id = models.CharField(max_length=50, unique=True, primary_key=True)
    name = models.CharField(max_length=255, db_index=True)
    topic = models.TextField(blank=True, default="")
    purpose = models.TextField(blank=True, default="")
    num_members = models.IntegerField(default=0)
    is_private = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    is_general = models.BooleanField(default=False)
    creator = models.CharField(max_length=50, blank=True, default="")
    created_at = models.DateTimeField(null=True, blank=True)
    slack_url = models.URLField(max_length=255, blank=True, default="")
    last_synced = models.DateTimeField(auto_now=True)
    organization = models.ForeignKey("Organization", null=True, blank=True, on_delete=models.SET_NULL, related_name="slack_channels")
    project = models.ForeignKey("Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="slack_channels")

    class Meta:
        ordering = ["-num_members", "name"]
        indexes = [
            models.Index(fields=["name"], name="slackchannel_name_idx"),
            models.Index(fields=["num_members"], name="slackchannel_members_idx"),
        ]

class OrganisationType(Enum):
    ORGANIZATION = "organization"
    INDIVIDUAL = "individual"
    TEAM = "team"

class Organization(models.Model):
    admin = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    managers = models.ManyToManyField(User, related_name="user_organizations", blank=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True, max_length=255)
    description = models.CharField(max_length=500, null=True, blank=True)
    logo = models.ImageField(upload_to="organization_logos", null=True, blank=True, max_length=255)
    url = models.URLField(unique=True, max_length=255)
    email = models.EmailField(null=True, blank=True)
    twitter = models.URLField(null=True, blank=True)
    matrix_url = models.URLField(null=True, blank=True)
    slack_url = models.URLField(null=True, blank=True)
    discord_url = models.URLField(null=True, blank=True)
    gitter_url = models.URLField(null=True, blank=True)
    zulipchat_url = models.URLField(null=True, blank=True)
    element_url = models.URLField(null=True, blank=True)
    facebook = models.URLField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    subscription = models.ForeignKey(Subscription, null=True, blank=True, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, blank=True)
    integrations = models.ManyToManyField(Integration, related_name="organizations", blank=True)
    trademark_count = models.IntegerField(default=0)
    trademark_check_date = models.DateTimeField(null=True, blank=True)
    team_points = models.IntegerField(default=0)
    tagline = models.CharField(max_length=255, blank=True, null=True)
    license = models.CharField(max_length=100, blank=True, null=True)
    categories = models.JSONField(default=list)
    contributor_guidance_url = models.URLField(blank=True, null=True)
    tech_tags = models.JSONField(default=list)
    topic_tags = models.JSONField(default=list)
    source_code = models.URLField(blank=True, null=True)
    ideas_link = models.URLField(blank=True, null=True)
    repos_updated_at = models.DateTimeField(null=True, blank=True)
    type = models.CharField(
        max_length=15,
        choices=[(tag.value, tag.name) for tag in OrganisationType],
        default=OrganisationType.ORGANIZATION.value,
    )
    check_ins_enabled = models.BooleanField(default=False)

    # Address fields
    address_line_1 = models.CharField(max_length=255, blank=True, null=True)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    # Geographical coordinates
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    # GitHub and GSOC fields
    github_org = models.CharField(max_length=255, blank=True, null=True)
    gsoc_years = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            original_slug = self.slug
            counter = 1
            while Organization.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class JoinRequest(models.Model):
    team = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_accepted = models.BooleanField(default=False)

class Job(models.Model):
    JOB_TYPE_CHOICES = [
        ("full-time", "Full Time"),
        ("part-time", "Part Time"),
        ("contract", "Contract"),
        ("internship", "Internship"),
        ("freelance", "Freelance"),
    ]
    JOB_STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("paused", "Paused"),
        ("closed", "Closed"),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="jobs")
    title = models.CharField(max_length=255)
    description = models.TextField()
    requirements = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, default="full-time")
    salary_range = models.CharField(max_length=100, blank=True, null=True)
    is_public = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=JOB_STATUS_CHOICES, default="draft")
    expires_at = models.DateTimeField(blank=True, null=True)
    application_email = models.EmailField(blank=True, null=True)
    application_url = models.URLField(blank=True, null=True)
    application_instructions = models.TextField(blank=True, null=True)
    posted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "is_public", "status"], name="job_org_pub_status_idx"),
        ]

    def __str__(self):
        return f"{self.title} at {self.organization.name}"

class Domain(models.Model):
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.CASCADE)
    managers = models.ManyToManyField(User, related_name="user_domains", blank=True)
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
    tags = models.ManyToManyField(Tag, blank=True)
    is_active = models.BooleanField(default=True)
    has_security_txt = models.BooleanField(default=False)
    security_txt_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["organization"], name="domain_org_idx")]

    def __str__(self):
        return self.name

class TrademarkOwner(models.Model):
    name = models.CharField(max_length=255)
    address1 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

class Trademark(models.Model):
    keyword = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    owners = models.ManyToManyField(TrademarkOwner, related_name="trademarks")
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.CASCADE, related_name="trademarks")

    def __str__(self):
        return self.keyword

class Hunt(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    name = models.CharField(max_length=25)
    description = MDTextField(null=True, blank=True)
    url = models.URLField()
    prize = models.IntegerField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

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
        (8, "Trademark Squatting"),
    )
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    team_members = models.ManyToManyField(User, related_name="reportmembers", blank=True)
    hunt = models.ForeignKey(Hunt, null=True, blank=True, on_delete=models.CASCADE)
    domain = models.ForeignKey(Domain, null=True, blank=True, on_delete=models.CASCADE)
    url = models.URLField()
    description = models.TextField()
    markdown_description = models.TextField(null=True, blank=True)
    

    label = models.PositiveSmallIntegerField(choices=labels, default=0)
    views = models.IntegerField(null=True, blank=True)
    verified = models.BooleanField(default=False)
    score = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, default="open", null=True, blank=True)
    user_agent = models.CharField(max_length=255, default="", null=True, blank=True)
    ocr = models.TextField(default="", null=True, blank=True)
    screenshot = models.ImageField(upload_to="screenshots", null=True, blank=True, validators=[validate_image])
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    rewarded = models.PositiveIntegerField(default=0)
    cve_id = models.CharField(max_length=16, null=True, blank=True)
    cve_score = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    comments = GenericRelation("comments.Comment")

    class Meta:
        ordering = ["-created"]
        indexes = [models.Index(fields=["domain", "status"], name="issue_domain_status_idx")]

    def __str__(self):
        return self.description

# --- Image Handling Receivers ---

def is_using_gcs():
    if hasattr(settings, "STORAGES"):
        backend = settings.STORAGES.get("default", {}).get("BACKEND", "")
    else:
        backend = getattr(settings, "DEFAULT_FILE_STORAGE", "")
    return backend == "storages.backends.gcloud.GoogleCloudStorage"

@receiver(post_delete, sender=Issue)
def delete_image_on_issue_delete(sender, instance, **kwargs):
    if instance.screenshot:
        if is_using_gcs():
            client = storage.Client()
            bucket = client.bucket(settings.GS_BUCKET_NAME)
            blob = bucket.blob(instance.screenshot.name)
            try:
                blob.delete()
            except NotFound:
                pass
        else:
            instance.screenshot.delete(save=False)

class IssueScreenshot(models.Model):
    image = models.ImageField(upload_to="screenshots", validators=[validate_image])
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="screenshots")
    created = models.DateTimeField(auto_now_add=True)
 
