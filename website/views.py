import base64
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import humanize
import requests
import requests.exceptions
import six
import stripe
from allauth.account.models import EmailAddress
from allauth.account.signals import user_logged_in, user_signed_up
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core import serializers
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Prefetch, Q, Sum
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
from django.utils.dateparse import parse_datetime
from django.utils.html import escape
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from requests.auth import HTTPBasicAuth
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view
from rest_framework.response import Response
from sendgrid import SendGridAPIClient

from blt import settings
from comments.models import Comment
from website.class_views import IssueBaseCreate
from website.models import (
    Bid,
    ChatBotLog,
    Company,
    CompanyAdmin,
    Domain,
    Hunt,
    InviteFriend,
    Issue,
    IssueScreenshot,
    Monitor,
    Notification,
    Payment,
    Points,
    Subscription,
    Suggestion,
    SuggestionVotes,
    TimeLog,
    UserProfile,
    Wallet,
    Winner,
)
from website.utils import get_github_issue_title, is_valid_https_url, rebuild_safe_url

from .bitcoin_utils import create_bacon_token
from .bot import conversation_chain, is_api_key_valid, load_vector_store
from .forms import HuntForm, MonitorForm, UserProfileForm
from .models import BaconToken, Contribution, Tag, UserProfile

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
                return redirect("domain", slug=domain.url)
            else:
                messages.error(request, "Organization not found in the domain")
                return redirect("domain", slug=domain.url)
        else:
            domain.company = company
            domain.save()
            messages.success(request, "Organization added successfully")
            return redirect("domain", slug=domain.url)
    else:
        return redirect("index")


def check_status(request):
    status = cache.get("service_status")

    if not status:
        status = {
            "bitcoin": False,
            "bitcoin_block": None,
            "sendgrid": False,
            "github": False,
        }

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

        cache.set("service_status", status, timeout=60)

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


def newhome(request, template="new_home.html"):
    if request.user.is_authenticated:
        email_record = EmailAddress.objects.filter(email=request.user.email).first()
        if email_record:
            if not email_record.verified:
                messages.error(request, "Please verify your email address.")
        else:
            messages.error(request, "No email associated with your account. Please add an email.")

    issues_queryset = Issue.objects.exclude(Q(is_hidden=True) & ~Q(user_id=request.user.id))
    paginator = Paginator(issues_queryset, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    issues_with_screenshots = page_obj.object_list.prefetch_related(
        Prefetch("screenshots", queryset=IssueScreenshot.objects.all())
    )
    bugs_screenshots = {issue: issue.screenshots.all()[:3] for issue in issues_with_screenshots}

    current_time = now()
    leaderboard = User.objects.filter(
        points__created__month=current_time.month, points__created__year=current_time.year
    )

    context = {
        "bugs": page_obj,
        "bugs_screenshots": bugs_screenshots,
        "leaderboard": User.objects.filter(
            points__created__month=datetime.now().month, points__created__year=datetime.now().year
        ),
        "room_name": "brodcast",
        "leaderboard": leaderboard,
    }
    return render(request, template, context)


from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def notification(request):
    notification = Notification.objects.filter(user=request.user).all()
    messages = [n.message for n in notification]
    notification_id = [n.id for n in notification]
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"notification_{request.user.id}",
        {
            "type": "send_notification",
            "notification_id": notification_id,
            "message": messages,
        },
    )
    return HttpResponse("Notification Sent")


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


def profile(request):
    try:
        return redirect("/profile/" + request.user.username)
    except Exception:
        return redirect("/")


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


import requests
from bs4 import BeautifulSoup

from .models import (
    BaconToken,
    Bid,
    ChatBotLog,
    Company,
    CompanyAdmin,
    Contribution,
    Domain,
    Hunt,
    InviteFriend,
    Issue,
    IssueScreenshot,
    Monitor,
    Payment,
    Points,
    Subscription,
    Suggestion,
    SuggestionVotes,
    User,
    UserProfile,
    Wallet,
    Winner,
)


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
        comment = escape(request.POST.get("comment", ""))
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
        comment.text = escape(request.POST.get("comment", ""))
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
            monitor.user = request.user
            monitor.save()
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

    context["user_related_tags"] = Tag.objects.filter(userprofile__isnull=False).distinct()

    context["tags"] = Tag.objects.all()

    tag_name = request.GET.get("tag")
    if tag_name:
        if context["user_related_tags"].filter(name=tag_name).exists():
            context["tag"] = tag_name
            context["users"] = UserProfile.objects.filter(tags__name=tag_name)
        else:
            context["users"] = UserProfile.objects.none()  # No users if the tag isn't found
    else:
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

    bch_address = "bitcoincash:qr5yccf7j4dpjekyz3vpawgaarl352n7yv5d5mtzzc"

    balance = get_bch_balance(bch_address)
    if balance is not None:
        print(f"Balance of {bch_address}: {balance} BCH")

    return render(request, "sponsor.html", context={"balance": balance})


def safe_redirect(request: HttpRequest):
    http_referer = request.META.get("HTTP_REFERER")
    if http_referer:
        referer_url = urlparse(http_referer)
        if referer_url.netloc == request.get_host():
            safe_url = urlunparse(
                (referer_url.scheme, referer_url.netloc, referer_url.path, "", "", "")
            )
            return redirect(safe_url)
    fallback_url = f"{request.scheme}://{request.get_host()}/"
    return redirect(fallback_url)


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


def create_github_issue(request, id):
    issue = get_object_or_404(Issue, id=id)
    screenshot_all = IssueScreenshot.objects.filter(issue=issue)
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
    points, created = Points.objects.get_or_create(user=sender, defaults={"score": 0})
    points.score += 2
    points.save()


def referral_signup(request):
    referral_token = request.GET.get("ref")
    if referral_token:
        try:
            invite = InviteFriend.objects.get(referral_code=referral_token)
            request.session["ref"] = referral_token
        except InviteFriend.DoesNotExist:
            messages.error(request, "Invalid referral token")
            return redirect("account_signup")
    return redirect("account_signup")


def invite_friend(request):
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


vector_store = None
DAILY_REQUEST_LIMIT = 10


@api_view(["POST"])
def chatbot_conversation(request):
    try:
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

        if question.lower() == "exit":
            if "buffer" in request.session:
                del request.session["buffer"]
            return Response({"answer": "Conversation memory cleared."}, status=status.HTTP_200_OK)

        crc, memory = conversation_chain(vector_store)
        if "buffer" in request.session:
            memory.buffer = request.session["buffer"]

        try:
            response = crc.invoke({"question": question})
        except Exception as e:
            ChatBotLog.objects.create(question=question, answer=f"Error: {str(e)}")
            return Response(
                {"error": "An internal error has occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        cache.set(rate_limit_key, request_count + 1, timeout=86400)  # Timeout set to one day
        request.session["buffer"] = memory.buffer

        ChatBotLog.objects.create(question=question, answer=response["answer"])

        return Response({"answer": response["answer"]}, status=status.HTTP_200_OK)

    except Exception as e:
        ChatBotLog.objects.create(
            question=request.data.get("question", ""), answer=f"Error: {str(e)}"
        )
        return Response(
            {"error": "An internal error has occurred."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


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


def sizzle(request):
    print(request.user)
    if not request.user.is_authenticated:
        messages.error(request, "Please login to access the Sizzle page.")
        return redirect("index")

    sizzle_data = None

    last_data = TimeLog.objects.filter(user=request.user).order_by("-created").first()

    if last_data:
        all_data = TimeLog.objects.filter(
            user=request.user, created__date=last_data.created.date()
        ).order_by("created")

        total_duration = sum((entry.duration for entry in all_data if entry.duration), timedelta())

        total_duration_seconds = total_duration.total_seconds()
        formatted_duration = (
            f"{int(total_duration_seconds // 60)} min {int(total_duration_seconds % 60)} sec"
        )

        github_issue_url = all_data.first().github_issue_url

        issue_title = get_github_issue_title(github_issue_url)

        start_time = all_data.first().start_time.strftime("%I:%M %p")
        date = last_data.created.strftime("%d %B %Y")

        sizzle_data = {
            "issue_title": issue_title,
            "duration": formatted_duration,
            "start_time": start_time,
            "date": date,
        }

    return render(request, "sizzle/sizzle.html", {"sizzle_data": sizzle_data})


def TimeLogListAPIView(request):
    print(request.user)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    if not start_date_str or not end_date_str:
        return JsonResponse(
            {"error": "Both start_date and end_date are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    start_date = parse_datetime(start_date_str)
    end_date = parse_datetime(end_date_str)

    if not start_date or not end_date:
        return JsonResponse({"error": "Invalid date format."}, status=status.HTTP_400_BAD_REQUEST)

    time_logs = TimeLog.objects.filter(
        user=request.user, created__range=[start_date, end_date]
    ).order_by("created")

    grouped_logs = defaultdict(list)
    for log in time_logs:
        date_str = log.created.strftime("%Y-%m-%d")
        grouped_logs[date_str].append(log)

    response_data = []
    for date, logs in grouped_logs.items():
        first_log = logs[0]
        total_duration = sum((log.duration for log in logs if log.duration), timedelta())

        total_duration_seconds = total_duration.total_seconds()
        formatted_duration = (
            f"{int(total_duration_seconds // 60)} min {int(total_duration_seconds % 60)} sec"
        )

        issue_title = get_github_issue_title(first_log.github_issue_url)

        start_time = first_log.start_time.strftime("%I:%M %p")
        formatted_date = first_log.created.strftime("%d %B %Y")

        day_data = {
            "issue_title": issue_title,
            "duration": formatted_duration,
            "start_time": start_time,
            "date": formatted_date,
        }

        response_data.append(day_data)

    return JsonResponse(response_data, safe=False, status=status.HTTP_200_OK)


def sizzle_docs(request):
    return render(request, "sizzle/sizzle_docs.html")


@login_required
def TimeLogListView(request):
    time_logs = TimeLog.objects.filter(user=request.user).order_by("-start_time")
    active_time_log = time_logs.filter(end_time__isnull=True).first()
    # print the all details of the active time log
    token, created = Token.objects.get_or_create(user=request.user)
    return render(
        request,
        "sizzle/time_logs.html",
        {"time_logs": time_logs, "active_time_log": active_time_log, "token": token.key},
    )
