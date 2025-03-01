import base64
import io
import json
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
import six
from allauth.account.models import EmailAddress
from allauth.account.signals import user_logged_in
from allauth.socialaccount.models import SocialToken
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, Prefetch, Q, Sum
from django.db.transaction import atomic
from django.dispatch import receiver
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotFound,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, ListView, TemplateView
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from rest_framework.authtoken.models import Token
from user_agents import parse

from blt import settings
from comments.models import Comment
from website.forms import CaptchaForm
from website.models import (
    IP,
    Activity,
    Bid,
    ContentType,
    Domain,
    GitHubIssue,
    Hunt,
    Issue,
    IssueScreenshot,
    Points,
    User,
    UserProfile,
    Wallet,
)
from website.utils import (
    get_client_ip,
    get_email_from_domain,
    image_validator,
    is_valid_https_url,
    rebuild_safe_url,
    safe_redirect_request,
)


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
    context["isDisliked"] = UserProfile.objects.filter(issue_downvoted=issue, user=request.user).exists()
    return HttpResponse("Success")


@login_required(login_url="/accounts/login")
def vote_count(request, issue_pk):
    issue_pk = int(issue_pk)
    issue = Issue.objects.get(pk=issue_pk)

    total_upvotes = UserProfile.objects.filter(issue_upvoted=issue).count()
    total_downvotes = UserProfile.objects.filter(issue_downvoted=issue).count()
    return JsonResponse({"likes": total_upvotes, "dislikes": total_downvotes})


def create_github_issue(request, id):
    issue = get_object_or_404(Issue, id=id)
    screenshot_all = IssueScreenshot.objects.filter(issue=issue)
    if not os.environ.get("GITHUB_TOKEN"):
        return JsonResponse({"status": "Failed", "status_reason": "GitHub Access Token is missing"})
    if issue.github_url:
        return JsonResponse(
            {
                "status": "Failed",
                "status_reason": "GitHub Issue Exists at " + issue.github_url,
            }
        )
    if issue.domain.github:
        screenshot_text = ""
        for screenshot in screenshot_all:
            screenshot_text += f"![{screenshot.image.name}]({settings.FQDN}{screenshot.image.url})\n"

        github_url = issue.domain.github.replace("https", "git").replace("http", "git") + ".git"
        from giturlparse import parse as parse_github_url

        p = parse_github_url(github_url)

        url = f"https://api.github.com/repos/{p.owner}/{p.repo}/issues"
        the_user = request.user.username if request.user.is_authenticated else "Anonymous"

        issue_data = {
            "title": issue.description,
            "body": f"{issue.markdown_description}\n\n{screenshot_text}\nRead More: https://{settings.FQDN}/issue/{id}\n found by {the_user}\n at url: {issue.url}",
            "labels": ["Bug", settings.PROJECT_NAME_LOWER, issue.domain_name],
        }

        try:
            response = requests.post(
                url,
                data=json.dumps(issue_data),
                headers={"Authorization": f"token {os.environ.get('GITHUB_TOKEN')}"},
            )
            if response.status_code == 201:
                response_data = response.json()
                issue.github_url = response_data.get("html_url", "")
                issue.save()
                return JsonResponse({"status": "ok", "github_url": issue.github_url})
            else:
                return JsonResponse(
                    {
                        "status": "Failed",
                        "status_reason": f"Issue with Github: {response.reason}",
                    }
                )
        except Exception as e:
            send_mail(
                f"Error in GitHub issue creation for Issue ID {issue.id}",
                f"Error in GitHub issue creation, check your GitHub settings\nYour current settings are: {issue.github_url} and the error is: {e}",
                settings.EMAIL_TO_STRING,
                [request.user.email],
                fail_silently=True,
            )
            return JsonResponse({"status": "Failed", "status_reason": f"Failed: error is {e}"})
    else:
        return JsonResponse(
            {
                "status": "Failed",
                "status_reason": "No Github URL for this domain, please add it.",
            }
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


def UpdateIssue(request):
    if not request.POST.get("issue_pk"):
        return HttpResponse("Missing issue ID")
    issue = get_object_or_404(Issue, pk=request.POST.get("issue_pk"))
    try:
        tokenauth = False
        if "token" in request.POST:
            for token in Token.objects.all():
                if request.POST["token"] == token.key:
                    request.user = User.objects.get(id=token.user_id)
                    tokenauth = True
                    break
    except:
        tokenauth = False
    if request.method == "POST" and request.user.is_superuser or (issue is not None and request.user == issue.user):
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
            subject = issue.domain.name + " bug # " + str(issue.id) + " closed by " + request.user.username

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
            subject = issue.domain.name + " bug # " + str(issue.id) + " opened by " + request.user.username

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
    leaderboard = (
        User.objects.filter(
            points__created__month=current_time.month,
            points__created__year=current_time.year,
        )
        .annotate(total_points=Sum("points__score"))
        .order_by("-total_points")
    )

    context = {
        "bugs": page_obj,
        "bugs_screenshots": bugs_screenshots,
        "leaderboard": leaderboard,
    }
    return render(request, template, context)


# The delete_issue function performs delete operation from the database
def delete_issue(request, id):
    try:
        # TODO: Refactor this for a direct query instead of looping through all tokens
        for token in Token.objects.all():
            if request.POST["token"] == token.key:
                request.user = User.objects.get(id=token.user_id)
                tokenauth = True
    except Token.DoesNotExist:
        tokenauth = False

    issue = Issue.objects.get(id=id)
    if request.user.is_superuser or request.user == issue.user or tokenauth:
        screenshots = issue.screenshots.all()
        for screenshot in screenshots:
            screenshot.delete()
        issue.delete()
        messages.success(request, "Issue deleted")
        if tokenauth:
            return JsonResponse("Deleted", safe=False)
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
        # Remove user from corresponding activity object that was created
        issue_activity = Activity.objects.filter(
            content_type=ContentType.objects.get_for_model(Issue), object_id=id
        ).first()
        # Have to define a default anonymous user since the not null constraint fails
        anonymous_user = User.objects.get_or_create(username="anonymous")[0]
        issue_activity.user = anonymous_user
        issue_activity.save()
        messages.success(request, "User removed from the issue")
        if tokenauth:
            return JsonResponse("User removed from the issue", safe=False)
        else:
            return safe_redirect_request(request)
    else:
        messages.error(request, "Permission denied")
        return safe_redirect_request(request)


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
            issues = Issue.objects.filter(Q(description__icontains=query), hunt=None).exclude(Q(is_hidden=True))[0:20]
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
       
