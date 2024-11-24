import base64
import io
import json
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
import six
import tweepy
from allauth.account.models import EmailAddress
from allauth.account.signals import user_logged_in
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
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
from django.utils.html import escape
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView
from PIL import Image, ImageDraw, ImageFont
from rest_framework.authtoken.models import Token
from user_agents import parse

from blt import settings
from comments.models import Comment
from website.forms import CaptchaForm
from website.models import (
    IP,
    Bid,
    Domain,
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
        "leaderboard": leaderboard,
    }
    return render(request, template, context)


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

                    data = (
                        "data:image/"
                        + self.request.POST.get("type")
                        + ";base64,"
                        + self.request.POST.get("file")
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

                    self.request.FILES["screenshot"] = ContentFile(
                        decoded_file, name=complete_file_name
                    )
        except:
            tokenauth = False
        initial = super(IssueCreate, self).get_initial()
        if self.request.POST.get("screenshot-hash"):
            initial["screenshot"] = "uploads\/" + self.request.POST.get("screenshot-hash") + ".png"
        return initial

    def post(self, request, *args, **kwargs):
        print("processing post for ip address: ", get_client_ip(request))
        url = request.POST.get("url").replace("www.", "").replace("https://", "")

        request.POST._mutable = True
        request.POST.update(url=url)
        request.POST._mutable = False

        if not settings.IS_TEST:
            try:
                if settings.DOMAIN_NAME in url:
                    print("Web site exists")

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
            img = Image.open(screenshot)
            img.verify()
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
            if len(self.request.FILES.getlist("screenshots")) == 0:
                messages.error(self.request, "Screenshot is needed!")
                obj.delete()
                return render(
                    self.request,
                    "report.html",
                    {"form": self.get_form(), "captcha_form": captcha_form},
                )
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
                messages.success(self.request, "Bug added!")
                return HttpResponseRedirect("/")

            if tokenauth:
                self.process_issue(
                    User.objects.get(id=token.user_id), obj, domain_exists, domain, True
                )
                return JsonResponse("Created", safe=False)
            else:
                self.process_issue(self.request.user, obj, domain_exists, domain)
                return HttpResponseRedirect("/")

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
                    print(e)
                    pass  # pass this temporarly to avoid error
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


def issue_count(request):
    open_issue = Issue.objects.filter(status="open").count()
    close_issue = Issue.objects.filter(status="closed").count()
    return JsonResponse({"open": open_issue, "closed": close_issue}, safe=False)


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


@login_required(login_url="/accounts/login")
def unsave_issue(request, issue_pk):
    issue_pk = int(issue_pk)
    issue = Issue.objects.get(pk=issue_pk)
    userprof = UserProfile.objects.get(user=request.user)
    userprof.issue_saved.remove(issue)
    return HttpResponse("OK")


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


def select_bid(request):
    return render(request, "bid_selection.html")
