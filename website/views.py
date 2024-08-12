import base64
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import deque
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse, urlsplit, urlunparse

import humanize
import requests
import requests.exceptions
import six
import stripe
import tweepy

# from django_cron import CronJobBase, Schedule
from allauth.account.models import EmailAddress
from allauth.account.signals import user_logged_in, user_signed_up
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from bs4 import BeautifulSoup
from dj_rest_auth.registration.views import SocialConnectView, SocialLoginView
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core import serializers
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.core.validators import URLValidator
from django.db.models import Count, Prefetch, Q, Sum
from django.db.models.functions import ExtractMonth
from django.db.transaction import atomic
from django.dispatch import receiver
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotFound,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.views.generic import DetailView, ListView, TemplateView, View
from django.views.generic.edit import CreateView
from PIL import Image, ImageDraw, ImageFont
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import api_view
from rest_framework.response import Response
from user_agents import parse

from blt import settings
from comments.models import Comment
from website.models import (
    IP,
    Bid,
    ChatBotLog,
    Company,
    CompanyAdmin,
    ContributorStats,
    Domain,
    Hunt,
    InviteFriend,
    Issue,
    IssueScreenshot,
    Monitor,
    Payment,
    Points,
    Project,
    Subscription,
    Suggestion,
    SuggestionVotes,
    UserProfile,
    Wallet,
    Winner,
)

from .bot import conversation_chain, is_api_key_valid, load_vector_store
from .forms import (
    CaptchaForm,
    GitHubURLForm,
    HuntForm,
    MonitorForm,
    UserDeleteForm,
    UserProfileForm,
)

WHITELISTED_IMAGE_TYPES = {
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "png": "image/png",
}

import os

import requests
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.cache import cache
from django.shortcuts import redirect, render
from dotenv import load_dotenv
from PIL import Image
from requests.auth import HTTPBasicAuth
from sendgrid import SendGridAPIClient

from .bitcoin_utils import create_bacon_token
from .forms import UserProfileForm
from .models import BaconToken, Contribution, Tag, UserProfile

# Load environment variables
load_dotenv()


@login_required
def profile_edit(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            return redirect("profile", slug=request.user.username)
    else:
        form = UserProfileForm(instance=user_profile)

    return render(request, "profile_edit.html", {"form": form})


def add_domain_to_company(request):
    if request.method == "POST":
        domain = request.POST.get("domain")
        domain = Domain.objects.get(id=domain)
        company_name = request.POST.get("company")
        company = Company.objects.filter(name=company_name).first()

        if not company:
            response = requests.get(domain.url)
            soup = BeautifulSoup(response.text, "html.parser")
            if company_name in soup.get_text():
                company = Company.objects.create(name=company_name)
                domain.company = company
                domain.save()
                messages.success(request, "Organization added successfully")
                # back to the domain detail page
                return redirect("domain", slug=domain.url)
            else:
                messages.error(request, "Organization not found in the domain")
                return redirect("domain", slug=domain.url)
        else:
            domain.company = company
            domain.save()
            messages.success(request, "Organization added successfully")
            # back to the domain detail page
            return redirect("domain", slug=domain.url)
    else:
        return redirect("index")


def check_status(request):
    # Check if the status is already cached
    status = cache.get("service_status")

    if not status:
        # Initialize the status dictionary
        status = {
            "bitcoin": False,
            "bitcoin_block": None,
            "sendgrid": False,
            "github": False,
        }

        # Check Bitcoin Core Node Status
        bitcoin_rpc_user = os.getenv("BITCOIN_RPC_USER")
        bitcoin_rpc_password = os.getenv("BITCOIN_RPC_PASSWORD")
        bitcoin_rpc_host = os.getenv("BITCOIN_RPC_HOST", "127.0.0.1")
        bitcoin_rpc_port = os.getenv("BITCOIN_RPC_PORT", "8332")

        try:
            response = requests.post(
                f"http://{bitcoin_rpc_host}:{bitcoin_rpc_port}",
                json={
                    "jsonrpc": "1.0",
                    "id": "curltest",
                    "method": "getblockchaininfo",
                    "params": [],
                },
                auth=HTTPBasicAuth(bitcoin_rpc_user, bitcoin_rpc_password),
            )
            if response.status_code == 200:
                data = response.json().get("result", {})
                status["bitcoin"] = True
                status["bitcoin_block"] = data.get("blocks", None)
        except Exception as e:
            print(f"Bitcoin Core Node Error: {e}")

        try:
            sg = SendGridAPIClient(os.getenv("SENDGRID_PASSWORD"))
            response = sg.client.api_keys._(sg.api_key).get()
            if response.status_code == 200:
                status["sendgrid"] = True
        except Exception as e:
            print(f"SendGrid Error: {e}")

        # Check GitHub Repo Access
        github_token = os.getenv("GITHUB_ACCESS_TOKEN")

        if not github_token:
            print(
                "GitHub Access Token not found. Please set the GITHUB_ACCESS_TOKEN environment variable."
            )
            status["github"] = False
        else:
            try:
                headers = {"Authorization": f"token {github_token}"}
                response = requests.get("https://api.github.com/user/repos", headers=headers)

                print(f"Response Status Code: {response.status_code}")
                print(f"Response Content: {response.json()}")

                if response.status_code == 200:
                    status["github"] = True
                    print("GitHub API token has repository access.")
                else:
                    status["github"] = False
                    print(
                        f"GitHub API token check failed with status code {response.status_code}: {response.json().get('message', 'No message provided')}"
                    )

            except requests.exceptions.RequestException as e:
                status["github"] = False
                print(f"GitHub API Error: {e}")

        # Cache the status for 1 minute (60 seconds)
        cache.set("service_status", status, timeout=60)

    # Pass the status to the template
    return render(request, "status_page.html", {"status": status})


def admin_required(user):
    return user.is_superuser


@user_passes_test(admin_required)
def select_contribution(request):
    contributions = Contribution.objects.filter(status="closed").exclude(
        id__in=BaconToken.objects.values_list("contribution_id", flat=True)
    )
    return render(request, "select_contribution.html", {"contributions": contributions})


@user_passes_test(admin_required)
def distribute_bacon(request, contribution_id):
    contribution = Contribution.objects.get(id=contribution_id)
    if (
        contribution.status == "closed"
        and not BaconToken.objects.filter(contribution=contribution).exists()
    ):
        token = create_bacon_token(contribution.user, contribution)
        if token:
            messages.success(request, "Bacon distributed successfully")
            return redirect("contribution_detail", contribution_id=contribution.id)
        else:
            messages.error(request, "Failed to distribute bacon")
    contributions = Contribution.objects.filter(status="closed").exclude(
        id__in=BaconToken.objects.values_list("contribution_id", flat=True)
    )
    return render(request, "select_contribution.html", {"contributions": contributions})


def image_validator(img):
    try:
        filesize = img.file.size
    except:
        filesize = img.size

    extension = img.name.split(".")[-1]
    content_type = img.content_type
    megabyte_limit = 3.0
    if not extension or extension.lower() not in WHITELISTED_IMAGE_TYPES.keys():
        error = "Invalid image types"
        return error
    elif filesize > megabyte_limit * 1024 * 1024:
        error = "Max file size is %sMB" % str(megabyte_limit)
        return error

    elif content_type not in WHITELISTED_IMAGE_TYPES.values():
        error = "invalid image content-type"
        return error
    else:
        return True


def is_valid_https_url(url):
    validate = URLValidator(schemes=["https"])  # Only allow HTTPS URLs
    try:
        validate(url)
        return True
    except ValidationError:
        return False


def rebuild_safe_url(url):
    parsed_url = urlparse(url)
    # Rebuild the URL with scheme, netloc, and path only
    return urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, "", "", ""))


class ProjectDetailView(DetailView):
    model = Project


class ProjectListView(ListView):
    model = Project
    context_object_name = "projects"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = GitHubURLForm()
        return context

    def post(self, request, *args, **kwargs):
        form = GitHubURLForm(request.POST)
        if form.is_valid():
            github_url = form.cleaned_data["github_url"]
            api_url = github_url.replace("github.com", "api.github.com/repos")
            response = requests.get(api_url)
            if response.status_code == 200:
                data = response.json()
                project, created = Project.objects.get_or_create(
                    github_url=github_url,
                    defaults={
                        "name": data["name"],
                        "slug": data["name"].lower(),
                        "description": data["description"],
                        "wiki_url": data["html_url"],
                        "homepage_url": data.get("homepage", ""),
                        "logo_url": data["owner"]["avatar_url"],
                    },
                )
                if created:
                    messages.success(request, "Project added successfully.")
                else:
                    messages.info(request, "Project already exists.")
            else:
                messages.error(request, "Failed to fetch project from GitHub.")
            return redirect("project_list")
        context = self.get_context_data()
        context["form"] = form
        return self.render_to_response(context)


# # @cache_page(60 * 60 * 24)
# def index(request, template="index.html"):
#     try:
#         domains = random.sample(Domain.objects.all(), 3)
#     except:
#         domains = None
#     try:
#         if not EmailAddress.objects.get(email=request.user.email).verified:
#             messages.error(request, "Please verify your email address")
#     except:
#         pass

#     latest_hunts_filter = request.GET.get("latest_hunts", None)

#     bug_count = Issue.objects.all().count()
#     user_count = User.objects.all().count()
#     hunt_count = Hunt.objects.all().count()
#     domain_count = Domain.objects.all().count()

#     captcha_form = CaptchaForm()

#     wallet = None
#     if request.user.is_authenticated:
#         wallet, created = Wallet.objects.get_or_create(user=request.user)

#     activity_screenshots = {}
#     for activity in Issue.objects.all():
#         activity_screenshots[activity] = IssueScreenshot.objects.filter(issue=activity).first()

#     top_companies = (
#         Issue.objects.values("domain__name")
#         .annotate(count=Count("domain__name"))
#         .order_by("-count")[:10]
#     )
#     top_testers = (
#         Issue.objects.values("user__id", "user__username")
#         .filter(user__isnull=False)
#         .annotate(count=Count("user__username"))
#         .order_by("-count")[:10]
#     )

#     if request.user.is_anonymous:
#         activities = Issue.objects.exclude(Q(is_hidden=True))[0:10]
#     else:
#         activities = Issue.objects.exclude(Q(is_hidden=True) & ~Q(user_id=request.user.id))[0:10]

#     top_hunts = Hunt.objects.values(
#         "id",
#         "name",
#         "url",
#         "logo",
#         "starts_on",
#         "starts_on__day",
#         "starts_on__month",
#         "starts_on__year",
#         "end_on",
#         "end_on__day",
#         "end_on__month",
#         "end_on__year",
#     ).annotate(total_prize=Sum("huntprize__value"))

#     if latest_hunts_filter is not None:
#         top_hunts = top_hunts.filter(result_published=True).order_by("-created")[:3]
#     else:
#         top_hunts = top_hunts.filter(is_published=True, result_published=False).order_by(
#             "-created"
#         )[:3]

#     context = {
#         "server_url": request.build_absolute_uri("/"),
#         "activities": activities,
#         "domains": domains,
#         "hunts": Hunt.objects.exclude(txn_id__isnull=True)[:4],
#         "leaderboard": User.objects.filter(
#             points__created__month=datetime.now().month,
#             points__created__year=datetime.now().year,
#         )
#         .annotate(total_score=Sum("points__score"))
#         .order_by("-total_score")[:10],
#         "bug_count": bug_count,
#         "user_count": user_count,
#         "hunt_count": hunt_count,
#         "domain_count": domain_count,
#         "wallet": wallet,
#         "captcha_form": captcha_form,
#         "activity_screenshots": activity_screenshots,
#         "top_companies": top_companies,
#         "top_testers": top_testers,
#         "top_hunts": top_hunts,
#         "ended_hunts": False if latest_hunts_filter is None else True,
#     }
#     return render(request, template, context)


def newhome(request, template="new_home.html"):
    if request.user.is_authenticated:
        email_record = EmailAddress.objects.filter(email=request.user.email).first()
        if email_record:
            if not email_record.verified:
                messages.error(request, "Please verify your email address.")
        else:
            messages.error(request, "No email associated with your account. Please add an email.")

    # Fetch and paginate issues
    issues_queryset = Issue.objects.exclude(Q(is_hidden=True) & ~Q(user_id=request.user.id))
    paginator = Paginator(issues_queryset, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Prefetch related screenshots only for issues on the current page
    issues_with_screenshots = page_obj.object_list.prefetch_related(
        Prefetch("screenshots", queryset=IssueScreenshot.objects.all())
    )
    bugs_screenshots = {issue: issue.screenshots.all()[:3] for issue in issues_with_screenshots}

    # Filter leaderboard for current month and year
    current_time = now()
    leaderboard = User.objects.filter(
        points__created__month=current_time.month, points__created__year=current_time.year
    )

    context = {
        "bugs": page_obj,
        "bugs_screenshots": bugs_screenshots,
        "leaderboard": leaderboard,
    }
    return render(request, template, context)


def is_safe_url(url, allowed_hosts, allowed_paths=None):
    if not is_valid_https_url(url):
        return False

    parsed_url = urlparse(url)

    if parsed_url.netloc not in allowed_hosts:
        return False

    if allowed_paths and parsed_url.path not in allowed_paths:
        return False

    return True


def safe_redirect(url, allowed_hosts, allowed_paths=None):
    if is_safe_url(url, allowed_hosts, allowed_paths):
        safe_url = rebuild_safe_url(url)
        return redirect(safe_url)
    else:
        return HttpResponseBadRequest("Invalid redirection URL.")


def github_callback(request):
    ALLOWED_HOSTS = ["github.com"]
    params = urllib.parse.urlencode(request.GET)
    url = f"{settings.CALLBACK_URL_FOR_GITHUB}?{params}"

    return safe_redirect(url, ALLOWED_HOSTS)


def google_callback(request):
    ALLOWED_HOSTS = ["accounts.google.com"]
    params = urllib.parse.urlencode(request.GET)
    url = f"{settings.CALLBACK_URL_FOR_GOOGLE}?{params}"

    return safe_redirect(url, ALLOWED_HOSTS)


def facebook_callback(request):
    ALLOWED_HOSTS = ["www.facebook.com"]
    params = urllib.parse.urlencode(request.GET)
    url = f"{settings.CALLBACK_URL_FOR_FACEBOOK}?{params}"

    return safe_redirect(url, ALLOWED_HOSTS)


class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        # use the same callback url as defined in your Facebook app, this url
        # must be absolute:
        return self.request.build_absolute_uri(reverse("facebook_callback"))


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        # use the same callback url as defined in your Google app, this url
        # must be absolute:
        return self.request.build_absolute_uri(reverse("google_callback"))


class GithubLogin(SocialLoginView):
    adapter_class = GitHubOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        # use the same callback url as defined in your GitHub app, this url
        # must be absolute:
        return self.request.build_absolute_uri(reverse("github_callback"))


class FacebookConnect(SocialConnectView):
    adapter_class = FacebookOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        # use the same callback url as defined in your Facebook app, this url
        # must be absolute:
        return self.request.build_absolute_uri(reverse("facebook_callback"))


class GithubConnect(SocialConnectView):
    adapter_class = GitHubOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        # use the same callback url as defined in your GitHub app, this url
        # must be absolute:
        return self.request.build_absolute_uri(reverse("github_callback"))


class GoogleConnect(SocialConnectView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        # use the same callback url as defined in your Google app, this url
        # must be absolute:
        return self.request.build_absolute_uri(reverse("google_callback"))


@login_required(login_url="/accounts/login")
def company_dashboard(request, template="index_company.html"):
    try:
        company_admin = CompanyAdmin.objects.get(user=request.user)
        if not company_admin.is_active:
            return HttpResponseRedirect("/")
        hunts = Hunt.objects.filter(is_published=True, domain=company_admin.domain)
        upcoming_hunt = []
        ongoing_hunt = []
        previous_hunt = []
        for hunt in hunts:
            if ((hunt.starts_on - datetime.now(timezone.utc)).total_seconds()) > 0:
                upcoming_hunt.append(hunt)
            elif ((hunt.end_on - datetime.now(timezone.utc)).total_seconds()) < 0:
                previous_hunt.append(hunt)
            else:
                ongoing_hunt.append(hunt)
        context = {
            "upcoming_hunts": upcoming_hunt,
            "ongoing_hunt": ongoing_hunt,
            "previous_hunt": previous_hunt,
        }
        return render(request, template, context)
    except:
        return redirect("/")


@login_required(login_url="/accounts/login")
def admin_company_dashboard(request, template="admin_dashboard_company.html"):
    user = request.user
    if user.is_superuser:
        if not user.is_active:
            return HttpResponseRedirect("/")
        company = Company.objects.all()
        context = {"companys": company}
        return render(request, template, context)
    else:
        return redirect("/")


@login_required(login_url="/accounts/login")
def admin_company_dashboard_detail(request, pk, template="admin_dashboard_company_detail.html"):
    user = request.user
    if user.is_superuser:
        if not user.is_active:
            return HttpResponseRedirect("/")
        company = get_object_or_404(Company, pk=pk)
        return render(request, template, {"company": company})
    else:
        return redirect("/")


@login_required(login_url="/accounts/login")
def admin_dashboard(request, template="admin_home.html"):
    user = request.user
    if user.is_superuser:
        if not user.is_active:
            return HttpResponseRedirect("/")
        return render(request, template)
    else:
        return redirect("/")


@login_required(login_url="/accounts/login")
def user_dashboard(request, template="index_user.html"):
    hunts = Hunt.objects.filter(is_published=True)
    upcoming_hunt = []
    ongoing_hunt = []
    previous_hunt = []
    for hunt in hunts:
        if ((hunt.starts_on - datetime.now(timezone.utc)).total_seconds()) > 0:
            upcoming_hunt.append(hunt)
        elif ((hunt.end_on - datetime.now(timezone.utc)).total_seconds()) < 0:
            previous_hunt.append(hunt)
        else:
            ongoing_hunt.append(hunt)
    context = {
        "upcoming_hunts": upcoming_hunt,
        "ongoing_hunt": ongoing_hunt,
        "previous_hunt": previous_hunt,
    }
    return render(request, template, context)


def find_key(request, token):
    if token == os.environ.get("ACME_TOKEN"):
        return HttpResponse(os.environ.get("ACME_KEY"))
    for k, v in list(os.environ.items()):
        if v == token and k.startswith("ACME_TOKEN_"):
            n = k.replace("ACME_TOKEN_", "")
            return HttpResponse(os.environ.get("ACME_KEY_%s" % n))
    raise Http404("Token or key does not exist")


class UserDeleteView(LoginRequiredMixin, View):
    """
    Deletes the currently signed-in user and all associated data.
    """

    def get(self, request, *args, **kwargs):
        form = UserDeleteForm()
        return render(request, "user_deletion.html", {"form": form})

    def post(self, request, *args, **kwargs):
        form = UserDeleteForm(request.POST)
        if form.is_valid():
            user = request.user
            logout(request)
            user.delete()
            messages.success(request, "Account successfully deleted")
            return redirect(reverse("index"))
        return render(request, "user_deletion.html", {"form": form})


class IssueBaseCreate(object):
    def form_valid(self, form):
        print(
            "processing form_valid IssueBaseCreate for ip address: ",
            get_client_ip(self.request),
        )
        score = 3
        obj = form.save(commit=False)
        obj.user = self.request.user
        domain, created = Domain.objects.get_or_create(
            name=obj.domain_name.replace("www.", ""),
            defaults={"url": "http://" + obj.domain_name.replace("www.", "")},
        )
        obj.domain = domain
        if self.request.POST.get("screenshot-hash"):
            filename = self.request.POST.get("screenshot-hash")
            extension = filename.split(".")[-1]
            self.request.POST["screenshot-hash"] = (
                filename[:99] + str(uuid.uuid4()) + "." + extension
            )

            reopen = default_storage.open(
                "uploads\/" + self.request.POST.get("screenshot-hash") + ".png", "rb"
            )
            django_file = File(reopen)
            obj.screenshot.save(
                self.request.POST.get("screenshot-hash") + ".png",
                django_file,
                save=True,
            )

        obj.user_agent = self.request.META.get("HTTP_USER_AGENT")
        obj.save()
        p = Points.objects.create(user=self.request.user, issue=obj, score=score)

    def process_issue(self, user, obj, created, domain, tokenauth=False, score=3):
        print("processing process_issue for ip address: ", get_client_ip(self.request))
        p = Points.objects.create(user=user, issue=obj, score=score)
        messages.success(self.request, "Bug added ! +" + str(score))
        # tweet feature
        try:
            auth = tweepy.Client(
                settings.BEARER_TOKEN,
                settings.APP_KEY,
                settings.APP_KEY_SECRET,
                settings.ACCESS_TOKEN,
                settings.ACCESS_TOKEN_SECRET,
            )

            blt_url = "https://%s/issue/%d" % (
                settings.DOMAIN_NAME,
                obj.id,
            )
            domain_name = domain.get_name
            twitter_account = (
                "@" + domain.get_or_set_x_url(domain_name) + " "
                if domain.get_or_set_x_url(domain_name)
                else ""
            )

            issue_title = obj.description + " " if not obj.is_hidden else ""

            message = "%sAn Issue %shas been reported on %s by %s on %s.\n Have look here %s" % (
                twitter_account,
                issue_title,
                domain_name,
                user.username,
                settings.PROJECT_NAME,
                blt_url,
            )

            auth.create_tweet(text=message)

        except (
            TypeError,
            tweepy.errors.HTTPException,
            tweepy.errors.TweepyException,
        ) as e:
            print(e)

        if created:
            try:
                email_to = get_email_from_domain(domain)
            except:
                email_to = "support@" + domain.name

            domain.email = email_to
            domain.save()

            name = email_to.split("@")[0]

            msg_plain = render_to_string(
                "email/domain_added.txt", {"domain": domain.name, "name": name}
            )
            msg_html = render_to_string(
                "email/domain_added.txt", {"domain": domain.name, "name": name}
            )

            send_mail(
                domain.name + " added to " + settings.PROJECT_NAME,
                msg_plain,
                settings.EMAIL_TO_STRING,
                [email_to],
                html_message=msg_html,
            )

        else:
            email_to = domain.email
            try:
                name = email_to.split("@")[0]
            except:
                email_to = "support@" + domain.name
                name = "support"
                domain.email = email_to
                domain.save()
            if not tokenauth:
                msg_plain = render_to_string(
                    "email/bug_added.txt",
                    {
                        "domain": domain.name,
                        "name": name,
                        "username": self.request.user,
                        "id": obj.id,
                        "description": obj.description,
                        "label": obj.get_label_display,
                    },
                )
                msg_html = render_to_string(
                    "email/bug_added.txt",
                    {
                        "domain": domain.name,
                        "name": name,
                        "username": self.request.user,
                        "id": obj.id,
                        "description": obj.description,
                        "label": obj.get_label_display,
                    },
                )
            else:
                msg_plain = render_to_string(
                    "email/bug_added.txt",
                    {
                        "domain": domain.name,
                        "name": name,
                        "username": user,
                        "id": obj.id,
                        "description": obj.description,
                        "label": obj.get_label_display,
                    },
                )
                msg_html = render_to_string(
                    "email/bug_added.txt",
                    {
                        "domain": domain.name,
                        "name": name,
                        "username": user,
                        "id": obj.id,
                        "description": obj.description,
                        "label": obj.get_label_display,
                    },
                )
            send_mail(
                "Bug found on " + domain.name,
                msg_plain,
                settings.EMAIL_TO_STRING,
                [email_to],
                html_message=msg_html,
            )
        return HttpResponseRedirect("/")


def get_client_ip(request):
    """Extract the client's IP address from the request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


class IssueCreate(IssueBaseCreate, CreateView):
    model = Issue
    fields = ["url", "description", "domain", "label", "markdown_description", "cve_id"]
    template_name = "report.html"

    def get_initial(self):
        print("processing post for ip address: ", get_client_ip(self.request))
        try:
            json_data = json.loads(self.request.body)
            if not self.request.GET._mutable:
                self.request.POST._mutable = True
            self.request.POST["url"] = json_data["url"]
            self.request.POST["description"] = json_data["description"]
            self.request.POST["markdown_description"] = json_data["markdown_description"]
            self.request.POST["file"] = json_data["file"]
            self.request.POST["label"] = json_data["label"]
            self.request.POST["token"] = json_data["token"]
            self.request.POST["type"] = json_data["type"]
            self.request.POST["cve_id"] = json_data["cve_id"]
            self.request.POST["cve_score"] = json_data["cve_score"]

            if self.request.POST.get("file"):
                if isinstance(self.request.POST.get("file"), six.string_types):
                    import imghdr

                    # Check if the base64 string is in the "data:" format
                    data = (
                        "data:image/"
                        + self.request.POST.get("type")
                        + ";base64,"
                        + self.request.POST.get("file")
                    )
                    data = data.replace(" ", "")
                    data += "=" * ((4 - len(data) % 4) % 4)
                    if "data:" in data and ";base64," in data:
                        # Break out the header from the base64 content
                        header, data = data.split(";base64,")

                    # Try to decode the file. Return validation error if it fails.
                    try:
                        decoded_file = base64.b64decode(data)
                    except TypeError:
                        TypeError("invalid_image")

                    # Generate file name:
                    file_name = str(uuid.uuid4())[:12]  # 12 characters are more than enough.
                    # Get the file name extension:
                    extension = imghdr.what(file_name, decoded_file)
                    extension = "jpg" if extension == "jpeg" else extension
                    file_extension = extension

                    complete_file_name = "%s.%s" % (
                        file_name,
                        file_extension,
                    )

                    self.request.FILES["screenshot"] = ContentFile(
                        decoded_file, name=complete_file_name
                    )
        except:
            tokenauth = False
        initial = super(IssueCreate, self).get_initial()
        if self.request.POST.get("screenshot-hash"):
            initial["screenshot"] = "uploads\/" + self.request.POST.get("screenshot-hash") + ".png"
        return initial

    # def get(self, request, *args, **kwargs):
    #     print("processing get for ip address: ", get_client_ip(request))

    #     captcha_form = CaptchaForm()
    #     return render(
    #         request,
    #         self.template_name,
    #         {"form": self.get_form(), "captcha_form": captcha_form},
    #     )

    def post(self, request, *args, **kwargs):
        print("processing post for ip address: ", get_client_ip(request))
        # resolve domain
        url = request.POST.get("url").replace("www.", "").replace("https://", "")

        request.POST._mutable = True
        request.POST.update(url=url)  # only domain.com will be stored in db
        request.POST._mutable = False

        # disable domain search on testing
        if not settings.IS_TEST:
            try:
                if settings.DOMAIN_NAME in url:
                    print("Web site exists")

                # skip domain validation check if bugreport server down
                elif request.POST["label"] == "7":
                    pass

                else:
                    full_url = "https://" + url
                    if is_valid_https_url(full_url):
                        safe_url = rebuild_safe_url(full_url)
                        try:
                            response = requests.get(safe_url, timeout=5)
                            if response.status_code == 200:
                                print("Web site exists")
                            else:
                                raise Exception
                        except Exception:
                            raise Exception
                    else:
                        raise Exception
            except:
                # TODO: it could be that the site is down so we can consider logging this differently
                messages.error(request, "Domain does not exist")

                captcha_form = CaptchaForm(request.POST)
                return render(
                    self.request,
                    "report.html",
                    {"form": self.get_form(), "captcha_form": captcha_form},
                )
        # if not request.FILES.get("screenshots"):
        #     messages.error(request, "Screenshot is required")
        #     captcha_form = CaptchaForm(request.POST)
        #     return render(
        #         self.request,
        #         "report.html",
        #         {"form": self.get_form(), "captcha_form": captcha_form},
        #     )

        screenshot = request.FILES.get("screenshots")
        if not screenshot:
            messages.error(request, "Screenshot is required")
            captcha_form = CaptchaForm(request.POST)
            return render(
                request,
                "report.html",
                {"form": self.get_form(), "captcha_form": captcha_form},
            )

        try:
            # Attempt to open the image to validate if it's a correct format
            img = Image.open(screenshot)
            img.verify()  # Verify that it is, in fact, an image
        except (IOError, ValueError):
            messages.error(request, "Invalid image file.")
            captcha_form = CaptchaForm(request.POST)
            return render(
                request,
                "report.html",
                {"form": self.get_form(), "captcha_form": captcha_form},
            )

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        print(
            "processing form_valid in IssueCreate for ip address: ",
            get_client_ip(self.request),
        )
        reporter_ip = get_client_ip(self.request)
        form.instance.reporter_ip_address = reporter_ip

        # implement rate limit
        limit = 50 if self.request.user.is_authenticated else 30
        today = now().date()
        recent_issues_count = Issue.objects.filter(
            reporter_ip_address=reporter_ip, created__date=today
        ).count()

        if recent_issues_count >= limit:
            messages.error(self.request, "You have reached your issue creation limit for today.")
            return render(self.request, "report.html", {"form": self.get_form()})
        form.instance.reporter_ip_address = reporter_ip

        @atomic
        def create_issue(self, form):
            tokenauth = False
            obj = form.save(commit=False)
            if self.request.user.is_authenticated:
                obj.user = self.request.user
            if not self.request.user.is_authenticated:
                for token in Token.objects.all():
                    if self.request.POST.get("token") == token.key:
                        obj.user = User.objects.get(id=token.user_id)
                        tokenauth = True

            captcha_form = CaptchaForm(self.request.POST)
            if not captcha_form.is_valid() and not settings.TESTING:
                messages.error(self.request, "Invalid Captcha!")

                return render(
                    self.request,
                    "report.html",
                    {"form": self.get_form(), "captcha_form": captcha_form},
                )
            parsed_url = urlparse(obj.url)
            clean_domain = parsed_url.netloc
            domain = Domain.objects.filter(url=clean_domain).first()

            domain_exists = False if domain is None else True

            if not domain_exists:
                domain = Domain.objects.filter(name=clean_domain).first()
                if domain is None:
                    domain = Domain.objects.create(name=clean_domain, url=clean_domain)
                    domain.save()

            hunt = self.request.POST.get("hunt", None)
            if hunt is not None and hunt != "None":
                hunt = Hunt.objects.filter(id=hunt).first()
                obj.hunt = hunt

            obj.domain = domain
            # obj.is_hidden = bool(self.request.POST.get("private", False))
            obj.cve_score = obj.get_cve_score()
            obj.save()

            if not domain_exists and (self.request.user.is_authenticated or tokenauth):
                p = Points.objects.create(user=self.request.user, domain=domain, score=1)
                messages.success(self.request, "Domain added! + 1")

            if self.request.POST.get("screenshot-hash"):
                reopen = default_storage.open(
                    "uploads\/" + self.request.POST.get("screenshot-hash") + ".png",
                    "rb",
                )
                django_file = File(reopen)
                obj.screenshot.save(
                    self.request.POST.get("screenshot-hash") + ".png",
                    django_file,
                    save=True,
                )
            obj.user_agent = self.request.META.get("HTTP_USER_AGENT")

            if len(self.request.FILES.getlist("screenshots")) > 5:
                messages.error(self.request, "Max limit of 5 images!")
                obj.delete()
                return render(
                    self.request,
                    "report.html",
                    {"form": self.get_form(), "captcha_form": captcha_form},
                )
            for screenshot in self.request.FILES.getlist("screenshots"):
                img_valid = image_validator(screenshot)
                if img_valid is True:
                    filename = screenshot.name
                    extension = filename.split(".")[-1]
                    screenshot.name = (filename[:10] + str(uuid.uuid4()))[:40] + "." + extension
                    default_storage.save(f"screenshots/{screenshot.name}", screenshot)
                    IssueScreenshot.objects.create(
                        image=f"screenshots/{screenshot.name}", issue=obj
                    )
                else:
                    messages.error(self.request, img_valid)
                    return render(
                        self.request,
                        "report.html",
                        {"form": self.get_form(), "captcha_form": captcha_form},
                    )

            obj_screenshots = IssueScreenshot.objects.filter(issue_id=obj.id)
            screenshot_text = ""
            for screenshot in obj_screenshots:
                screenshot_text += "![0](" + screenshot.image.url + ") "

            team_members_id = [
                member["id"]
                for member in User.objects.values("id").filter(
                    email__in=self.request.POST.getlist("team_members")
                )
            ] + [self.request.user.id]
            for member_id in team_members_id:
                if member_id is None:
                    team_members_id.remove(member_id)  # remove None values if user not exists
            obj.team_members.set(team_members_id)

            obj.save()

            if self.request.user.is_authenticated:
                total_issues = Issue.objects.filter(user=self.request.user).count()
                user_prof = UserProfile.objects.get(user=self.request.user)
                if total_issues <= 10:
                    user_prof.title = 1
                elif total_issues <= 50:
                    user_prof.title = 2
                elif total_issues <= 200:
                    user_prof.title = 3
                else:
                    user_prof.title = 4

                user_prof.save()

            if tokenauth:
                total_issues = Issue.objects.filter(user=User.objects.get(id=token.user_id)).count()
                user_prof = UserProfile.objects.get(user=User.objects.get(id=token.user_id))
                if total_issues <= 10:
                    user_prof.title = 1
                elif total_issues <= 50:
                    user_prof.title = 2
                elif total_issues <= 200:
                    user_prof.title = 3
                else:
                    user_prof.title = 4

                user_prof.save()

            redirect_url = "/report"

            if domain.github and os.environ.get("GITHUB_ACCESS_TOKEN"):
                import json

                import requests
                from giturlparse import parse

                github_url = domain.github.replace("https", "git").replace("http", "git") + ".git"
                p = parse(github_url)

                url = "https://api.github.com/repos/%s/%s/issues" % (p.owner, p.repo)

                if not obj.user:
                    the_user = "Anonymous"
                else:
                    the_user = obj.user
                issue = {
                    "title": obj.description,
                    "body": obj.markdown_description
                    + "\n\n"
                    + screenshot_text
                    + "https://"
                    + settings.FQDN
                    + "/issue/"
                    + str(obj.id)
                    + " found by "
                    + str(the_user)
                    + " at url: "
                    + obj.url,
                    "labels": ["bug", settings.PROJECT_NAME_LOWER],
                }
                r = requests.post(
                    url,
                    json.dumps(issue),
                    headers={"Authorization": "token " + os.environ.get("GITHUB_ACCESS_TOKEN")},
                )
                response = r.json()
                try:
                    obj.github_url = response["html_url"]
                except Exception as e:
                    send_mail(
                        "Error in github issue creation for "
                        + str(domain.name)
                        + ", check your github settings",
                        "Error in github issue creation, check your github settings\n"
                        + " your current settings are: "
                        + str(domain.github)
                        + " and the error is: "
                        + str(e),
                        settings.EMAIL_TO_STRING,
                        [domain.email],
                        fail_silently=True,
                    )
                    pass
                obj.save()

            if not (self.request.user.is_authenticated or tokenauth):
                self.request.session["issue"] = obj.id
                self.request.session["created"] = domain_exists
                self.request.session["domain"] = domain.id
                login_url = reverse("account_login")
                messages.success(self.request, "Bug added!")
                return HttpResponseRedirect("{}?next={}".format(login_url, redirect_url))

            if tokenauth:
                self.process_issue(
                    User.objects.get(id=token.user_id), obj, domain_exists, domain, True
                )
                return JsonResponse("Created", safe=False)
            else:
                self.process_issue(self.request.user, obj, domain_exists, domain)
                return HttpResponseRedirect(redirect_url + "/")

        return create_issue(self, form)

    def get_context_data(self, **kwargs):
        # if self.request is a get, clear out the form data
        if self.request.method == "GET":
            self.request.POST = {}
            self.request.GET = {}

        print("processing get_context_data for ip address: ", get_client_ip(self.request))
        context = super(IssueCreate, self).get_context_data(**kwargs)
        context["activities"] = Issue.objects.exclude(
            Q(is_hidden=True) & ~Q(user_id=self.request.user.id)
        )[0:10]
        context["captcha_form"] = CaptchaForm()
        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)
        context["leaderboard"] = (
            User.objects.filter(
                points__created__month=datetime.now().month,
                points__created__year=datetime.now().year,
            )
            .annotate(total_score=Sum("points__score"))
            .order_by("-total_score")[:10],
        )

        # automatically add specified hunt to dropdown of Bugreport
        report_on_hunt = self.request.GET.get("hunt", None)
        if report_on_hunt:
            context["hunts"] = Hunt.objects.values("id", "name").filter(
                id=report_on_hunt, is_published=True, result_published=False
            )
            context["report_on_hunt"] = True
        else:
            context["hunts"] = Hunt.objects.values("id", "name").filter(
                is_published=True, result_published=False
            )
            context["report_on_hunt"] = False

        context["top_domains"] = (
            Issue.objects.values("domain__name")
            .annotate(count=Count("domain__name"))
            .order_by("-count")[:30]
        )

        return context


class UploadCreate(View):
    template_name = "index.html"

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(UploadCreate, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = request.FILES.get("image")
        result = default_storage.save(
            "uploads\/" + self.kwargs["hash"] + ".png", ContentFile(data.read())
        )
        return JsonResponse({"status": result})


class InviteCreate(TemplateView):
    template_name = "invite.html"

    def post(self, request, *args, **kwargs):
        email = request.POST.get("email")
        exists = False
        domain = None
        if email:
            domain = email.split("@")[-1]
            try:
                full_url_domain = "https://" + domain + "/favicon.ico"
                if is_valid_https_url(full_url_domain):
                    safe_url = rebuild_safe_url(full_url_domain)
                    response = requests.get(safe_url, timeout=5)
                    if response.status_code == 200:
                        exists = "exists"
            except:
                pass
        context = {
            "exists": exists,
            "domain": domain,
            "email": email,
        }
        return render(request, "invite.html", context)


def profile(request):
    try:
        return redirect("/profile/" + request.user.username)
    except Exception:
        return redirect("/")


class UserProfileDetailView(DetailView):
    model = get_user_model()
    slug_field = "username"
    template_name = "profile.html"

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Http404:
            messages.error(self.request, "That user was not found.")
            return redirect("/")
        return super(UserProfileDetailView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        user = self.object
        context = super(UserProfileDetailView, self).get_context_data(**kwargs)
        context["my_score"] = list(
            Points.objects.filter(user=self.object).aggregate(total_score=Sum("score")).values()
        )[0]
        context["websites"] = (
            Domain.objects.filter(issue__user=self.object)
            .annotate(total=Count("issue"))
            .order_by("-total")
        )
        context["activities"] = Issue.objects.filter(user=self.object, hunt=None).exclude(
            Q(is_hidden=True) & ~Q(user_id=self.request.user.id)
        )[0:3]
        context["activity_screenshots"] = {}
        for activity in context["activities"]:
            context["activity_screenshots"][activity] = IssueScreenshot.objects.filter(
                issue=activity.pk
            ).first()
        context["profile_form"] = UserProfileForm()
        context["total_open"] = Issue.objects.filter(user=self.object, status="open").count()
        context["total_closed"] = Issue.objects.filter(user=self.object, status="closed").count()
        context["current_month"] = datetime.now().month
        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)
        context["graph"] = (
            Issue.objects.filter(user=self.object)
            .filter(
                created__month__gte=(datetime.now().month - 6),
                created__month__lte=datetime.now().month,
            )
            .annotate(month=ExtractMonth("created"))
            .values("month")
            .annotate(c=Count("id"))
            .order_by()
        )
        context["total_bugs"] = Issue.objects.filter(user=self.object, hunt=None).count()
        for i in range(0, 7):
            context["bug_type_" + str(i)] = Issue.objects.filter(
                user=self.object, hunt=None, label=str(i)
            )

        arr = []
        allFollowers = user.userprofile.follower.all()
        for userprofile in allFollowers:
            arr.append(User.objects.get(username=str(userprofile.user)))
        context["followers"] = arr

        arr = []
        allFollowing = user.userprofile.follows.all()
        for userprofile in allFollowing:
            arr.append(User.objects.get(username=str(userprofile.user)))
        context["following"] = arr

        context["followers_list"] = [
            str(prof.user.email) for prof in user.userprofile.follower.all()
        ]
        context["bookmarks"] = user.userprofile.issue_saved.all()
        # tags
        context["user_related_tags"] = (
            UserProfile.objects.filter(user=self.object).first().tags.all()
        )
        context["issues_hidden"] = "checked" if user.userprofile.issues_hidden else "!checked"
        return context

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
        if request.FILES.get("user_avatar") and form.is_valid():
            form.save()
        else:
            hide = True if request.POST.get("issues_hidden") == "on" else False
            user_issues = Issue.objects.filter(user=request.user)
            user_issues.update(is_hidden=hide)
            request.user.userprofile.issues_hidden = hide
            request.user.userprofile.save()
        return redirect(reverse("profile", kwargs={"slug": kwargs.get("slug")}))


class UserProfileDetailsView(DetailView):
    model = get_user_model()
    slug_field = "username"
    template_name = "dashboard_profile.html"

    def get(self, request, *args, **kwargs):
        try:
            if request.user.is_authenticated:
                self.object = self.get_object()
            else:
                return redirect("/accounts/login")
        except Http404:
            messages.error(self.request, "That user was not found.")
            return redirect("/")
        return super(UserProfileDetailsView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        user = self.object
        context = super(UserProfileDetailsView, self).get_context_data(**kwargs)
        context["my_score"] = list(
            Points.objects.filter(user=self.object).aggregate(total_score=Sum("score")).values()
        )[0]
        context["websites"] = (
            Domain.objects.filter(issue__user=self.object)
            .annotate(total=Count("issue"))
            .order_by("-total")
        )
        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)
        context["activities"] = Issue.objects.filter(user=self.object, hunt=None).exclude(
            Q(is_hidden=True) & ~Q(user_id=self.request.user.id)
        )[0:10]
        context["profile_form"] = UserProfileForm()
        context["total_open"] = Issue.objects.filter(user=self.object, status="open").count()
        context["user_details"] = UserProfile.objects.get(user=self.object)
        context["total_closed"] = Issue.objects.filter(user=self.object, status="closed").count()
        context["current_month"] = datetime.now().month
        context["graph"] = (
            Issue.objects.filter(user=self.object, hunt=None)
            .filter(
                created__month__gte=(datetime.now().month - 6),
                created__month__lte=datetime.now().month,
            )
            .annotate(month=ExtractMonth("created"))
            .values("month")
            .annotate(c=Count("id"))
            .order_by()
        )
        context["total_bugs"] = Issue.objects.filter(user=self.object).count()
        for i in range(0, 7):
            context["bug_type_" + str(i)] = Issue.objects.filter(
                user=self.object, hunt=None, label=str(i)
            ).exclude(Q(is_hidden=True) & ~Q(user_id=self.request.user.id))

        arr = []
        allFollowers = user.userprofile.follower.all()
        for userprofile in allFollowers:
            arr.append(User.objects.get(username=str(userprofile.user)))
        context["followers"] = arr

        arr = []
        allFollowing = user.userprofile.follows.all()
        for userprofile in allFollowing:
            arr.append(User.objects.get(username=str(userprofile.user)))
        context["following"] = arr

        context["followers_list"] = [
            str(prof.user.email) for prof in user.userprofile.follower.all()
        ]
        context["bookmarks"] = user.userprofile.issue_saved.all()
        return context

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
        if form.is_valid():
            form.save()
        return redirect(reverse("profile", kwargs={"slug": kwargs.get("slug")}))


def delete_issue(request, id):
    try:
        # TODO: Refactor this for a direct query instead of looping through all tokens
        for token in Token.objects.all():
            if request.POST["token"] == token.key:
                request.user = User.objects.get(id=token.user_id)
                tokenauth = True
    except:
        tokenauth = False
    issue = Issue.objects.get(id=id)
    if request.user.is_superuser or request.user == issue.user or tokenauth:
        screenshots = issue.screenshots.all()
        for screenshot in screenshots:
            screenshot.delete()
    if request.user.is_superuser or request.user == issue.user:
        issue.delete()
        messages.success(request, "Issue deleted")
    if tokenauth:
        return JsonResponse("Deleted", safe=False)
    else:
        return redirect("/")


def remove_user_from_issue(request, id):
    tokenauth = False
    try:
        for token in Token.objects.all():
            if request.POST["token"] == token.key:
                request.user = User.objects.get(id=token.user_id)
                tokenauth = True
    except:
        pass

    issue = Issue.objects.get(id=id)
    if request.user.is_superuser or request.user == issue.user:
        issue.remove_user()
        messages.success(request, "User removed from the issue")
        if tokenauth:
            return JsonResponse("User removed from the issue", safe=False)
        else:
            return safe_redirect(request)
    else:
        messages.error(request, "Permission denied")
        return safe_redirect(request)


class DomainDetailView(ListView):
    template_name = "domain.html"
    model = Issue

    def get_context_data(self, *args, **kwargs):
        context = super(DomainDetailView, self).get_context_data(*args, **kwargs)
        # remove any arguments from the slug
        self.kwargs["slug"] = self.kwargs["slug"].split("?")[0]
        domain = get_object_or_404(Domain, name=self.kwargs["slug"])
        context["domain"] = domain

        parsed_url = urlparse("http://" + self.kwargs["slug"])

        open_issue = (
            Issue.objects.filter(domain__name__contains=self.kwargs["slug"])
            .filter(status="open", hunt=None)
            .exclude(Q(is_hidden=True) & ~Q(user_id=self.request.user.id))
        )
        close_issue = (
            Issue.objects.filter(domain__name__contains=self.kwargs["slug"])
            .filter(status="closed", hunt=None)
            .exclude(Q(is_hidden=True) & ~Q(user_id=self.request.user.id))
        )
        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)

        context["name"] = parsed_url.netloc.split(".")[-2:][0].title()

        paginator = Paginator(open_issue, 10)
        page = self.request.GET.get("open")
        try:
            openissue_paginated = paginator.page(page)
        except PageNotAnInteger:
            openissue_paginated = paginator.page(1)
        except EmptyPage:
            openissue_paginated = paginator.page(paginator.num_pages)

        paginator = Paginator(close_issue, 10)
        page = self.request.GET.get("close")
        try:
            closeissue_paginated = paginator.page(page)
        except PageNotAnInteger:
            closeissue_paginated = paginator.page(1)
        except EmptyPage:
            closeissue_paginated = paginator.page(paginator.num_pages)

        context["opened_net"] = open_issue
        context["opened"] = openissue_paginated
        context["closed_net"] = close_issue
        context["closed"] = closeissue_paginated
        context["leaderboard"] = (
            User.objects.filter(issue__url__contains=self.kwargs["slug"])
            .annotate(total=Count("issue"))
            .order_by("-total")
        )
        context["current_month"] = datetime.now().month
        context["domain_graph"] = (
            Issue.objects.filter(domain=context["domain"], hunt=None)
            .filter(
                created__month__gte=(datetime.now().month - 6),
                created__month__lte=datetime.now().month,
            )
            .annotate(month=ExtractMonth("created"))
            .values("month")
            .annotate(c=Count("id"))
            .order_by()
        )
        context["pie_chart"] = (
            Issue.objects.filter(domain=context["domain"], hunt=None)
            .values("label")
            .annotate(c=Count("label"))
            .order_by()
        )
        context["twitter_url"] = "https://twitter.com/%s" % domain.get_or_set_x_url(domain.get_name)

        return context


import requests
from bs4 import BeautifulSoup
from django.db.models.functions import ExtractMonth
from django.views.generic import TemplateView

from .models import (
    IP,
    BaconToken,
    Bid,
    ChatBotLog,
    Company,
    CompanyAdmin,
    Contribution,
    Contributor,
    ContributorStats,
    Domain,
    Hunt,
    HuntPrize,
    InviteFriend,
    Issue,
    IssueScreenshot,
    Monitor,
    Payment,
    Points,
    Project,
    Subscription,
    Suggestion,
    SuggestionVotes,
    Transaction,
    User,
    UserProfile,
    Wallet,
    Winner,
)


class StatsDetailView(TemplateView):
    template_name = "stats.html"

    def get_context_data(self, *args, **kwargs):
        context = super(StatsDetailView, self).get_context_data(*args, **kwargs)

        response = requests.get(settings.EXTENSION_URL)
        soup = BeautifulSoup(response.text, "html.parser")

        stats = ""
        for item in soup.findAll("span", {"class": "e-f-ih"}):
            stats = item.attrs["title"]
        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)
        context["extension_users"] = stats.replace(" users", "") or "0"

        # Prepare stats data for display
        context["stats"] = [
            {"label": "Bugs", "count": Issue.objects.all().count(), "icon": "fas fa-bug"},
            {"label": "Users", "count": User.objects.all().count(), "icon": "fas fa-users"},
            {"label": "Hunts", "count": Hunt.objects.all().count(), "icon": "fas fa-crosshairs"},
            {"label": "Domains", "count": Domain.objects.all().count(), "icon": "fas fa-globe"},
            {
                "label": "Extension Users",
                "count": int(context["extension_users"].replace(",", "")),
                "icon": "fas fa-puzzle-piece",
            },
            {
                "label": "Subscriptions",
                "count": Subscription.objects.all().count(),
                "icon": "fas fa-envelope",
            },
            {
                "label": "Companies",
                "count": Company.objects.all().count(),
                "icon": "fas fa-building",
            },
            {
                "label": "Hunt Prizes",
                "count": HuntPrize.objects.all().count(),
                "icon": "fas fa-gift",
            },
            {
                "label": "Screenshots",
                "count": IssueScreenshot.objects.all().count(),
                "icon": "fas fa-camera",
            },
            {"label": "Winners", "count": Winner.objects.all().count(), "icon": "fas fa-trophy"},
            {"label": "Points", "count": Points.objects.all().count(), "icon": "fas fa-star"},
            {
                "label": "Invitations",
                "count": InviteFriend.objects.all().count(),
                "icon": "fas fa-envelope-open",
            },
            {
                "label": "User Profiles",
                "count": UserProfile.objects.all().count(),
                "icon": "fas fa-id-badge",
            },
            {"label": "IPs", "count": IP.objects.all().count(), "icon": "fas fa-network-wired"},
            {
                "label": "Company Admins",
                "count": CompanyAdmin.objects.all().count(),
                "icon": "fas fa-user-tie",
            },
            {
                "label": "Transactions",
                "count": Transaction.objects.all().count(),
                "icon": "fas fa-exchange-alt",
            },
            {
                "label": "Payments",
                "count": Payment.objects.all().count(),
                "icon": "fas fa-credit-card",
            },
            {
                "label": "Contributor Stats",
                "count": ContributorStats.objects.all().count(),
                "icon": "fas fa-chart-bar",
            },
            {"label": "Monitors", "count": Monitor.objects.all().count(), "icon": "fas fa-desktop"},
            {"label": "Bids", "count": Bid.objects.all().count(), "icon": "fas fa-gavel"},
            {
                "label": "Chatbot Logs",
                "count": ChatBotLog.objects.all().count(),
                "icon": "fas fa-robot",
            },
            {
                "label": "Suggestions",
                "count": Suggestion.objects.all().count(),
                "icon": "fas fa-lightbulb",
            },
            {
                "label": "Suggestion Votes",
                "count": SuggestionVotes.objects.all().count(),
                "icon": "fas fa-thumbs-up",
            },
            {
                "label": "Contributors",
                "count": Contributor.objects.all().count(),
                "icon": "fas fa-user-friends",
            },
            {
                "label": "Projects",
                "count": Project.objects.all().count(),
                "icon": "fas fa-project-diagram",
            },
            {
                "label": "Contributions",
                "count": Contribution.objects.all().count(),
                "icon": "fas fa-hand-holding-heart",
            },
            {
                "label": "Bacon Tokens",
                "count": BaconToken.objects.all().count(),
                "icon": "fas fa-coins",
            },
        ]
        context["stats"] = sorted(context["stats"], key=lambda x: int(x["count"]), reverse=True)

        def get_cumulative_data(queryset, date_field="created"):
            data = list(
                queryset.annotate(month=ExtractMonth(date_field))
                .values("month")
                .annotate(count=Count("id"))
                .order_by("month")
                .values_list("count", flat=True)
            )

            cumulative_data = []
            cumulative_sum = 0
            for count in data:
                cumulative_sum += count
                cumulative_data.append(cumulative_sum)

            return cumulative_data

        # Prepare cumulative sparklines data
        context["sparklines_data"] = [
            get_cumulative_data(Issue.objects),  # Uses "created"
            get_cumulative_data(User.objects, date_field="date_joined"),  # Uses "date_joined"
            get_cumulative_data(Hunt.objects),  # Uses "created"
            get_cumulative_data(Domain.objects),  # Uses "created"
            get_cumulative_data(Subscription.objects),  # Uses "created"
            get_cumulative_data(Company.objects),  # Uses "created"
            get_cumulative_data(HuntPrize.objects),  # Uses "created"
            get_cumulative_data(IssueScreenshot.objects),  # Uses "created"
            get_cumulative_data(Winner.objects),  # Uses "created"
            get_cumulative_data(Points.objects),  # Uses "created"
            get_cumulative_data(InviteFriend.objects),  # Uses "created"
            get_cumulative_data(UserProfile.objects),  # Uses "created"
            get_cumulative_data(IP.objects),  # Uses "created"
            get_cumulative_data(CompanyAdmin.objects),  # Uses "created"
            get_cumulative_data(Transaction.objects),  # Uses "created"
            get_cumulative_data(Payment.objects),  # Uses "created"
            get_cumulative_data(ContributorStats.objects),  # Uses "created"
            get_cumulative_data(Monitor.objects),  # Uses "created"
            get_cumulative_data(Bid.objects),  # Uses "created"
            get_cumulative_data(ChatBotLog.objects),  # Uses "created"
            get_cumulative_data(Suggestion.objects),  # Uses "created"
            get_cumulative_data(SuggestionVotes.objects),  # Uses "created"
            get_cumulative_data(Contributor.objects),  # Uses "created"
            get_cumulative_data(Project.objects),  # Uses "created"
            get_cumulative_data(Contribution.objects),  # Uses "created"
            get_cumulative_data(BaconToken.objects),  # Uses "created"
        ]

        return context


class AllIssuesView(ListView):
    paginate_by = 20
    template_name = "list_view.html"

    def get_queryset(self):
        username = self.request.GET.get("user")
        if username is None:
            self.activities = Issue.objects.filter(hunt=None).exclude(
                Q(is_hidden=True) & ~Q(user_id=self.request.user.id)
            )
        else:
            self.activities = Issue.objects.filter(user__username=username, hunt=None).exclude(
                Q(is_hidden=True) & ~Q(user_id=self.request.user.id)
            )
        return self.activities

    def get_context_data(self, *args, **kwargs):
        context = super(AllIssuesView, self).get_context_data(*args, **kwargs)
        paginator = Paginator(self.activities, self.paginate_by)
        page = self.request.GET.get("page")

        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)
        try:
            activities_paginated = paginator.page(page)
        except PageNotAnInteger:
            activities_paginated = paginator.page(1)
        except EmptyPage:
            activities_paginated = paginator.page(paginator.num_pages)

        context["activities"] = activities_paginated
        context["user"] = self.request.GET.get("user")
        context["activity_screenshots"] = {}
        for activity in self.activities:
            context["activity_screenshots"][activity] = IssueScreenshot.objects.filter(
                issue=activity
            ).first()
        return context


class SpecificIssuesView(ListView):
    paginate_by = 20
    template_name = "list_view.html"

    def get_queryset(self):
        username = self.request.GET.get("user")
        label = self.request.GET.get("label")
        query = 0
        statu = "none"

        if label == "General":
            query = 0
        elif label == "Number":
            query = 1
        elif label == "Functional":
            query = 2
        elif label == "Performance":
            query = 3
        elif label == "Security":
            query = 4
        elif label == "Typo":
            query = 5
        elif label == "Design":
            query = 6
        elif label == "open":
            statu = "open"
        elif label == "closed":
            statu = "closed"

        if username is None:
            self.activities = Issue.objects.filter(hunt=None).exclude(
                Q(is_hidden=True) & ~Q(user_id=self.request.user.id)
            )
        elif statu != "none":
            self.activities = Issue.objects.filter(
                user__username=username, status=statu, hunt=None
            ).exclude(Q(is_hidden=True) & ~Q(user_id=self.request.user.id))
        else:
            self.activities = Issue.objects.filter(
                user__username=username, label=query, hunt=None
            ).exclude(Q(is_hidden=True) & ~Q(user_id=self.request.user.id))
        return self.activities

    def get_context_data(self, *args, **kwargs):
        context = super(SpecificIssuesView, self).get_context_data(*args, **kwargs)
        paginator = Paginator(self.activities, self.paginate_by)
        page = self.request.GET.get("page")

        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)
        try:
            activities_paginated = paginator.page(page)
        except PageNotAnInteger:
            activities_paginated = paginator.page(1)
        except EmptyPage:
            activities_paginated = paginator.page(paginator.num_pages)

        context["activities"] = activities_paginated
        context["user"] = self.request.GET.get("user")
        context["label"] = self.request.GET.get("label")
        return context


class LeaderboardBase:
    """
    get:
        1) ?monthly=true will give list of winners for current month
        2) ?year=2022 will give list of winner of every month from month 1-12 else None

    """

    def get_leaderboard(self, month=None, year=None, api=False):
        """
        all user scores for specified month and year
        """

        data = User.objects

        if year and not month:
            data = data.filter(points__created__year=year)

        if year and month:
            data = data.filter(Q(points__created__year=year) & Q(points__created__month=month))

        data = (
            data.annotate(total_score=Sum("points__score"))
            .order_by("-total_score")
            .filter(
                total_score__gt=0,
            )
        )
        if api:
            return data.values("id", "username", "total_score")

        return data

    def current_month_leaderboard(self, api=False):
        """
        leaderboard which includes current month users scores
        """
        return self.get_leaderboard(
            month=int(datetime.now().month), year=int(datetime.now().year), api=api
        )

    def monthly_year_leaderboard(self, year, api=False):
        """
        leaderboard which includes current year top user from each month
        """

        monthly_winner = []

        # iterating over months 1-12
        for month in range(1, 13):
            month_winner = self.get_leaderboard(month, year, api).first()
            monthly_winner.append(month_winner)

        return monthly_winner


class GlobalLeaderboardView(LeaderboardBase, ListView):
    """
    Returns: All users:score data in descending order
    """

    model = User
    template_name = "leaderboard_global.html"

    def get_context_data(self, *args, **kwargs):
        context = super(GlobalLeaderboardView, self).get_context_data(*args, **kwargs)

        user_related_tags = Tag.objects.filter(userprofile__isnull=False).distinct()
        context["user_related_tags"] = user_related_tags

        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)
        context["leaderboard"] = self.get_leaderboard()
        return context


class EachmonthLeaderboardView(LeaderboardBase, ListView):
    """
    Returns: Grouped user:score data in months for current year
    """

    model = User
    template_name = "leaderboard_eachmonth.html"

    def get_context_data(self, *args, **kwargs):
        context = super(EachmonthLeaderboardView, self).get_context_data(*args, **kwargs)

        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)

        year = self.request.GET.get("year")

        if not year:
            year = datetime.now().year

        if isinstance(year, str) and not year.isdigit():
            raise Http404(f"Invalid query passed | Year:{year}")

        year = int(year)

        leaderboard = self.monthly_year_leaderboard(year)
        month_winners = []

        months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "Novermber",
            "December",
        ]

        for month_indx, usr in enumerate(leaderboard):
            month_winner = {"user": usr, "month": months[month_indx]}
            month_winners.append(month_winner)

        context["leaderboard"] = month_winners

        return context


class SpecificMonthLeaderboardView(LeaderboardBase, ListView):
    """
    Returns: leaderboard for filtered month and year requested in the query
    """

    model = User
    template_name = "leaderboard_specific_month.html"

    def get_context_data(self, *args, **kwargs):
        context = super(SpecificMonthLeaderboardView, self).get_context_data(*args, **kwargs)

        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)

        month = self.request.GET.get("month")
        year = self.request.GET.get("year")

        if not month:
            month = datetime.now().month
        if not year:
            year = datetime.now().year

        if isinstance(month, str) and not month.isdigit():
            raise Http404(f"Invalid query passed | Month:{month}")
        if isinstance(year, str) and not year.isdigit():
            raise Http404(f"Invalid query passed | Year:{year}")

        month = int(month)
        year = int(year)

        if not (month >= 1 and month <= 12):
            raise Http404(f"Invalid query passed | Month:{month}")

        context["leaderboard"] = self.get_leaderboard(month, year, api=False)
        return context


class ScoreboardView(ListView):
    model = Domain
    template_name = "scoreboard.html"
    paginate_by = 20

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        # Annotate each domain with the count of open issues
        annotated_domains = Domain.objects.annotate(
            open_issues_count=Count("issue", filter=Q(issue__status="open"))
        ).order_by("-open_issues_count")

        paginator = Paginator(annotated_domains, self.paginate_by)
        page = self.request.GET.get("page")

        try:
            scoreboard_paginated = paginator.page(page)
        except PageNotAnInteger:
            scoreboard_paginated = paginator.page(1)
        except EmptyPage:
            scoreboard_paginated = paginator.page(paginator.num_pages)

        context["scoreboard"] = scoreboard_paginated
        context["user"] = self.request.GET.get("user")
        return context


def search(request, template="search.html"):
    query = request.GET.get("query")
    stype = request.GET.get("type")
    context = None
    if query is None:
        return render(request, template)
    query = query.strip()
    if query[:6] == "issue:":
        stype = "issue"
        query = query[6:]
    elif query[:7] == "domain:":
        stype = "domain"
        query = query[7:]
    elif query[:5] == "user:":
        stype = "user"
        query = query[5:]
    elif query[:6] == "label:":
        stype = "label"
        query = query[6:]
    if stype == "issue" or stype is None:
        context = {
            "query": query,
            "type": stype,
            "issues": Issue.objects.filter(Q(description__icontains=query), hunt=None).exclude(
                Q(is_hidden=True) & ~Q(user_id=request.user.id)
            )[0:20],
        }
    elif stype == "domain":
        context = {
            "query": query,
            "type": stype,
            "domains": Domain.objects.filter(Q(url__icontains=query), hunt=None)[0:20],
        }
    elif stype == "user":
        context = {
            "query": query,
            "type": stype,
            "users": UserProfile.objects.filter(Q(user__username__icontains=query))
            .annotate(total_score=Sum("user__points__score"))
            .order_by("-total_score")[0:20],
        }
    elif stype == "label":
        context = {
            "query": query,
            "type": stype,
            "issues": Issue.objects.filter(Q(label__icontains=query), hunt=None).exclude(
                Q(is_hidden=True) & ~Q(user_id=request.user.id)
            )[0:20],
        }

    if request.user.is_authenticated:
        context["wallet"] = Wallet.objects.get(user=request.user)
    return render(request, template, context)


def search_issues(request, template="search.html"):
    query = request.GET.get("query")
    stype = request.GET.get("type")
    context = None
    if query is None:
        return render(request, template)
    query = query.strip()
    if query[:6] == "issue:":
        stype = "issue"
        query = query[6:]
    elif query[:7] == "domain:":
        stype = "domain"
        query = query[7:]
    elif query[:5] == "user:":
        stype = "user"
        query = query[5:]
    elif query[:6] == "label:":
        stype = "label"
        query = query[6:]
    if stype == "issue" or stype is None:
        if request.user.is_anonymous:
            issues = Issue.objects.filter(Q(description__icontains=query), hunt=None).exclude(
                Q(is_hidden=True)
            )[0:20]
        else:
            issues = Issue.objects.filter(Q(description__icontains=query), hunt=None).exclude(
                Q(is_hidden=True) & ~Q(user_id=request.user.id)
            )[0:20]

        context = {
            "query": query,
            "type": stype,
            "issues": issues,
        }
    if stype == "domain" or stype is None:
        context = {
            "query": query,
            "type": stype,
            "issues": Issue.objects.filter(Q(domain__name__icontains=query), hunt=None).exclude(
                Q(is_hidden=True) & ~Q(user_id=request.user.id)
            )[0:20],
        }
    if stype == "user" or stype is None:
        context = {
            "query": query,
            "type": stype,
            "issues": Issue.objects.filter(Q(user__username__icontains=query), hunt=None).exclude(
                Q(is_hidden=True) & ~Q(user_id=request.user.id)
            )[0:20],
        }

    if stype == "label" or stype is None:
        context = {
            "query": query,
            "type": stype,
            "issues": Issue.objects.filter(Q(label__icontains=query), hunt=None).exclude(
                Q(is_hidden=True) & ~Q(user_id=request.user.id)
            )[0:20],
        }

    if request.user.is_authenticated:
        context["wallet"] = Wallet.objects.get(user=request.user)
    issues = serializers.serialize("json", context["issues"])
    issues = json.loads(issues)
    return HttpResponse(json.dumps({"issues": issues}), content_type="application/json")


class HuntCreate(CreateView):
    model = Hunt
    fields = ["url", "logo", "name", "description", "prize", "plan"]
    template_name = "hunt.html"

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.user

        domain, created = Domain.objects.get_or_create(
            name=self.request.POST.get("url").replace("www.", ""),
            defaults={"url": "http://" + self.request.POST.get("url").replace("www.", "")},
        )
        self.object.domain = domain

        self.object.save()
        return super(HuntCreate, self).form_valid(form)


class IssueView(DetailView):
    model = Issue
    slug_field = "id"
    template_name = "issue.html"

    def get(self, request, *args, **kwargs):
        print("getting issue id: ", self.kwargs["slug"])
        print("getting issue id: ", self.kwargs)
        ipdetails = IP()
        try:
            id = int(self.kwargs["slug"])
        except ValueError:
            return HttpResponseNotFound("Invalid ID: ID must be an integer")

        self.object = get_object_or_404(Issue, id=self.kwargs["slug"])
        ipdetails.user = self.request.user
        ipdetails.address = get_client_ip(request)
        ipdetails.issuenumber = self.object.id
        ipdetails.path = request.path
        ipdetails.agent = request.META["HTTP_USER_AGENT"]
        ipdetails.referer = request.META.get("HTTP_REFERER", None)

        print("IP Address: ", ipdetails.address)
        print("Issue Number: ", ipdetails.issuenumber)

        try:
            if self.request.user.is_authenticated:
                try:
                    objectget = IP.objects.get(user=self.request.user, issuenumber=self.object.id)
                    self.object.save()
                except:
                    ipdetails.save()
                    self.object.views = (self.object.views or 0) + 1
                    self.object.save()
            else:
                try:
                    objectget = IP.objects.get(
                        address=get_client_ip(request), issuenumber=self.object.id
                    )
                    self.object.save()
                except Exception as e:
                    pass  # pass this temporarly to avoid error
                    # print(e)
                    # messages.error(self.request, "That issue was not found 2." + str(e))
                    # ipdetails.save()
                    # self.object.views = (self.object.views or 0) + 1
                    # self.object.save()
        except Exception as e:
            pass  # pass this temporarly to avoid error
            # print(e)
            # messages.error(self.request, "That issue was not found 1." + str(e))
            # return redirect("/")
        return super(IssueView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        print("getting context data")
        context = super(IssueView, self).get_context_data(**kwargs)
        if self.object.user_agent:
            user_agent = parse(self.object.user_agent)
            context["browser_family"] = user_agent.browser.family
            context["browser_version"] = user_agent.browser.version_string
            context["os_family"] = user_agent.os.family
            context["os_version"] = user_agent.os.version_string
        context["users_score"] = list(
            Points.objects.filter(user=self.object.user)
            .aggregate(total_score=Sum("score"))
            .values()
        )[0]

        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)
        context["issue_count"] = Issue.objects.filter(url__contains=self.object.domain_name).count()
        context["all_comment"] = self.object.comments.all
        context["all_users"] = User.objects.all()
        context["likes"] = UserProfile.objects.filter(issue_upvoted=self.object).count()
        context["likers"] = UserProfile.objects.filter(issue_upvoted=self.object)
        context["dislikes"] = UserProfile.objects.filter(issue_downvoted=self.object).count()
        context["dislikers"] = UserProfile.objects.filter(issue_downvoted=self.object)

        context["flags"] = UserProfile.objects.filter(issue_flaged=self.object).count()
        context["flagers"] = UserProfile.objects.filter(issue_flaged=self.object)

        context["screenshots"] = IssueScreenshot.objects.filter(issue=self.object).all()

        return context


@login_required(login_url="/accounts/login")
def flag_issue(request, issue_pk):
    context = {}
    issue_pk = int(issue_pk)
    issue = Issue.objects.get(pk=issue_pk)
    userprof = UserProfile.objects.get(user=request.user)
    if userprof in UserProfile.objects.filter(issue_flaged=issue):
        userprof.issue_flaged.remove(issue)
    else:
        userprof.issue_flaged.add(issue)
        issue_pk = issue.pk

    userprof.save()
    total_flag_votes = UserProfile.objects.filter(issue_flaged=issue).count()
    context["object"] = issue
    context["flags"] = total_flag_votes
    return render(request, "_flags.html", context)


def IssueEdit(request):
    if request.method == "POST":
        issue = Issue.objects.get(pk=request.POST.get("issue_pk"))
        uri = request.POST.get("domain")
        link = uri.replace("www.", "")
        if request.user == issue.user or request.user.is_superuser:
            domain, created = Domain.objects.get_or_create(
                name=link, defaults={"url": "http://" + link}
            )
            issue.domain = domain
            if uri[:4] != "http" and uri[:5] != "https":
                uri = "https://" + uri
            issue.url = uri
            issue.description = request.POST.get("description")
            issue.label = request.POST.get("label")
            issue.save()
            if created:
                return HttpResponse("Domain Created")
            else:
                return HttpResponse("Updated")
        else:
            return HttpResponse("Unauthorised")
    else:
        return HttpResponse("POST ONLY")


def get_email_from_domain(domain_name):
    new_urls = deque(["http://" + domain_name])
    processed_urls = set()
    emails = set()
    emails_out = set()
    t_end = time.time() + 20

    while len(new_urls) and time.time() < t_end:
        url = new_urls.popleft()
        processed_urls.add(url)
        parts = urlsplit(url)
        base_url = "{0.scheme}://{0.netloc}".format(parts)
        path = url[: url.rfind("/") + 1] if "/" in parts.path else url
        try:
            response = requests.get(url)
        except:
            continue
        new_emails = set(
            re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", response.text, re.I)
        )
        if new_emails:
            emails.update(new_emails)
            break
        soup = BeautifulSoup(response.text)
        for anchor in soup.find_all("a"):
            link = anchor.attrs["href"] if "href" in anchor.attrs else ""
            if link.startswith("/"):
                link = base_url + link
            elif not link.startswith("http"):
                link = path + link
            if link not in new_urls and link not in processed_urls and link.find(domain_name) > 0:
                new_urls.append(link)

    for email in emails:
        if email.find(domain_name) > 0:
            emails_out.add(email)
    try:
        return list(emails_out)[0]
    except:
        return False


class InboundParseWebhookView(View):
    def post(self, request, *args, **kwargs):
        data = request.body
        for event in json.loads(data):
            try:
                domain = Domain.objects.get(email__iexact=event.get("email"))
                domain.email_event = event.get("event")
                if event.get("event") == "click":
                    domain.clicks = int(domain.clicks or 0) + 1
                domain.save()
            except Exception:
                pass

        return JsonResponse({"detail": "Inbound Sendgrid Webhook recieved"})


def UpdateIssue(request):
    if not request.POST.get("issue_pk"):
        return HttpResponse("Missing issue ID")
    issue = get_object_or_404(Issue, pk=request.POST.get("issue_pk"))
    try:
        for token in Token.objects.all():
            if request.POST["token"] == token.key:
                request.user = User.objects.get(id=token.user_id)
                tokenauth = True
    except:
        tokenauth = False
    if (
        request.method == "POST"
        and request.user.is_superuser
        or (issue is not None and request.user == issue.user)
    ):
        if request.POST.get("action") == "close":
            issue.status = "closed"
            issue.closed_by = request.user
            issue.closed_date = datetime.now()

            msg_plain = msg_html = render_to_string(
                "email/bug_updated.txt",
                {
                    "domain": issue.domain.name,
                    "name": issue.user.username if issue.user else "Anonymous",
                    "id": issue.id,
                    "username": request.user.username,
                    "action": "closed",
                },
            )
            subject = (
                issue.domain.name
                + " bug # "
                + str(issue.id)
                + " closed by "
                + request.user.username
            )

        elif request.POST.get("action") == "open":
            issue.status = "open"
            issue.closed_by = None
            issue.closed_date = None
            msg_plain = msg_html = render_to_string(
                "email/bug_updated.txt",
                {
                    "domain": issue.domain.name,
                    "name": issue.domain.email.split("@")[0],
                    "id": issue.id,
                    "username": request.user.username,
                    "action": "opened",
                },
            )
            subject = (
                issue.domain.name
                + " bug # "
                + str(issue.id)
                + " opened by "
                + request.user.username
            )

        mailer = settings.EMAIL_TO_STRING
        email_to = issue.user.email
        send_mail(subject, msg_plain, mailer, [email_to], html_message=msg_html)
        send_mail(subject, msg_plain, mailer, [issue.domain.email], html_message=msg_html)
        issue.save()
        return HttpResponse("Updated")

    elif request.method == "POST":
        return HttpResponse("invalid")


@receiver(user_logged_in)
def assign_issue_to_user(request, user, **kwargs):
    issue_id = request.session.get("issue")
    created = request.session.get("created")
    domain_id = request.session.get("domain")
    if issue_id and domain_id:
        try:
            del request.session["issue"]
            del request.session["domain"]
            del request.session["created"]
        except Exception:
            pass
        request.session.modified = True

        issue = Issue.objects.get(id=issue_id)
        domain = Domain.objects.get(id=domain_id)

        issue.user = user
        issue.save()

        assigner = IssueBaseCreate()
        assigner.request = request
        assigner.process_issue(user, issue, created, domain)


@login_required(login_url="/accounts/login")
def follow_user(request, user):
    if request.method == "GET":
        userx = User.objects.get(username=user)
        flag = 0
        list_userfrof = request.user.userprofile.follows.all()
        for prof in list_userfrof:
            if str(prof) == (userx.email):
                request.user.userprofile.follows.remove(userx.userprofile)
                flag = 1
        if flag != 1:
            request.user.userprofile.follows.add(userx.userprofile)
            msg_plain = render_to_string(
                "email/follow_user.txt", {"follower": request.user, "followed": userx}
            )
            msg_html = render_to_string(
                "email/follow_user.txt", {"follower": request.user, "followed": userx}
            )

            send_mail(
                "You got a new follower!!",
                msg_plain,
                settings.EMAIL_TO_STRING,
                [userx.email],
                html_message=msg_html,
            )
        return HttpResponse("Success")


@login_required(login_url="/accounts/login")
def save_issue(request, issue_pk):
    issue_pk = int(issue_pk)
    issue = Issue.objects.get(pk=issue_pk)
    userprof = UserProfile.objects.get(user=request.user)

    already_saved = userprof.issue_saved.filter(pk=issue_pk).exists()

    if already_saved:
        userprof.issue_saved.remove(issue)
        return HttpResponse("REMOVED")

    else:
        userprof.issue_saved.add(issue)
        return HttpResponse("OK")


@login_required(login_url="/accounts/login")
def unsave_issue(request, issue_pk):
    issue_pk = int(issue_pk)
    issue = Issue.objects.get(pk=issue_pk)
    userprof = UserProfile.objects.get(user=request.user)
    userprof.issue_saved.remove(issue)
    return HttpResponse("OK")


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def get_score(request):
    users = []
    temp_users = (
        User.objects.annotate(total_score=Sum("points__score"))
        .order_by("-total_score")
        .filter(total_score__gt=0)
    )
    rank_user = 1
    for each in temp_users.all():
        temp = {}
        temp["rank"] = rank_user
        temp["id"] = each.id
        temp["User"] = each.username
        temp["score"] = Points.objects.filter(user=each.id).aggregate(total_score=Sum("score"))
        temp["image"] = list(UserProfile.objects.filter(user=each.id).values("user_avatar"))[0]
        temp["title_type"] = list(UserProfile.objects.filter(user=each.id).values("title"))[0]
        temp["follows"] = list(UserProfile.objects.filter(user=each.id).values("follows"))[0]
        temp["savedissue"] = list(UserProfile.objects.filter(user=each.id).values("issue_saved"))[0]
        rank_user = rank_user + 1
        users.append(temp)
    return JsonResponse(users, safe=False)


def comment_on_issue(request, issue_pk):
    try:
        issue_pk = int(issue_pk)
    except ValueError:
        raise Http404("Issue does not exist")
    issue = Issue.objects.filter(pk=issue_pk).first()

    if request.method == "POST" and isinstance(request.user, User):
        comment = request.POST.get("comment", "")
        replying_to_input = request.POST.get("replying_to_input", "").split("#")

        if issue is None:
            Http404("Issue does not exist, cannot comment")

        if len(replying_to_input) == 2:
            replying_to_user = replying_to_input[0]
            replying_to_comment_id = replying_to_input[1]

            parent_comment = Comment.objects.filter(pk=replying_to_comment_id).first()

            if parent_comment is None:
                messages.error(request, "Parent comment doesn't exist.")
                return redirect(f"/issue/{issue_pk}")

            Comment.objects.create(
                parent=parent_comment,
                issue=issue,
                author=request.user.username,
                author_fk=request.user.userprofile,
                author_url=f"profile/{request.user.username}/",
                text=comment,
            )

        else:
            Comment.objects.create(
                issue=issue,
                author=request.user.username,
                author_fk=request.user.userprofile,
                author_url=f"profile/{request.user.username}/",
                text=comment,
            )

    context = {
        "all_comment": Comment.objects.filter(issue__id=issue_pk).order_by("-created_date"),
        "object": issue,
    }

    return render(request, "comments2.html", context)


# get issue and comment id from url
def update_comment(request, issue_pk, comment_pk):
    issue = Issue.objects.filter(pk=issue_pk).first()
    comment = Comment.objects.filter(pk=comment_pk).first()
    if request.method == "POST" and isinstance(request.user, User):
        comment.text = request.POST.get("comment", "")
        comment.save()

    context = {
        "all_comment": Comment.objects.filter(issue__id=issue_pk).order_by("-created_date"),
        "object": issue,
    }
    return render(request, "comments2.html", context)


@login_required(login_url="/accounts/login")
def delete_comment(request):
    int_issue_pk = int(request.POST["issue_pk"])
    issue = get_object_or_404(Issue, pk=int_issue_pk)
    if request.method == "POST":
        comment = Comment.objects.get(
            pk=int(request.POST["comment_pk"]), author=request.user.username
        )
        comment.delete()
    context = {
        "all_comments": Comment.objects.filter(issue__id=int_issue_pk).order_by("-created_date"),
        "object": issue,
    }
    return render(request, "comments2.html", context)


class CustomObtainAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        response = super(CustomObtainAuthToken, self).post(request, *args, **kwargs)
        token = Token.objects.get(key=response.data["token"])
        return Response({"token": token.key, "id": token.user_id})


def create_tokens(request):
    for user in User.objects.all():
        Token.objects.get_or_create(user=user)
    return JsonResponse("Created", safe=False)


def create_wallet(request):
    for user in User.objects.all():
        Wallet.objects.get_or_create(user=user)
    return JsonResponse("Created", safe=False)


def monitor_create_view(request):
    if request.method == "POST":
        form = MonitorForm(request.POST)
        if form.is_valid():
            monitor = form.save(commit=False)
            monitor.user = request.user  # Assuming you have a logged-in user
            monitor.save()
            # Redirect to a success page or render a success message
    else:
        form = MonitorForm()
    return render(request, "Moniter.html", {"form": form})


def issue_count(request):
    open_issue = Issue.objects.filter(status="open").count()
    close_issue = Issue.objects.filter(status="closed").count()
    return JsonResponse({"open": open_issue, "closed": close_issue}, safe=False)


def contributors(request):
    contributors_file_path = os.path.join(settings.BASE_DIR, "contributors.json")

    with open(contributors_file_path, "r", encoding="utf-8", errors="replace") as file:
        content = file.read()

    contributors_data = json.loads(content)
    return JsonResponse({"contributors": contributors_data})


def get_scoreboard(request):
    scoreboard = []
    temp_domain = Domain.objects.all()
    for each in temp_domain:
        temp = {}
        temp["name"] = each.name
        temp["open"] = len(each.open_issues)
        temp["closed"] = len(each.closed_issues)
        temp["modified"] = each.modified
        temp["logo"] = each.logo
        if each.top_tester is None:
            temp["top"] = "None"
        else:
            temp["top"] = each.top_tester.username
        scoreboard.append(temp)
    paginator = Paginator(scoreboard, 10)
    domain_list = []
    for data in scoreboard:
        domain_list.append(data)
    count = (Paginator(scoreboard, 10).count) % 10
    for i in range(10 - count):
        domain_list.append(None)
    temp = {}
    temp["name"] = None
    domain_list.append(temp)
    paginator = Paginator(domain_list, 10)
    page = request.GET.get("page")
    try:
        domain = paginator.page(page)
    except PageNotAnInteger:
        domain = paginator.page(1)
    except EmptyPage:
        domain = paginator.page(paginator.num_pages)
    return HttpResponse(
        json.dumps(domain.object_list, default=str), content_type="application/json"
    )


def throw_error(request):
    raise ValueError("error")


@require_GET
def robots_txt(request):
    lines = [
        "User-Agent: *",
        "Allow: /",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


@require_GET
def ads_txt(request):
    lines = [
        "google.com, pub-6468204154139130, DIRECT, f08c47fec0942fa0",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


class CreateHunt(TemplateView):
    model = Hunt
    fields = ["url", "logo", "domain", "plan", "prize", "txn_id"]
    template_name = "create_hunt.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        try:
            domain_admin = CompanyAdmin.objects.get(user=request.user)
            if not domain_admin.is_active:
                return HttpResponseRedirect("/")
            domain = []
            if domain_admin.role == 0:
                domain = Domain.objects.filter(company=domain_admin.company)
            else:
                domain = Domain.objects.filter(pk=domain_admin.domain.pk)

            context = {"domains": domain, "hunt_form": HuntForm()}
            return render(request, self.template_name, context)
        except:
            return HttpResponseRedirect("/")

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        try:
            domain_admin = CompanyAdmin.objects.get(user=request.user)
            if (
                domain_admin.role == 1
                and (
                    str(domain_admin.domain.pk)
                    == ((request.POST["domain"]).split("-"))[0].replace(" ", "")
                )
            ) or domain_admin.role == 0:
                wallet, created = Wallet.objects.get_or_create(user=request.user)
                total_amount = (
                    Decimal(request.POST["prize_winner"])
                    + Decimal(request.POST["prize_runner"])
                    + Decimal(request.POST["prize_second_runner"])
                )
                if total_amount > wallet.current_balance:
                    return HttpResponse("failed")
                hunt = Hunt()
                hunt.domain = Domain.objects.get(
                    pk=(request.POST["domain"]).split("-")[0].replace(" ", "")
                )
                data = {}
                data["content"] = request.POST["content"]
                data["start_date"] = request.POST["start_date"]
                data["end_date"] = request.POST["end_date"]
                form = HuntForm(data)
                if not form.is_valid():
                    return HttpResponse("failed")
                if not domain_admin.is_active:
                    return HttpResponse("failed")
                if domain_admin.role == 1:
                    if hunt.domain != domain_admin.domain:
                        return HttpResponse("failed")
                hunt.domain = Domain.objects.get(
                    pk=(request.POST["domain"]).split("-")[0].replace(" ", "")
                )
                tzsign = 1
                offset = request.POST["tzoffset"]
                if int(offset) < 0:
                    offset = int(offset) * (-1)
                    tzsign = -1
                start_date = form.cleaned_data["start_date"]
                end_date = form.cleaned_data["end_date"]
                if tzsign > 0:
                    start_date = start_date + timedelta(
                        hours=int(int(offset) / 60), minutes=int(int(offset) % 60)
                    )
                    end_date = end_date + timedelta(
                        hours=int(int(offset) / 60), minutes=int(int(offset) % 60)
                    )
                else:
                    start_date = start_date - (
                        timedelta(hours=int(int(offset) / 60), minutes=int(int(offset) % 60))
                    )
                    end_date = end_date - (
                        timedelta(hours=int(int(offset) / 60), minutes=int(int(offset) % 60))
                    )
                hunt.starts_on = start_date
                hunt.prize_winner = Decimal(request.POST["prize_winner"])
                hunt.prize_runner = Decimal(request.POST["prize_runner"])
                hunt.prize_second_runner = Decimal(request.POST["prize_second_runner"])
                hunt.end_on = end_date
                hunt.name = request.POST["name"]
                hunt.description = request.POST["content"]
                wallet.withdraw(total_amount)
                wallet.save()
                try:
                    is_published = request.POST["publish"]
                    hunt.is_published = True
                except:
                    hunt.is_published = False
                hunt.save()
                return HttpResponse("success")
            else:
                return HttpResponse("failed")
        except:
            return HttpResponse("failed")


class ListHunts(TemplateView):
    model = Hunt
    template_name = "hunt_list.html"

    def get(self, request, *args, **kwargs):
        search = request.GET.get("search", "")
        start_date = request.GET.get("start_date", None)
        end_date = request.GET.get("end_date", None)
        domain = request.GET.get("domain", None)
        hunt_type = request.GET.get("hunt_type", "all")

        hunts = (
            Hunt.objects.values(
                "id",
                "name",
                "url",
                "logo",
                "starts_on",
                "starts_on__day",
                "starts_on__month",
                "starts_on__year",
                "end_on",
                "end_on__day",
                "end_on__month",
                "end_on__year",
            )
            .annotate(total_prize=Sum("huntprize__value"))
            .all()
        )

        filtered_bughunts = {
            "all": hunts,
            "ongoing": hunts.filter(result_published=False, is_published=True),
            "ended": hunts.filter(result_published=True),
            "draft": hunts.filter(result_published=False, is_published=False),
        }

        hunts = filtered_bughunts.get(hunt_type, hunts)

        if search.strip() != "":
            hunts = hunts.filter(Q(name__icontains=search))

        if start_date != "" and start_date is not None:
            start_date = datetime.strptime(start_date, "%m/%d/%Y").strftime("%Y-%m-%d %H:%M")
            hunts = hunts.filter(starts_on__gte=start_date)

        if end_date != "" and end_date is not None:
            end_date = datetime.strptime(end_date, "%m/%d/%Y").strftime("%Y-%m-%d %H:%M")
            hunts = hunts.filter(end_on__gte=end_date)

        if domain != "Select Domain" and domain is not None:
            domain = Domain.objects.filter(id=domain).first()
            hunts = hunts.filter(domain=domain)

        context = {"hunts": hunts, "domains": Domain.objects.values("id", "name").all()}

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        request.GET.search = request.GET.get("search", "")
        request.GET.start_date = request.GET.get("start_date", "")
        request.GET.end_date = request.GET.get("end_date", "")
        request.GET.domain = request.GET.get("domain", "Select Domain")
        request.GET.hunt_type = request.GET.get("type", "all")

        return self.get(request)


class DraftHunts(TemplateView):
    model = Hunt
    fields = ["url", "logo", "domain", "plan", "prize", "txn_id"]
    template_name = "hunt_drafts.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        try:
            domain_admin = CompanyAdmin.objects.get(user=request.user)
            if not domain_admin.is_active:
                return HttpResponseRedirect("/")
            if domain_admin.role == 0:
                hunt = self.model.objects.filter(is_published=False)
            else:
                hunt = self.model.objects.filter(is_published=False, domain=domain_admin.domain)
            context = {"hunts": hunt}
            return render(request, self.template_name, context)
        except:
            return HttpResponseRedirect("/")


class UpcomingHunts(TemplateView):
    model = Hunt
    fields = ["url", "logo", "domain", "plan", "prize", "txn_id"]
    template_name = "hunt_upcoming.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        try:
            domain_admin = CompanyAdmin.objects.get(user=request.user)
            if not domain_admin.is_active:
                return HttpResponseRedirect("/")

            if domain_admin.role == 0:
                hunts = self.model.objects.filter(is_published=True)
            else:
                hunts = self.model.objects.filter(is_published=True, domain=domain_admin.domain)
            new_hunt = []
            for hunt in hunts:
                if ((hunt.starts_on - datetime.now(timezone.utc)).total_seconds()) > 0:
                    new_hunt.append(hunt)
            context = {"hunts": new_hunt}
            return render(request, self.template_name, context)
        except:
            return HttpResponseRedirect("/")


class OngoingHunts(TemplateView):
    model = Hunt
    fields = ["url", "logo", "domain", "plan", "prize", "txn_id"]
    template_name = "hunt_ongoing.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        try:
            domain_admin = CompanyAdmin.objects.get(user=request.user)
            if not domain_admin.is_active:
                return HttpResponseRedirect("/")
            if domain_admin.role == 0:
                hunts = self.model.objects.filter(is_published=True)
            else:
                hunts = self.model.objects.filter(is_published=True, domain=domain_admin.domain)
            new_hunt = []
            for hunt in hunts:
                if ((hunt.starts_on - datetime.now(timezone.utc)).total_seconds()) > 0:
                    new_hunt.append(hunt)
            context = {"hunts": new_hunt}
            return render(request, self.template_name, context)
        except:
            return HttpResponseRedirect("/")


class PreviousHunts(TemplateView):
    model = Hunt
    fields = ["url", "logo", "domain", "plan", "prize", "txn_id"]
    template_name = "hunt_previous.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        try:
            domain_admin = CompanyAdmin.objects.get(user=request.user)
            if not domain_admin.is_active:
                return HttpResponseRedirect("/")
            if domain_admin.role == 0:
                hunts = self.model.objects.filter(is_published=True)
            else:
                hunts = self.model.objects.filter(is_published=True, domain=domain_admin.domain)
            new_hunt = []
            for hunt in hunts:
                if ((hunt.starts_on - datetime.now(timezone.utc)).total_seconds()) > 0:
                    pass
                elif ((hunt.end_on - datetime.now(timezone.utc)).total_seconds()) < 0:
                    new_hunt.append(hunt)
                else:
                    pass
            context = {"hunts": new_hunt}
            return render(request, self.template_name, context)
        except:
            return HttpResponseRedirect("/")

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
        if form.is_valid():
            form.save()
        return redirect(reverse("profile", kwargs={"slug": kwargs.get("slug")}))


class CompanySettings(TemplateView):
    model = CompanyAdmin
    fields = ["user", "domain", "role", "is_active"]
    template_name = "company_settings.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        try:
            domain_admin = CompanyAdmin.objects.get(user=request.user)
            if not domain_admin.is_active:
                return HttpResponseRedirect("/")
            domain_admins = []
            domain_list = Domain.objects.filter(company=domain_admin.company)
            if domain_admin.role == 0:
                domain_admins = CompanyAdmin.objects.filter(
                    company=domain_admin.company, is_active=True
                )
            else:
                domain_admins = CompanyAdmin.objects.filter(
                    domain=domain_admin.domain, is_active=True
                )
            context = {
                "admins": domain_admins,
                "user": domain_admin,
                "domain_list": domain_list,
            }
            return render(request, self.template_name, context)
        except:
            return HttpResponseRedirect("/")

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
        if form.is_valid():
            form.save()
        return redirect(reverse("profile", kwargs={"slug": kwargs.get("slug")}))


@login_required(login_url="/accounts/login")
def update_role(request):
    if request.method == "POST":
        domain_admin = CompanyAdmin.objects.get(user=request.user)
        if domain_admin.role == 0 and domain_admin.is_active:
            for key, value in request.POST.items():
                if key.startswith("user@"):
                    user = User.objects.get(username=value)
                    if domain_admin.company.admin == request.user:
                        pass
                    domain_admin = CompanyAdmin.objects.get(user=user)
                    if request.POST["role@" + value] != "9":
                        domain_admin.role = request.POST["role@" + value]
                    elif request.POST["role@" + value] == "9":
                        domain_admin.is_active = False
                    if request.POST["domain@" + value] != "":
                        domain_admin.domain = Domain.objects.get(pk=request.POST["domain@" + value])
                    else:
                        domain_admin.domain = None
                    domain_admin.save()
            return HttpResponse("success")
        elif domain_admin.role == 1 and domain_admin.is_active:
            for key, value in request.POST.items():
                if key.startswith("user@"):
                    user = User.objects.get(username=value)
                    if domain_admin.company.admin == request.user:
                        pass
                    domain_admin = CompanyAdmin.objects.get(user=user)
                    if request.POST["role@" + value] == "1":
                        domain_admin.role = request.POST["role@" + value]
                    elif request.POST["role@" + value] == "9":
                        domain_admin.is_active = False
                    domain_admin.save()
            return HttpResponse("success")
        else:
            return HttpResponse("failed")
    else:
        return HttpResponse("failed")


@login_required(login_url="/accounts/login")
def add_role(request):
    if request.method == "POST":
        domain_admin = CompanyAdmin.objects.get(user=request.user)
        if domain_admin.role == 0 and domain_admin.is_active:
            email = request.POST["email"]
            user = User.objects.get(email=email)
            if request.user == user:
                return HttpResponse("success")
            try:
                admin = CompanyAdmin.objects.get(user=user)
                if admin.company == domain_admin.company:
                    admin.is_active = True
                    admin.save()
                    return HttpResponse("success")
                else:
                    return HttpResponse("already admin of another domain")
            except:
                try:
                    admin = CompanyAdmin()
                    admin.user = user
                    admin.role = 1
                    admin.company = domain_admin.company
                    admin.is_active = True
                    admin.save()
                    return HttpResponse("success")
                except:
                    return HttpResponse("failed")
        else:
            return HttpResponse("failed")
    else:
        return HttpResponse("failed")


@login_required(login_url="/accounts/login")
def add_or_update_company(request):
    user = request.user
    if user.is_superuser:
        if not user.is_active:
            return HttpResponseRedirect("/")
        if request.method == "POST":
            domain_pk = request.POST["id"]
            company = Company.objects.get(pk=domain_pk)
            user = company.admin
            if user != User.objects.get(email=request.POST["admin"]):
                try:
                    admin = CompanyAdmin.objects.get(user=user, company=company)
                    admin.user = User.objects.get(email=request.POST["admin"])
                    admin.save()
                except:
                    admin = CompanyAdmin()
                    admin.user = User.objects.get(email=request.POST["admin"])
                    admin.role = 0
                    admin.company = company
                    admin.is_active = True
                    admin.save()
            company.name = request.POST["name"]
            company.email = request.POST["email"]
            company.url = request.POST["url"]
            company.admin = User.objects.get(email=request.POST["admin"])
            company.github = request.POST["github"]
            try:
                is_verified = request.POST["verify"]
                if is_verified == "on":
                    company.is_active = True
                else:
                    company.is_active = False
            except:
                company.is_active = False
            try:
                company.subscription = Subscription.objects.get(name=request.POST["subscription"])
            except:
                pass
            try:
                company.logo = request.FILES["logo"]
            except:
                pass
            company.save()
            return HttpResponse("success")

        else:
            return HttpResponse("failed")
    else:
        return HttpResponse("no access")


class DomainList(TemplateView):
    model = Domain
    template_name = "company_domain_lists.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        domain_admin = CompanyAdmin.objects.get(user=request.user)
        if not domain_admin.is_active:
            return HttpResponseRedirect("/")
        domain = []
        if domain_admin.role == 0:
            domain = self.model.objects.filter(company=domain_admin.company)
        else:
            domain = self.model.objects.filter(pk=domain_admin.domain.pk)
        context = {"domains": domain}
        return render(request, self.template_name, context)


@login_required(login_url="/accounts/login")
def add_or_update_domain(request):
    if request.method == "POST":
        company_admin = CompanyAdmin.objects.get(user=request.user)
        subscription = company_admin.company.subscription
        count_domain = Domain.objects.filter(company=company_admin.company).count()
        try:
            try:
                domain_pk = request.POST["id"]
                domain = Domain.objects.get(pk=domain_pk)
                domain.name = request.POST["name"]
                domain.email = request.POST["email"]
                domain.github = request.POST["github"]
                try:
                    domain.logo = request.FILES["logo"]
                except:
                    pass
                domain.save()
                return HttpResponse("Domain Updated")
            except:
                if count_domain == subscription.number_of_domains:
                    return HttpResponse("Domains Reached Limit")
                else:
                    if company_admin.role == 0:
                        domain = Domain()
                        domain.name = request.POST["name"]
                        domain.url = request.POST["url"]
                        domain.email = request.POST["email"]
                        domain.github = request.POST["github"]
                        try:
                            domain.logo = request.FILES["logo"]
                        except:
                            pass
                        domain.company = company_admin.company
                        domain.save()
                        return HttpResponse("Domain Created")
                    else:
                        return HttpResponse("failed")
        except:
            return HttpResponse("failed")


@login_required(login_url="/accounts/login")
def company_dashboard_domain_detail(request, pk, template="company_dashboard_domain_detail.html"):
    user = request.user
    domain_admin = CompanyAdmin.objects.get(user=request.user)
    try:
        if (Domain.objects.get(pk=pk)) == domain_admin.domain:
            if not user.is_active:
                return HttpResponseRedirect("/")
            domain = get_object_or_404(Domain, pk=pk)
            return render(request, template, {"domain": domain})
        else:
            return redirect("/")
    except:
        return redirect("/")


@login_required(login_url="/accounts/login")
def company_dashboard_hunt_detail(request, pk, template="company_dashboard_hunt_detail.html"):
    hunt = get_object_or_404(Hunt, pk=pk)
    return render(request, template, {"hunt": hunt})


@login_required(login_url="/accounts/login")
def company_dashboard_hunt_edit(request, pk, template="company_dashboard_hunt_edit.html"):
    if request.method == "GET":
        hunt = get_object_or_404(Hunt, pk=pk)
        domain_admin = CompanyAdmin.objects.get(user=request.user)
        if not domain_admin.is_active:
            return HttpResponseRedirect("/")
        if domain_admin.role == 1:
            if hunt.domain != domain_admin.domain:
                return HttpResponseRedirect("/")
        domain = []
        if domain_admin.role == 0:
            domain = Domain.objects.filter(company=domain_admin.company)
        else:
            domain = Domain.objects.filter(pk=domain_admin.domain.pk)
        initial = {"content": hunt.description}
        context = {"hunt": hunt, "domains": domain, "hunt_form": HuntForm(initial)}
        return render(request, template, context)
    else:
        data = {}
        data["content"] = request.POST["content"]
        data["start_date"] = request.POST["start_date"]
        data["end_date"] = request.POST["end_date"]
        form = HuntForm(data)
        if not form.is_valid():
            return HttpResponse("failed")
        hunt = get_object_or_404(Hunt, pk=pk)
        domain_admin = CompanyAdmin.objects.get(user=request.user)
        if not domain_admin.is_active:
            return HttpResponse("failed")
        if domain_admin.role == 1:
            if hunt.domain != domain_admin.domain:
                return HttpResponse("failed")
        hunt.domain = Domain.objects.get(pk=(request.POST["domain"]).split("-")[0].replace(" ", ""))
        tzsign = 1
        offset = request.POST["tzoffset"]
        if int(offset) < 0:
            offset = int(offset) * (-1)
            tzsign = -1
        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]
        if tzsign > 0:
            start_date = start_date + timedelta(
                hours=int(int(offset) / 60), minutes=int(int(offset) % 60)
            )
            end_date = end_date + timedelta(
                hours=int(int(offset) / 60), minutes=int(int(offset) % 60)
            )
        else:
            start_date = start_date - (
                timedelta(hours=int(int(offset) / 60), minutes=int(int(offset) % 60))
            )
            end_date = end_date - (
                timedelta(hours=int(int(offset) / 60), minutes=int(int(offset) % 60))
            )
        hunt.starts_on = start_date
        hunt.end_on = end_date

        hunt.name = request.POST["name"]
        hunt.description = form.cleaned_data["content"]
        try:
            is_published = request.POST["publish"]
            hunt.is_published = True
        except:
            hunt.is_published = False
        hunt.save()
        return HttpResponse("success")


@login_required(login_url="/accounts/login")
def withdraw(request):
    if request.method == "POST":
        if request.user.is_authenticated:
            wallet, created = Wallet.objects.get_or_create(user=request.user)
            if wallet.current_balance < Decimal(request.POST["amount"]):
                return HttpResponse("msg : amount greater than wallet balance")
            else:
                amount = Decimal(request.POST["amount"])
            payments = Payment.objects.filter(wallet=wallet)
            for payment in payments:
                payment.active = False
            payment = Payment()
            payment.wallet = wallet
            payment.value = Decimal(request.POST["amount"])
            payment.save()
            from django.conf import settings

            stripe.api_key = settings.STRIPE_TEST_SECRET_KEY
            if wallet.account_id:
                account = stripe.Account.retrieve(wallet.account_id)
                if account.payouts_enabled:
                    balance = stripe.Balance.retrieve()
                    if balance.available[0].amount > payment.value * 100:
                        stripe.Transfer.create(
                            amount=Decimal(request.POST["amount"]) * 100,
                            currency="usd",
                            destination=wallet.account_id,
                            transfer_group="ORDER_95",
                        )
                        wallet.withdraw(Decimal(request.POST["amount"]))
                        wallet.save()
                        payment.active = False
                        payment.save()
                        return HttpResponseRedirect(
                            "/dashboard/user/profile/" + request.user.username
                        )
                    else:
                        return HttpResponse("INSUFFICIENT BALANCE")
                else:
                    wallet.account_id = None
                    wallet.save()
                    account = stripe.Account.create(
                        type="express",
                    )
                    wallet.account_id = account.id
                    wallet.save()
                    account_links = stripe.AccountLink.create(
                        account=account,
                        return_url=f"http://{settings.DOMAIN_NAME}:{settings.PORT}/dashboard/user/stripe/connected/"
                        + request.user.username,
                        refresh_url=f"http://{settings.DOMAIN_NAME}:{settings.PORT}/dashboard/user/profile/"
                        + request.user.username,
                        type="account_onboarding",
                    )
                    return JsonResponse({"redirect": account_links.url, "status": "success"})
            else:
                account = stripe.Account.create(
                    type="express",
                )
                wallet.account_id = account.id
                wallet.save()
                account_links = stripe.AccountLink.create(
                    account=account,
                    return_url=f"http://{settings.DOMAIN_NAME}:{settings.PORT}/dashboard/user/stripe/connected/"
                    + request.user.username,
                    refresh_url=f"http://{settings.DOMAIN_NAME}:{settings.PORT}/dashboard/user/profile/"
                    + request.user.username,
                    type="account_onboarding",
                )
                return JsonResponse({"redirect": account_links.url, "status": "success"})
        return JsonResponse({"status": "error"})


@login_required(login_url="/accounts/login")
def addbalance(request):
    if request.method == "POST":
        if request.user.is_authenticated:
            wallet, created = Wallet.objects.get_or_create(user=request.user)
            from django.conf import settings

            stripe.api_key = settings.STRIPE_TEST_SECRET_KEY
            charge = stripe.Charge.create(
                amount=int(Decimal(request.POST["amount"]) * 100),
                currency="usd",
                description="Example charge",
                source=request.POST["stripeToken"],
            )
            wallet.deposit(request.POST["amount"])
        return HttpResponse("success")


@login_required(login_url="/accounts/login")
def stripe_connected(request, username):
    user = User.objects.get(username=username)
    wallet, created = Wallet.objects.get_or_create(user=user)
    from django.conf import settings

    stripe.api_key = settings.STRIPE_TEST_SECRET_KEY
    account = stripe.Account.retrieve(wallet.account_id)
    if account.payouts_enabled:
        payment = Payment.objects.get(wallet=wallet, active=True)
        balance = stripe.Balance.retrieve()
        if balance.available[0].amount > payment.value * 100:
            stripe.Transfer.create(
                amount=payment.value * 100,
                currency="usd",
                destination="000123456789",
                transfer_group="ORDER_95",
            )
            wallet.withdraw(Decimal(request.POST["amount"]))
            wallet.save()
            payment.active = False
            payment.save()
            return HttpResponseRedirect("/dashboard/user/profile/" + username)
        else:
            return HttpResponse("ERROR")
    else:
        wallet.account_id = None
        wallet.save()
    return HttpResponse("error")


class JoinCompany(TemplateView):
    model = Company
    template_name = "join.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        context = {"wallet": wallet}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        name = request.POST["company"]
        try:
            company_exists = Company.objects.get(name=name)
            return JsonResponse({"status": "There was some error"})
        except:
            pass
        url = request.POST["url"]
        email = request.POST["email"]
        product = request.POST["product"]
        sub = Subscription.objects.get(name=product)
        if name == "" or url == "" or email == "" or product == "":
            return JsonResponse({"error": "Empty Fields"})
        paymentType = request.POST["paymentType"]
        if paymentType == "wallet":
            wallet, created = Wallet.objects.get_or_create(user=request.user)
            if wallet.current_balance < sub.charge_per_month:
                return JsonResponse({"error": "insufficient balance in Wallet"})
            wallet.withdraw(sub.charge_per_month)
            company = Company()
            company.admin = request.user
            company.name = name
            company.url = url
            company.email = email
            company.subscription = sub
            company.save()
            admin = CompanyAdmin()
            admin.user = request.user
            admin.role = 0
            admin.company = company
            admin.is_active = True
            admin.save()
            return JsonResponse({"status": "Success"})
            # company.subscription =
        elif paymentType == "card":
            from django.conf import settings

            stripe.api_key = settings.STRIPE_TEST_SECRET_KEY
            charge = stripe.Charge.create(
                amount=int(Decimal(sub.charge_per_month) * 100),
                currency="usd",
                description="Example charge",
                source=request.POST["stripeToken"],
            )
            company = Company()
            company.admin = request.user
            company.name = name
            company.url = url
            company.email = email
            company.subscription = sub
            company.save()
            admin = CompanyAdmin()
            admin.user = request.user
            admin.role = 0
            admin.company = company
            admin.is_active = True
            admin.save()
            return JsonResponse({"status": "Success"})
        else:
            return JsonResponse({"status": "There was some error"})


@login_required(login_url="/accounts/login")
def view_hunt(request, pk, template="view_hunt.html"):
    hunt = get_object_or_404(Hunt, pk=pk)
    time_remaining = None
    if ((hunt.starts_on - datetime.now(timezone.utc)).total_seconds()) > 0:
        hunt_active = False
        hunt_completed = False
        time_remaining = humanize.naturaltime(datetime.now(timezone.utc) - hunt.starts_on)
    elif ((hunt.end_on - datetime.now(timezone.utc)).total_seconds()) < 0:
        hunt_active = False
        hunt_completed = True
    else:
        hunt_active = True
        hunt_completed = False
    return render(
        request,
        template,
        {
            "hunt": hunt,
            "hunt_completed": hunt_completed,
            "time_remaining": time_remaining,
            "hunt_active": hunt_active,
        },
    )


@login_required(login_url="/accounts/login")
def submit_bug(request, pk, template="hunt_submittion.html"):
    hunt = get_object_or_404(Hunt, pk=pk)
    time_remaining = None
    if request.method == "GET":
        if ((hunt.starts_on - datetime.now(timezone.utc)).total_seconds()) > 0:
            return redirect("/dashboard/user/hunt/" + str(pk) + "/")
        elif ((hunt.end_on - datetime.now(timezone.utc)).total_seconds()) < 0:
            return redirect("/dashboard/user/hunt/" + str(pk) + "/")
        else:
            return render(request, template, {"hunt": hunt})
    elif request.method == "POST":
        if ((hunt.starts_on - datetime.now(timezone.utc)).total_seconds()) > 0:
            return redirect("/dashboard/user/hunt/" + str(pk) + "/")
        elif ((hunt.end_on - datetime.now(timezone.utc)).total_seconds()) < 0:
            return redirect("/dashboard/user/hunt/" + str(pk) + "/")
        else:
            url = request.POST["url"]
            description = request.POST["description"]
            if url == "" or description == "":
                issue_list = Issue.objects.filter(user=request.user, hunt=hunt).exclude(
                    Q(is_hidden=True) & ~Q(user_id=request.user.id)
                )
                return render(request, template, {"hunt": hunt, "issue_list": issue_list})
            parsed_url = urlparse(url)
            if parsed_url.scheme == "":
                url = "https://" + url
            parsed_url = urlparse(url)
            if parsed_url.netloc == "":
                issue_list = Issue.objects.filter(user=request.user, hunt=hunt).exclude(
                    Q(is_hidden=True) & ~Q(user_id=request.user.id)
                )
                return render(request, template, {"hunt": hunt, "issue_list": issue_list})
            label = request.POST["label"]
            if request.POST.get("file"):
                if isinstance(request.POST.get("file"), six.string_types):
                    import imghdr

                    # Check if the base64 string is in the "data:" format
                    data = (
                        "data:image/"
                        + request.POST.get("type")
                        + ";base64,"
                        + request.POST.get("file")
                    )
                    data = data.replace(" ", "")
                    data += "=" * ((4 - len(data) % 4) % 4)
                    if "data:" in data and ";base64," in data:
                        header, data = data.split(";base64,")

                    try:
                        decoded_file = base64.b64decode(data)
                    except TypeError:
                        TypeError("invalid_image")

                    file_name = str(uuid.uuid4())[:12]
                    extension = imghdr.what(file_name, decoded_file)
                    extension = "jpg" if extension == "jpeg" else extension
                    file_extension = extension

                    complete_file_name = "%s.%s" % (
                        file_name,
                        file_extension,
                    )

                    request.FILES["screenshot"] = ContentFile(decoded_file, name=complete_file_name)
            issue = Issue()
            issue.label = label
            issue.url = url
            issue.user = request.user
            issue.description = description
            try:
                issue.screenshot = request.FILES["screenshot"]
            except:
                issue_list = Issue.objects.filter(user=request.user, hunt=hunt).exclude(
                    Q(is_hidden=True) & ~Q(user_id=request.user.id)
                )
                return render(request, template, {"hunt": hunt, "issue_list": issue_list})
            issue.hunt = hunt
            issue.save()
            issue_list = Issue.objects.filter(user=request.user, hunt=hunt).exclude(
                Q(is_hidden=True) & ~Q(user_id=request.user.id)
            )
            return render(request, template, {"hunt": hunt, "issue_list": issue_list})


@login_required(login_url="/accounts/login")
def hunt_results(request, pk, template="hunt_results.html"):
    hunt = get_object_or_404(Hunt, pk=pk)
    return render(request, template, {"hunt": hunt})


@login_required(login_url="/accounts/login")
def company_hunt_results(request, pk, template="company_hunt_results.html"):
    hunt = get_object_or_404(Hunt, pk=pk)
    issues = Issue.objects.filter(hunt=hunt).exclude(
        Q(is_hidden=True) & ~Q(user_id=request.user.id)
    )
    context = {}
    if request.method == "GET":
        context["hunt"] = get_object_or_404(Hunt, pk=pk)
        context["issues"] = Issue.objects.filter(hunt=hunt).exclude(
            Q(is_hidden=True) & ~Q(user_id=request.user.id)
        )
        if hunt.result_published:
            context["winner"] = Winner.objects.get(hunt=hunt)
        return render(request, template, context)
    else:
        for issue in issues:
            issue.verified = False
            issue.score = 0
            issue.save()
        for key, value in request.POST.items():
            if key != "csrfmiddlewaretoken" and key != "submit" and key != "checkAll":
                submit_type = key.split("_")[0]
                issue_id = key.split("_")[1]
                issue = Issue.objects.get(pk=issue_id)
                if issue.hunt == hunt and submit_type == "item":
                    if value == "on":
                        issue.verified = True
                elif issue.hunt == hunt and submit_type == "value":
                    if value != "":
                        issue.score = int(value)
                try:
                    if request.POST["checkAll"]:
                        issue.verified = True
                except:
                    pass
                issue.save()
        if request.POST["submit"] == "save":
            pass
        if request.POST["submit"] == "publish":
            issue.save()
            index = 1
            winner = Winner()
            issue_with_score = (
                Issue.objects.filter(hunt=hunt, verified=True)
                .values("user")
                .order_by("user")
                .annotate(total_score=Sum("score"))
            )
            for obj in issue_with_score:
                user = User.objects.get(pk=obj["user"])
                if index == 1:
                    winner.winner = user
                if index == 2:
                    winner.runner = user
                if index == 3:
                    winner.second_runner = user
                if index == 4:
                    break
                index = index + 1
            total_amount = (
                Decimal(hunt.prize_winner)
                + Decimal(hunt.prize_runner)
                + Decimal(hunt.prize_second_runner)
            )
            from django.conf import settings

            stripe.api_key = settings.STRIPE_TEST_SECRET_KEY
            balance = stripe.Balance.retrieve()
            if balance.available[0].amount > total_amount * 100:
                if winner.winner:
                    wallet, created = Wallet.objects.get_or_create(user=winner.winner)
                    wallet.deposit(hunt.prize_winner)
                    wallet.save()
                if winner.runner:
                    wallet, created = Wallet.objects.get_or_create(user=winner.runner)
                    wallet.deposit(hunt.prize_runner)
                    wallet.save()
                if winner.second_runner:
                    wallet, created = Wallet.objects.get_or_create(user=winner.second_runner)
                    wallet.deposit(hunt.prize_second_runner)
                    wallet.save()
            winner.prize_distributed = True
            winner.hunt = hunt
            winner.save()
            hunt.result_published = True
            hunt.save()
            context["winner"] = winner
        context["hunt"] = get_object_or_404(Hunt, pk=pk)
        context["issues"] = Issue.objects.filter(hunt=hunt).exclude(
            Q(is_hidden=True) & ~Q(user_id=request.user.id)
        )
        return render(request, template, context)


def handler404(request, exception):
    return render(request, "404.html", {}, status=404)


def handler500(request, exception=None):
    return render(request, "500.html", {}, status=500)


def users_view(request, *args, **kwargs):
    context = {}

    # Get all tags related to all user profiles
    context["user_related_tags"] = Tag.objects.filter(userprofile__isnull=False).distinct()

    # Get all tags in the system
    context["tags"] = Tag.objects.all()

    # Check if a specific tag is being requested
    tag_name = request.GET.get("tag")
    if tag_name:
        # Check if the requested tag exists in user_related_tags
        if context["user_related_tags"].filter(name=tag_name).exists():
            context["tag"] = tag_name
            context["users"] = UserProfile.objects.filter(tags__name=tag_name)
        else:
            context["users"] = UserProfile.objects.none()  # No users if the tag isn't found
    else:
        # Default filter: Show users with the tag "BLT Contributor"
        context["tag"] = "BLT Contributors"
        context["users"] = UserProfile.objects.filter(tags__name="BLT Contributors")

    return render(request, "users.html", context=context)


def contributors_view(request, *args, **kwargs):
    contributors_file_path = os.path.join(settings.BASE_DIR, "contributors.json")

    with open(contributors_file_path, "r", encoding="utf-8") as file:
        content = file.read()

    contributors = json.loads(content)

    contributor_id = request.GET.get("contributor", None)

    if contributor_id:
        contributor = None
        for i in contributors:
            if str(i["id"]) == contributor_id:
                contributor = i

        if contributor is None:
            return HttpResponseNotFound("Contributor not found")

        return render(request, "contributors_detail.html", context={"contributor": contributor})

    context = {"contributors": contributors}

    return render(request, "contributors.html", context=context)


def sponsor_view(request):
    from bitcash.network import NetworkAPI

    def get_bch_balance(address):
        try:
            balance_satoshis = NetworkAPI.get_balance(address)
            balance_bch = balance_satoshis / 100000000  # Convert from satoshis to BCH
            return balance_bch
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    # Example BCH address
    bch_address = "bitcoincash:qr5yccf7j4dpjekyz3vpawgaarl352n7yv5d5mtzzc"

    balance = get_bch_balance(bch_address)
    if balance is not None:
        print(f"Balance of {bch_address}: {balance} BCH")

    return render(request, "sponsor.html", context={"balance": balance})


def safe_redirect(request: HttpRequest):
    http_referer = request.META.get("HTTP_REFERER")
    if http_referer:
        referer_url = urlparse(http_referer)
        # Check if the referer URL's host is the same as the site's host
        if referer_url.netloc == request.get_host():
            # Build a 'safe' version of the referer URL (without query string or fragment)
            safe_url = urlunparse(
                (referer_url.scheme, referer_url.netloc, referer_url.path, "", "", "")
            )
            return redirect(safe_url)
    # Redirect to the fallback path if 'HTTP_REFERER' is not provided or is not safe
    # Build the fallback URL using the request's scheme and host
    fallback_url = f"{request.scheme}://{request.get_host()}/"
    return redirect(fallback_url)


class DomainListView(ListView):
    model = Domain
    paginate_by = 20
    template_name = "domain_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        domain = Domain.objects.all()

        paginator = Paginator(domain, self.paginate_by)
        page = self.request.GET.get("page")

        try:
            domain_paginated = paginator.page(page)
        except PageNotAnInteger:
            domain_paginated = paginator.page(1)
        except EmptyPage:
            domain_paginated = paginator.page(paginator.num_pages)

        context["domain"] = domain_paginated
        return context


@login_required(login_url="/accounts/login")
def flag_issue(request, issue_pk):
    context = {}
    issue_pk = int(issue_pk)
    issue = Issue.objects.get(pk=issue_pk)
    userprof = UserProfile.objects.get(user=request.user)
    if userprof in UserProfile.objects.filter(issue_flaged=issue):
        userprof.issue_flaged.remove(issue)
    else:
        userprof.issue_flaged.add(issue)
        issue_pk = issue.pk

    userprof.save()
    total_flag_votes = UserProfile.objects.filter(issue_flaged=issue).count()
    context["object"] = issue
    context["flags"] = total_flag_votes
    context["isFlagged"] = UserProfile.objects.filter(
        issue_flaged=issue, user=request.user
    ).exists()
    return HttpResponse("Success")


@login_required(login_url="/accounts/login")
def like_issue(request, issue_pk):
    context = {}
    issue_pk = int(issue_pk)
    issue = get_object_or_404(Issue, pk=issue_pk)
    userprof = UserProfile.objects.get(user=request.user)

    if UserProfile.objects.filter(issue_downvoted=issue, user=request.user).exists():
        userprof.issue_downvoted.remove(issue)
    if UserProfile.objects.filter(issue_upvoted=issue, user=request.user).exists():
        userprof.issue_upvoted.remove(issue)
    else:
        userprof.issue_upvoted.add(issue)
    if issue.user is not None:
        liked_user = issue.user
        liker_user = request.user
        issue_pk = issue.pk
        msg_plain = render_to_string(
            "email/issue_liked.txt",
            {
                "liker_user": liker_user.username,
                "liked_user": liked_user.username,
                "issue_pk": issue_pk,
            },
        )
        msg_html = render_to_string(
            "email/issue_liked.txt",
            {
                "liker_user": liker_user.username,
                "liked_user": liked_user.username,
                "issue_pk": issue_pk,
            },
        )

        send_mail(
            "Your issue got an upvote!!",
            msg_plain,
            settings.EMAIL_TO_STRING,
            [liked_user.email],
            html_message=msg_html,
        )

    total_votes = UserProfile.objects.filter(issue_upvoted=issue).count()
    context["object"] = issue
    context["likes"] = total_votes
    context["isLiked"] = UserProfile.objects.filter(issue_upvoted=issue, user=request.user).exists()
    return HttpResponse("Success")


@login_required(login_url="/accounts/login")
def dislike_issue(request, issue_pk):
    context = {}
    issue_pk = int(issue_pk)
    issue = get_object_or_404(Issue, pk=issue_pk)
    userprof = UserProfile.objects.get(user=request.user)

    if UserProfile.objects.filter(issue_upvoted=issue, user=request.user).exists():
        userprof.issue_upvoted.remove(issue)
    if UserProfile.objects.filter(issue_downvoted=issue, user=request.user).exists():
        userprof.issue_downvoted.remove(issue)
    else:
        userprof.issue_downvoted.add(issue)
    total_votes = UserProfile.objects.filter(issue_downvoted=issue).count()
    context["object"] = issue
    context["dislikes"] = total_votes
    context["isDisliked"] = UserProfile.objects.filter(
        issue_downvoted=issue, user=request.user
    ).exists()
    return HttpResponse("Success")


@login_required(login_url="/accounts/login")
def vote_count(request, issue_pk):
    issue_pk = int(issue_pk)
    issue = Issue.objects.get(pk=issue_pk)

    total_upvotes = UserProfile.objects.filter(issue_upvoted=issue).count()
    total_downvotes = UserProfile.objects.filter(issue_downvoted=issue).count()
    return JsonResponse({"likes": total_upvotes, "dislikes": total_downvotes})


@login_required(login_url="/accounts/login")
def subscribe_to_domains(request, pk):
    domain = Domain.objects.filter(pk=pk).first()
    if domain is None:
        return JsonResponse("ERROR", safe=False, status=400)

    already_subscribed = request.user.userprofile.subscribed_domains.filter(pk=domain.id).exists()

    if already_subscribed:
        request.user.userprofile.subscribed_domains.remove(domain)
        request.user.userprofile.save()
        return JsonResponse("UNSUBSCRIBED", safe=False)

    else:
        request.user.userprofile.subscribed_domains.add(domain)
        request.user.userprofile.save()
        return JsonResponse("SUBSCRIBED", safe=False)


class IssueView(DetailView):
    model = Issue
    slug_field = "id"
    template_name = "issue.html"

    def get(self, request, *args, **kwargs):
        ipdetails = IP()
        try:
            id = int(self.kwargs["slug"])
        except ValueError:
            return HttpResponseNotFound("Invalid ID: ID must be an integer")

        self.object = get_object_or_404(Issue, id=self.kwargs["slug"])
        ipdetails.user = self.request.user
        ipdetails.address = get_client_ip(request)
        ipdetails.issuenumber = self.object.id
        ipdetails.path = request.get_full_path()
        ipdetails.referer = request.META.get("HTTP_REFERER")
        ipdetails.agent = request.META.get("HTTP_USER_AGENT")

        try:
            if self.request.user.is_authenticated:
                try:
                    objectget = IP.objects.get(user=self.request.user, issuenumber=self.object.id)
                    self.object.save()
                except:
                    ipdetails.save()
                    self.object.views = (self.object.views or 0) + 1
                    self.object.save()
            else:
                try:
                    objectget = IP.objects.get(
                        address=get_client_ip(request), issuenumber=self.object.id
                    )
                    self.object.save()
                except:
                    ipdetails.save()
                    self.object.views = (self.object.views or 0) + 1
                    self.object.save()
        except Exception as e:
            print(e)
            # TODO: this is only an error for ipv6 currently and doesn't require us to redirect the user - we'll sort this out later
            # messages.error(self.request, "That issue was not found."+str(e))
            # return redirect("/")
        return super(IssueView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(IssueView, self).get_context_data(**kwargs)
        if self.object.user_agent:
            user_agent = parse(self.object.user_agent)
            context["browser_family"] = user_agent.browser.family
            context["browser_version"] = user_agent.browser.version_string
            context["os_family"] = user_agent.os.family
            context["os_version"] = user_agent.os.version_string
        context["users_score"] = list(
            Points.objects.filter(user=self.object.user)
            .aggregate(total_score=Sum("score"))
            .values()
        )[0]

        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)
            context["isLiked"] = UserProfile.objects.filter(
                issue_upvoted=self.object, user=self.request.user
            ).exists()
            context["isDisliked"] = UserProfile.objects.filter(
                issue_downvoted=self.object, user=self.request.user
            ).exists()
            context["isFlagged"] = UserProfile.objects.filter(
                issue_flaged=self.object, user=self.request.user
            ).exists()
        context["issue_count"] = Issue.objects.filter(url__contains=self.object.domain_name).count()
        context["all_comment"] = self.object.comments.all().order_by("-created_date")
        context["all_users"] = User.objects.all()
        context["likes"] = UserProfile.objects.filter(issue_upvoted=self.object).count()
        context["dislikes"] = UserProfile.objects.filter(issue_downvoted=self.object).count()
        context["likers"] = UserProfile.objects.filter(issue_upvoted=self.object).all()
        context["flags"] = UserProfile.objects.filter(issue_flaged=self.object).count()
        context["flagers"] = UserProfile.objects.filter(issue_flaged=self.object)
        context["more_issues"] = (
            Issue.objects.filter(user=self.object.user)
            .exclude(id=self.object.id)
            .values("id", "description", "markdown_description", "screenshots__image")
            .order_by("views")[:4]
        )
        # TODO test if email works
        if isinstance(self.request.user, User):
            context["subscribed_to_domain"] = self.object.domain.user_subscribed_domains.filter(
                pk=self.request.user.userprofile.id
            ).exists()
        else:
            context["subscribed_to_domain"] = False

        if isinstance(self.request.user, User):
            context["bookmarked"] = self.request.user.userprofile.issue_saved.filter(
                pk=self.object.id
            ).exists()
        context["screenshots"] = IssueScreenshot.objects.filter(issue=self.object).all()
        context["status"] = Issue.objects.filter(id=self.object.id).get().status
        context["github_issues_url"] = (
            str(Issue.objects.filter(id=self.object.id).get().domain.github) + "/issues"
        )
        context["email_clicks"] = Issue.objects.filter(id=self.object.id).get().domain.clicks
        context["email_events"] = Issue.objects.filter(id=self.object.id).get().domain.email_event
        if not self.object.github_url:
            context["github_link"] = "empty"
        else:
            context["github_link"] = self.object.github_url

        return context


def create_github_issue(request, id):
    issue = get_object_or_404(Issue, id=id)
    screenshot_all = IssueScreenshot.objects.filter(issue=issue)
    # referer = request.META.get("HTTP_REFERER")
    # if not referer:
    #     return HttpResponseForbidden()
    if not os.environ.get("GITHUB_ACCESS_TOKEN"):
        return JsonResponse({"status": "Failed", "status_reason": "GitHub Access Token is missing"})
    if issue.github_url:
        return JsonResponse(
            {"status": "Failed", "status_reason": "GitHub Issue Exists at " + issue.github_url}
        )
    if issue.domain.github:
        screenshot_text = ""
        for screenshot in screenshot_all:
            screenshot_text += "![0](" + settings.FQDN + screenshot.image.url + ") \n"

        github_url = issue.domain.github.replace("https", "git").replace("http", "git") + ".git"
        from giturlparse import parse as parse_github_url

        p = parse_github_url(github_url)

        url = "https://api.github.com/repos/%s/%s/issues" % (p.owner, p.repo)
        the_user = request.user.username if request.user.is_authenticated else "Anonymous"

        issue_data = {
            "title": issue.description,
            "body": issue.markdown_description
            + "\n\n"
            + screenshot_text
            + "Read More: https://"
            + settings.FQDN
            + "/issue/"
            + str(id)
            + "\n found by "
            + str(the_user)
            + "\n at url: "
            + issue.url,
            "labels": ["Bug", settings.PROJECT_NAME_LOWER, issue.domain_name],
        }

        try:
            response = requests.post(
                url,
                data=json.dumps(issue_data),
                headers={"Authorization": "token " + os.environ.get("GITHUB_ACCESS_TOKEN")},
            )
            if response.status_code == 201:
                response_data = response.json()
                issue.github_url = response_data.get("html_url", "")
                issue.save()
                return JsonResponse({"status": "ok", "github_url": issue.github_url})
            else:
                return JsonResponse(
                    {"status": "Failed", "status_reason": "Issue with Github:" + response.reason}
                )
        except Exception as e:
            send_mail(
                "Error in GitHub issue creation for Issue ID " + str(issue.id),
                "Error in GitHub issue creation, check your GitHub settings\n"
                + "Your current settings are: "
                + str(issue.github_url)
                + " and the error is: "
                + str(e),
                settings.EMAIL_TO_STRING,
                [request.user.email],
                fail_silently=True,
            )
            return JsonResponse({"status": "Failed", "status_reason": "Failed: error is " + str(e)})
    else:
        return JsonResponse(
            {"status": "Failed", "status_reason": "No Github URL for this domain, please add it."}
        )


@login_required(login_url="/accounts/login")
@csrf_exempt
def resolve(request, id):
    issue = Issue.objects.get(id=id)
    if request.user.is_superuser or request.user == issue.user:
        if issue.status == "open":
            issue.status = "close"
            issue.closed_by = request.user
            issue.closed_date = now()
            issue.save()
            return JsonResponse({"status": "ok", "issue_status": issue.status})
        else:
            issue.status = "open"
            issue.closed_by = None
            issue.closed_date = None
            issue.save()
            return JsonResponse({"status": "ok", "issue_status": issue.status})
    else:
        return HttpResponseForbidden("not logged in or superuser or issue user")


@receiver(user_signed_up)
def handle_user_signup(request, user, **kwargs):
    referral_token = request.session.get("ref")
    if referral_token:
        try:
            invite = InviteFriend.objects.get(referral_code=referral_token)
            invite.recipients.add(user)
            invite.point_by_referral += 2
            invite.save()
            reward_sender_with_points(invite.sender)
            del request.session["ref"]
        except InviteFriend.DoesNotExist:
            pass


def reward_sender_with_points(sender):
    # Create or update points for the sender
    points, created = Points.objects.get_or_create(user=sender, defaults={"score": 0})
    points.score += 2  # Reward 2 points for each successful referral signup
    points.save()


def referral_signup(request):
    referral_token = request.GET.get("ref")
    # check the referral token is present on invitefriend model or not and if present then set the referral token in the session
    if referral_token:
        try:
            invite = InviteFriend.objects.get(referral_code=referral_token)
            request.session["ref"] = referral_token
        except InviteFriend.DoesNotExist:
            messages.error(request, "Invalid referral token")
            return redirect("account_signup")
    return redirect("account_signup")


def invite_friend(request):
    # check if the user is authenticated or not
    if not request.user.is_authenticated:
        return redirect("account_login")
    current_site = get_current_site(request)
    referral_code, created = InviteFriend.objects.get_or_create(sender=request.user)
    referral_link = f"https://{current_site.domain}/referral/?ref={referral_code.referral_code}"
    context = {
        "referral_link": referral_link,
    }
    return render(request, "invite_friend.html", context)


def trademark_search(request, **kwargs):
    if request.method == "POST":
        slug = request.POST.get("query")
        return redirect("trademark_detailview", slug=slug)
    return render(request, "trademark_search.html")


def trademark_detailview(request, slug):
    if settings.USPTO_API is None:
        return HttpResponse("API KEY NOT SETUP")

    trademark_available_url = "https://uspto-trademark.p.rapidapi.com/v1/trademarkAvailable/%s" % (
        slug
    )
    headers = {
        "x-rapidapi-host": "uspto-trademark.p.rapidapi.com",
        "x-rapidapi-key": settings.USPTO_API,
    }
    trademark_available_response = requests.get(trademark_available_url, headers=headers)
    ta_data = trademark_available_response.json()

    if ta_data[0]["available"] == "no":
        trademark_search_url = (
            "https://uspto-trademark.p.rapidapi.com/v1/trademarkSearch/%s/active" % (slug)
        )
        trademark_search_response = requests.get(trademark_search_url, headers=headers)
        ts_data = trademark_search_response.json()
        context = {"count": ts_data["count"], "items": ts_data["items"], "query": slug}

    else:
        context = {"available": ta_data[0]["available"]}

    return render(request, "trademark_detailview.html", context)


# class CreateIssue(CronJobBase):
#     RUN_EVERY_MINS = 1

#     schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
#     code = "blt.create_issue"  # a unique code

#     def do(self):
#         from django.conf import settings
#         import imaplib

#         mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
#         error = False
#         mail.login(settings.REPORT_EMAIL, settings.REPORT_EMAIL_PASSWORD)
#         mail.list()
#         # Out: list of "folders" aka labels in gmail.
#         mail.select("inbox")  # connect to inbox.
#         typ, data = mail.search(None, "ALL", "UNSEEN")
#         import email


#         for num in data[0].split():
#             image = False
#             screenshot_base64 = ""
#             url = ""
#             label = ""
#             token = "None"
#             typ, data = mail.fetch(num, "(RFC822)")
#             raw_email = (data[0][1]).decode("utf-8")
#             email_message = email.message_from_string(raw_email)
#             maintype = email_message.get_content_maintype()
#             error = False
#             for part in email_message.walk():
#                 if part.get_content_type() == "text/plain":  # ignore attachments/html
#                     body = part.get_payload(decode=True)
#                     body_text = body.decode("utf-8")
#                     words = body_text.split()
#                     flag_word = False
#                     for word in words:
#                         if word.lower() == ":":
#                             continue
#                         if word.lower() == "url":
#                             continue
#                         if word.lower() == "type":
#                             flag_word = True
#                             continue
#                         if not flag_word:
#                             url = word
#                             continue
#                         if flag_word:
#                             label = word
#                 if part.get_content_maintype() == "multipart":
#                     continue
#                 if part.get("Content-Disposition") is None:
#                     continue
#                 image = True
#                 screenshot_base64 = part
#             sender = email_message["From"].split()[-1]
#             address = re.sub(r"[<>]", "", sender)
#             for user in User.objects.all():
#                 if user.email == address:
#                     token = Token.objects.get(user_id=user.id).key
#                     break
#             if label.lower() == "general":
#                 label = 0
#             elif label.lower() == "number error":
#                 label = 1
#             elif label.lower() == "functional":
#                 label = 2
#             elif label.lower() == "performance":
#                 label = 3
#             elif label.lower() == "security":
#                 label = 4
#             elif label.lower() == "typo":
#                 label = 5
#             elif label.lower() == "design":
#                 label = 6
#             else:
#                 error = True
#             if token == "None":
#                 error = "TokenTrue"
#             if not image:
#                 error = True
#             if error:
#                 send_mail(
#                     "Error In Your Report",
#                     "There was something wrong with the mail you sent regarding the issue to be created. Please check the content and try again later !",
#                     settings.EMAIL_TO_STRING,
#                     [address],
#                     fail_silently=False,
#                 )
#             elif error == "TokenTrue":
#                 send_mail(
#                     "You are not a user of " + settings.PROJECT_NAME,
#                     "You are not a Registered user at " + settings.PROJECT_NAME + " .Please first Signup at " + settings.PROJECT_NAME + " and Try Again Later ! .",
#                     settings.EMAIL_TO_STRING,
#                     [address],
#                     fail_silently=False,
#                 )
#             else:
#                 data = {
#                     "url": url,
#                     "description": email_message["Subject"],
#                     "file": str(screenshot_base64.get_payload(decode=False)),
#                     "token": token,
#                     "label": label,
#                     "type": "jpg",
#                 }
#                 headers = {"Content-Type": "application/x-www-form-urlencoded"}
#                 requests.post(
#                     "https://" + settings.FQDN + "/api/v1/createissues/",
#                     data=json.dumps(data),
#                     headers=headers,
#                 )
#         mail.logout()
def update_bch_address(request):
    if request.method == "POST":
        selected_crypto = request.POST.get("selected_crypto")
        new_address = request.POST.get("new_address")
        if selected_crypto and new_address:
            try:
                user_profile = request.user.userprofile
                match selected_crypto:
                    case "Bitcoin":
                        user_profile.btc_address = new_address
                    case "Ethereum":
                        user_profile.eth_address = new_address
                    case "BitcoinCash":
                        user_profile.bch_address = new_address
                    case _:
                        messages.error(request, f"Invalid crypto selected: {selected_crypto}")
                        return redirect(reverse("profile", args=[request.user.username]))
                user_profile.save()
                messages.success(request, f"{selected_crypto} Address updated successfully.")
            except Exception as e:
                messages.error(request, f"Failed to update {selected_crypto} Address.")
        else:
            messages.error(request, f"Please provide a valid {selected_crypto}  Address.")
    else:
        messages.error(request, "Invalid request method.")

    username = request.user.username if request.user.username else "default_username"
    return redirect(reverse("profile", args=[username]))


def sitemap(request):
    random_domain = Domain.objects.order_by("?").first()
    return render(request, "sitemap.html", {"random_domain": random_domain})


class ContributorStatsView(TemplateView):
    template_name = "contributor_stats.html"
    today = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch all contributor stats records
        stats = ContributorStats.objects.all()
        if self.today:
            # For "today" stats
            user_stats = sorted(
                ([stat.username, stat.prs] for stat in stats if stat.prs > 0),
                key=lambda x: x[1],  # Sort by PRs value
                reverse=True,  # Descending order
            )
        else:
            # Convert the stats to a dictionary format expected by the template
            user_stats = {
                stat.username: {
                    "commits": stat.commits,
                    "issues_opened": stat.issues_opened,
                    "issues_closed": stat.issues_closed,
                    "assigned_issues": stat.assigned_issues,
                    "prs": stat.prs,
                    "comments": stat.comments,
                }
                for stat in stats
            }

        context["user_stats"] = user_stats
        context["today"] = self.today
        context["owner"] = "OWASP-BLT"
        context["repo"] = "BLT"
        context["start_date"] = (datetime.now().date() - timedelta(days=7)).isoformat()
        context["end_date"] = datetime.now().date().isoformat()

        return context


@login_required
def deletions(request):
    if request.method == "POST":
        form = MonitorForm(request.POST)
        if form.is_valid():
            monitor = form.save(commit=False)
            monitor.user = request.user
            monitor.save()
            messages.success(request, "Form submitted successfully!")
        else:
            messages.error(request, "Form submission failed. Please correct the errors.")
    else:
        form = MonitorForm()

    return render(
        request,
        "monitor.html",
        {"form": form, "deletions": Monitor.objects.filter(user=request.user)},
    )


def generate_bid_image(request, bid_amount):
    image = Image.new("RGB", (300, 100), color="white")
    draw = ImageDraw.Draw(image)

    font = ImageFont.load_default()
    draw.text((10, 10), f"Bid Amount: ${bid_amount}", fill="black", font=font)
    byte_io = io.BytesIO()
    image.save(byte_io, format="PNG")
    byte_io.seek(0)

    return HttpResponse(byte_io, content_type="image/png")


def change_bid_status(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            bid_id = data.get("id")
            bid = Bid.objects.get(id=bid_id)
            bid.status = "Selected"
            bid.save()
            return JsonResponse({"success": True})
        except Bid.DoesNotExist:
            return JsonResponse({"success": False, "error": "Bid not found"})
    return HttpResponse(status=405)


def get_unique_issues(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            issue_url = data.get("issue_url")
            if not issue_url:
                return JsonResponse({"success": False, "error": "issue_url not provided"})

            all_bids = Bid.objects.filter(issue_url=issue_url).values()
            return JsonResponse(list(all_bids), safe=False)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"})
    return HttpResponse(status=405)


def select_bid(request):
    return render(request, "bid_selection.html")


def SaveBiddingData(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "Please login to bid.")
            return redirect("login")
        user = request.user.username
        url = request.POST.get("issue_url")
        amount = request.POST.get("bid_amount")
        current_time = datetime.now(timezone.utc)
        bid = Bid(
            user=user,
            issue_url=url,
            amount=amount,
            created=current_time,
            modified=current_time,
        )
        bid.save()
        bid_link = f"https://blt.owasp.org/generate_bid_image/{amount}/"
        return JsonResponse({"Paste this in GitHub Issue Comments:": bid_link})
    bids = Bid.objects.all()
    return render(request, "bidding.html", {"bids": bids})


def fetch_current_bid(request):
    if request.method == "POST":
        unique_issue_links = Bid.objects.values_list("issue_url", flat=True).distinct()
        data = json.loads(request.body)
        issue_url = data.get("issue_url")
        bid = Bid.objects.filter(issue_url=issue_url).order_by("-created").first()
        if bid is not None:
            return JsonResponse(
                {
                    "issueLinks": list(unique_issue_links),
                    "current_bid": bid.amount,
                    "status": bid.status,
                }
            )
        else:
            return JsonResponse({"error": "Bid not found"}, status=404)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def submit_pr(request):
    if request.method == "POST":
        user = request.user.username
        pr_link = request.POST.get("pr_link")
        amount = request.POST.get("bid_amount")
        issue_url = request.POST.get("issue_link")
        status = "Submitted"
        current_time = datetime.now(timezone.utc)
        bch_address = request.POST.get("bch_address")
        bid = Bid(
            user=user,
            pr_link=pr_link,
            amount=amount,
            issue_url=issue_url,
            status=status,
            created=current_time,
            modified=current_time,
            bch_address=bch_address,
        )
        bid.save()
        return render(request, "submit_pr.html")

    return render(request, "submit_pr.html")


# Global variable to store the vector store
vector_store = None

# Define the daily request limit as a variable
DAILY_REQUEST_LIMIT = 10


@api_view(["POST"])
def chatbot_conversation(request):
    try:
        # Rate Limit Check
        today = datetime.now(timezone.utc).date()
        rate_limit_key = f"global_daily_requests_{today}"
        request_count = cache.get(rate_limit_key, 0)

        if request_count >= DAILY_REQUEST_LIMIT:
            return Response(
                {"error": "Daily request limit exceeded."}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        question = request.data.get("question", "")
        if not question:
            return Response({"error": "Invalid question"}, status=status.HTTP_400_BAD_REQUEST)
        check_api = is_api_key_valid(os.getenv("OPENAI_API_KEY"))
        if not check_api:
            ChatBotLog.objects.create(question=question, answer="Error: Invalid API Key")
            return Response({"error": "Invalid API Key"}, status=status.HTTP_400_BAD_REQUEST)

        # Apply validation for question
        if not question or not isinstance(question, str):
            ChatBotLog.objects.create(question=question, answer="Error: Invalid question")
            return Response({"error": "Invalid question"}, status=status.HTTP_400_BAD_REQUEST)

        global vector_store
        if not vector_store:
            try:
                vector_store = load_vector_store()
            except FileNotFoundError as e:
                ChatBotLog.objects.create(
                    question=question, answer="Error: Vector store not found {e}"
                )
                return Response(
                    {"error": "Vector store not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except Exception as e:
                ChatBotLog.objects.create(question=question, answer=f"Error: {str(e)}")
                return Response(
                    {"error": "Error loading vector store"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            finally:
                if not vector_store:
                    ChatBotLog.objects.create(
                        question=question, answer="Error: Vector store not loaded"
                    )
                    return Response(
                        {"error": "Vector store not loaded"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

        # Handle the "exit" command
        if question.lower() == "exit":
            # if buffer is present in the session then delete it
            if "buffer" in request.session:
                del request.session["buffer"]
            return Response({"answer": "Conversation memory cleared."}, status=status.HTTP_200_OK)

        crc, memory = conversation_chain(vector_store)
        if "buffer" in request.session:
            memory.buffer = request.session["buffer"]

        try:
            response = crc.invoke({"question": question})
        except Exception as e:
            error_message = f"Error: {str(e)}"
            ChatBotLog.objects.create(question=question, answer=error_message)
            return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # Increment the request count
        cache.set(rate_limit_key, request_count + 1, timeout=86400)  # Timeout set to one day
        request.session["buffer"] = memory.buffer

        # Log the conversation
        ChatBotLog.objects.create(question=question, answer=response["answer"])

        return Response({"answer": response["answer"]}, status=status.HTTP_200_OK)

    except Exception as e:
        error_message = f"Error: {str(e)}"
        ChatBotLog.objects.create(question=request.data.get("question", ""), answer=error_message)
        return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def weekly_report(request):
    domains = Domain.objects.all()
    report_data = [
        "Hey This is a weekly report from OWASP BLT regarding the bugs reported for your company!"
    ]
    try:
        for domain in domains:
            open_issues = domain.open_issues
            closed_issues = domain.closed_issues
            total_issues = open_issues.count() + closed_issues.count()
            issues = Issue.objects.filter(domain=domain)
            email = domain.email
            report_data.append(
                "Hey This is a weekly report from OWASP BLT regarding the bugs reported for your company!"
                f"\n\nCompany Name: {domain.name}"
                f"Open issues: {open_issues.count()}"
                f"Closed issues: {closed_issues.count()}"
                f"Total issues: {total_issues}"
            )
            for issue in issues:
                description = issue.description
                views = issue.views
                label = issue.get_label_display()
                report_data.append(
                    f"\n Description: {description} \n Views: {views} \n Labels: {label} \n"
                )

        report_string = "".join(report_data)
        send_mail(
            "Weekly Report!!!",
            report_string,
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )
    except:
        return HttpResponse("An error occurred while sending the weekly report")

    return HttpResponse("Weekly report sent successfully.")


def blt_tomato(request):
    current_dir = Path(__file__).parent
    json_file_path = current_dir / "fixtures" / "blt_tomato_project_link.json"

    try:
        with json_file_path.open("r") as json_file:
            data = json.load(json_file)
    except Exception:
        data = []

    for project in data:
        funding_details = project.get("funding_details", "").split(", ")
        funding_links = [url.strip() for url in funding_details if url.startswith("https://")]

        funding_link = funding_links[0] if funding_links else "#"
        project["funding_hyperlinks"] = funding_link

    return render(request, "blt_tomato.html", {"projects": data})


@login_required
def vote_suggestions(request):
    if request.method == "POST":
        user = request.user
        data = json.loads(request.body)
        suggestion_id = data.get("suggestion_id")
        suggestion = Suggestion.objects.get(id=suggestion_id)
        up_vote = data.get("up_vote")
        down_vote = data.get("down_vote")
        voted = SuggestionVotes.objects.filter(user=user, suggestion=suggestion).exists()
        if not voted:
            up_vote = True if up_vote else False
            down_vote = True if down_vote else False

            if up_vote or down_vote:
                voted = SuggestionVotes.objects.create(
                    user=user, suggestion=suggestion, up_vote=up_vote, down_vote=down_vote
                )

                if up_vote:
                    suggestion.up_votes += 1
                if down_vote:
                    suggestion.down_votes += 1
        else:
            if not up_vote:
                suggestion.up_votes -= 1
            if down_vote is False:
                suggestion.down_votes -= 1

            voted = SuggestionVotes.objects.filter(user=user, suggestion=suggestion).delete()

            if up_vote:
                voted = SuggestionVotes.objects.create(
                    user=user, suggestion=suggestion, up_vote=True, down_vote=False
                )
                suggestion.up_votes += 1

            if down_vote:
                voted = SuggestionVotes.objects.create(
                    user=user, suggestion=suggestion, down_vote=True, up_vote=False
                )
                suggestion.down_votes += 1

            suggestion.save()

        response = {
            "success": True,
            "up_vote": suggestion.up_votes,
            "down_vote": suggestion.down_votes,
        }
        return JsonResponse(response)

    return JsonResponse({"success": False, "error": "Invalid request method"}, status=402)


@login_required
def set_vote_status(request):
    if request.method == "POST":
        user = request.user
        data = json.loads(request.body)
        id = data.get("id")
        try:
            suggestion = Suggestion.objects.get(id=id)
        except Suggestion.DoesNotExist:
            return JsonResponse({"success": False, "error": "Suggestion not found"}, status=404)

        up_vote = SuggestionVotes.objects.filter(
            suggestion=suggestion, user=user, up_vote=True
        ).exists()
        down_vote = SuggestionVotes.objects.filter(
            suggestion=suggestion, user=user, down_vote=True
        ).exists()

        response = {"up_vote": up_vote, "down_vote": down_vote}
        return JsonResponse(response)

    return JsonResponse({"success": False, "error": "Invalid request method"}, status=400)


@login_required
def add_suggestions(request):
    if request.method == "POST":
        user = request.user
        data = json.loads(request.body)
        title = data.get("title")
        description = data.get("description", "")
        id = str(uuid.uuid4())
        print(description, title, id)
        if title and description and user:
            suggestion = Suggestion(user=user, title=title, description=description, id=id)
            suggestion.save()
            messages.success(request, "Suggestion added successfully.")
            return JsonResponse({"status": "success"})
        else:
            messages.error(request, "Please fill all the fields.")
            return JsonResponse({"status": "error"}, status=400)


def view_suggestions(request):
    suggestion = Suggestion.objects.all()
    return render(request, "feature_suggestion.html", {"suggestions": suggestion})
