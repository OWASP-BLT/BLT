import json
import os
import random
import re
import time
import urllib.request
import urllib.error
import urllib.parse
from collections import deque
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from urllib.parse import urlsplit

import requests
import requests.exceptions
import base64
import six
import uuid

#from django_cron import CronJobBase, Schedule
from allauth.account.models import EmailAddress
from allauth.account.signals import user_logged_in
from bs4 import BeautifulSoup
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse, reverse_lazy
from django.db.models import Sum, Count, Q
from django.db.models.functions import ExtractMonth
from django.dispatch import receiver
from django.http import Http404,JsonResponse,HttpResponseRedirect,HttpResponse,HttpResponseNotFound
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.views.generic import DetailView, TemplateView, ListView, View
from django.views.generic.edit import CreateView
from django.core import serializers
from django.conf import settings

from user_agents import parse
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialConnectView
from blt import settings
from rest_framework.authtoken.views import ObtainAuthToken

from website.models import (

    Winner,
    Payment,
    Wallet,
    Issue,
    Points,
    Hunt,
    Domain,
    InviteFriend,
    UserProfile,
    IP,
    CompanyAdmin,
    Subscription,
    Company,
    IssueScreenshot
)
from .forms import FormInviteFriend, UserProfileForm, HuntForm, CaptchaForm

from decimal import Decimal
import stripe
import humanize
from django.conf import settings

from django.views.decorators.cache import cache_page

#@cache_page(60 * 60 * 24)
def index(request, template="index.html"):
    
    try:
        domains = random.sample(Domain.objects.all(), 3)
    except:
        domains = None
    try:
        if not EmailAddress.objects.get(email=request.user.email).verified:
            messages.error(request, "Please verify your email address")
    except:
        pass

    bug_count = Issue.objects.all().count()
    user_count = User.objects.all().count()
    hunt_count = Hunt.objects.all().count()
    domain_count = Domain.objects.all().count()

    captcha_form = CaptchaForm()

    wallet = None
    if request.user.is_authenticated:
        wallet, created = Wallet.objects.get_or_create(user=request.user)

    activity_screenshots = {}
    for activity in Issue.objects.all():
        activity_screenshots[activity] = IssueScreenshot.objects.filter(issue=activity).first()

    top_companies = Issue.objects.values("domain__name").annotate(count=Count('domain__name')).order_by("-count")[:10]
    top_testers = Issue.objects.values("user__id","user__username").filter(user__isnull=False).annotate(count=Count('user__username')).order_by("-count")[:10]
    activities = Issue.objects.exclude(Q(is_hidden=True) & ~Q(user_id=request.user.id))[0:10]
    
    top_hunts = Hunt.objects.values('id','name','url','prize','logo').filter(is_published=True).order_by("-prize")[:3]

    context = {
        "server_url": request.build_absolute_uri('/'),
        "activities": activities,
        "domains": domains,
        "hunts": Hunt.objects.exclude(txn_id__isnull=True)[:4],
        "leaderboard": User.objects.filter(
            points__created__month=datetime.now().month,
            points__created__year=datetime.now().year,
        )
        .annotate(total_score=Sum("points__score"))
        .order_by("-total_score")[:10],
        "bug_count": bug_count,
        "user_count": user_count,
        "hunt_count": hunt_count,
        "domain_count": domain_count,
        "wallet": wallet,
        "captcha_form": captcha_form,
        "activity_screenshots":activity_screenshots,
        "top_companies":top_companies,
        "top_testers":top_testers,
        "top_hunts": top_hunts 
    }
    return render(request, template, context)


def github_callback(request):
    params = urllib.parse.urlencode(request.GET)
    return redirect(f"{settings.CALLBACK_URL_FOR_GITHUB}?{params}")


def google_callback(request):
    params = urllib.parse.urlencode(request.GET)
    return redirect(f"{settings.CALLBACK_URL_FOR_GOOGLE}?{params}")


def facebook_callback(request):
    params = urllib.parse.urlencode(request.GET)
    return redirect(f"{settings.CALLBACK_URL_FOR_FACEBOOK}?{params}")


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
        upcoming_hunt = list()
        ongoing_hunt = list()
        previous_hunt = list()
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
def admin_company_dashboard_detail(
    request, pk, template="admin_dashboard_company_detail.html"
):
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
    upcoming_hunt = list()
    ongoing_hunt = list()
    previous_hunt = list()
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


class IssueBaseCreate(object):
    def form_valid(self, form):
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
            self.request.POST["screenshot-hash"] = filename[:99] + str(uuid.uuid4()) + "." + extension

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
        p = Points.objects.create(user=user, issue=obj, score=score)
        messages.success(self.request, "Bug added! +" + str(score))

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
            if tokenauth == False:
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
    fields = ["url", "description", "domain", "label"]
    template_name = "report.html"

    def get_initial(self):
        try:
            json_data = json.loads(self.request.body)
            if not self.request.GET._mutable:
                self.request.POST._mutable = True
            self.request.POST["url"] = json_data["url"]
            self.request.POST["description"] = json_data["description"]
            self.request.POST["file"] = json_data["file"]
            self.request.POST["label"] = json_data["label"]
            self.request.POST["token"] = json_data["token"]
            self.request.POST["type"] = json_data["type"]
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
                    file_name = str(uuid.uuid4())[
                        :12
                    ]  # 12 characters are more than enough.
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
            initial["screenshot"] = (
                "uploads\/" + self.request.POST.get("screenshot-hash") + ".png"
            )
        return initial

    def post(self, request, *args, **kwargs):

        # resolve domain
        url = request.POST.get("url").replace("www.","").replace("https://","")
        
        request.POST._mutable = True
        request.POST.update(url=url) # only domain.com will be stored in db
        request.POST._mutable = False


        # disable domain search on testing
        if not settings.IS_TEST:
            try:

                if settings.DOMAIN_NAME in url:
                    print('Web site exists')

                # skip domain validation check if bugreport server down 
                elif request.POST["label"] == "7":
                    pass

                else:
                    response = requests.get( "https://" + url ,timeout=2)
                    if response.status_code == 200:
                        print('Web site exists')
                    else:
                        raise Exception
            except:
                messages.error(request,"Domain does not exist")
                return HttpResponseRedirect("/issue/")

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
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
            return HttpResponseRedirect("/issue/")
        
        clean_domain = obj.domain_name.replace("www.", "").replace("https://","").replace("http://","")
        domain = Domain.objects.filter(
            Q(name=clean_domain) |
            Q(url__icontains=clean_domain)
        ).first()
        
        created = False if domain==None else True 

        if not created:
            domain = Domain.objects.create(
                name=clean_domain,
                url=clean_domain
            )
            domain.save()
        

        obj.domain = domain

        if created and (self.request.user.is_authenticated or tokenauth):
            p = Points.objects.create(user=self.request.user, domain=domain, score=1)
            messages.success(self.request, "Domain added! + 1")

        if self.request.POST.get("screenshot-hash"):
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
            total_issues = Issue.objects.filter(
                user=User.objects.get(id=token.user_id)
            ).count()
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

        if len(self.request.FILES.getlist("screenshots")) > 5:
            messages.error(self.request, "Max limit of 5 images!")
            return HttpResponseRedirect("/issue/")
        for screenshot in self.request.FILES.getlist("screenshots"):
            filename = screenshot.name
            extension = filename.split(".")[-1] 
            screenshot.name = filename[:99] + str(uuid.uuid4()) + "." + extension            
            default_storage.save(f"screenshots/{screenshot.name}",screenshot)
            IssueScreenshot.objects.create(image=f"screenshots/{screenshot.name}",issue=obj)

        obj_screenshots = IssueScreenshot.objects.filter(issue_id=obj.id)
        screenshot_text = ''
        for screenshot in obj_screenshots:
            screenshot_text += "![0](" + screenshot.image.url + ") "

        if domain.github and os.environ.get("GITHUB_ACCESS_TOKEN"):
            from giturlparse import parse
            import json
            import requests

            github_url = (
                domain.github.replace("https", "git").replace("http", "git") + ".git"
            )
            p = parse(github_url)

            url = "https://api.github.com/repos/%s/%s/issues" % (p.owner, p.repo)

            if not obj.user:
                the_user = "Anonymous"
            else:
                the_user = obj.user
            issue = {
                "title": obj.description,
                "body": screenshot_text +
                 "https://" + settings.FQDN + "/issue/"
                + str(obj.id) + " found by " + str(the_user) + " at url: " + obj.url,
                "labels": ["bug", settings.PROJECT_NAME_LOWER],
            }
            r = requests.post(
                url,
                json.dumps(issue),
                headers={
                    "Authorization": "token " + os.environ.get("GITHUB_ACCESS_TOKEN")
                },
            )
            response = r.json()
            obj.github_url = response["html_url"]
            obj.save()

        if not (self.request.user.is_authenticated or tokenauth):
            self.request.session["issue"] = obj.id
            self.request.session["created"] = created
            self.request.session["domain"] = domain.id
            login_url = reverse("account_login")
            messages.success(self.request, "Bug added!")
            return HttpResponseRedirect("{}?next={}".format(login_url, redirect_url))

        if tokenauth:
            self.process_issue(
                User.objects.get(id=token.user_id), obj, created, domain, True
            )
            return JsonResponse("Created", safe=False)
        else:
            self.process_issue(self.request.user, obj, created, domain)
            return HttpResponseRedirect(self.request.META.get("HTTP_REFERER"))
        
        

    def get_context_data(self, **kwargs):
        context = super(IssueCreate, self).get_context_data(**kwargs)
        context["activities"] = Issue.objects.exclude(Q(is_hidden=True) & ~Q(user_id=self.request.user.id))[0:10]
        context["captcha_form"] = CaptchaForm()
        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)
        context["hunts"] = Hunt.objects.exclude(plan="Free")[:4]
        context["leaderboard"] = (
            User.objects.filter(
                points__created__month=datetime.now().month,
                points__created__year=datetime.now().year,
            )
            .annotate(total_score=Sum("points__score"))
            .order_by("-total_score")[:10],
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
                ret = urllib.request.urlopen("http://" + domain + "/favicon.ico")
                if ret.code == 200:
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
            Points.objects.filter(user=self.object)
            .aggregate(total_score=Sum("score"))
            .values()
        )[0]
        context["websites"] = (
            Domain.objects.filter(issue__user=self.object)
            .annotate(total=Count("issue"))
            .order_by("-total")
        )
        context["activities"] = Issue.objects.filter(user=self.object, hunt=None).exclude(
            Q(is_hidden=True) & ~Q(user_id=self.request.user.id))[0:10]
        context["profile_form"] = UserProfileForm()
        context["total_open"] = Issue.objects.filter(
            user=self.object, status="open"
        ).count()
        context["total_closed"] = Issue.objects.filter(
            user=self.object, status="closed"
        ).count()
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
        context["total_bugs"] = Issue.objects.filter(
            user=self.object, hunt=None
        ).count()
        for i in range(0, 7):
            context["bug_type_" + str(i)] = Issue.objects.filter(
                user=self.object, hunt=None, label=str(i))

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
        context['issues_hidden'] = "checked" if user.userprofile.issues_hidden else "!checked"
        return context

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        form = UserProfileForm(
            request.POST, request.FILES, instance=request.user.userprofile
        )
        if request.FILES.get("user_avatar") and form.is_valid():
            form.save()
        else:
            hide = True if request.POST.get('issues_hidden')=='on' else False
            user_issues = Issue.objects.filter(user=request.user)
            user_issues.update(is_hidden=hide)
            request.user.userprofile.issues_hidden=hide
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
            Points.objects.filter(user=self.object)
            .aggregate(total_score=Sum("score"))
            .values()
        )[0]
        context["websites"] = (
            Domain.objects.filter(issue__user=self.object)
            .annotate(total=Count("issue"))
            .order_by("-total")
        )
        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)
        context["activities"] = Issue.objects.filter(user=self.object, hunt=None).exclude(
            Q(is_hidden=True) & ~Q(user_id=self.request.user.id))[0:10]
        context["profile_form"] = UserProfileForm()
        context["total_open"] = Issue.objects.filter(
            user=self.object, status="open"
        ).count()
        context["user_details"] = UserProfile.objects.get(user=self.object)
        context["total_closed"] = Issue.objects.filter(
            user=self.object, status="closed"
        ).count()
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
            ).exclude(
            Q(is_hidden=True) & ~Q(user_id=self.request.user.id))

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
        form = UserProfileForm(
            request.POST, request.FILES, instance=request.user.userprofile
        )
        if form.is_valid():
            form.save()
        return redirect(reverse("profile", kwargs={"slug": kwargs.get("slug")}))


def delete_issue(request, id):
    try:
        for token in Token.objects.all():
            if request.POST["token"] == token.key:
                request.user = User.objects.get(id=token.user_id)
                tokenauth = True
    except:
        tokenauth = False
    issue = Issue.objects.get(id=id)
    if request.user.is_superuser or request.user == issue.user:
        issue.delete()
        messages.success(request, "Issue deleted")
    if tokenauth == True:
        return JsonResponse("Deleted", safe=False)
    else:
        return redirect("/")


class DomainDetailView(ListView):
    template_name = "domain.html"
    model = Issue

    def get_context_data(self, *args, **kwargs):
        context = super(DomainDetailView, self).get_context_data(*args, **kwargs)
        context["domain"] = get_object_or_404(Domain, name=self.kwargs["slug"])

        parsed_url = urlparse("http://" + self.kwargs["slug"])

        open_issue = Issue.objects.filter(
            domain__name__contains=self.kwargs["slug"]
        ).filter(status="open", hunt=None).exclude(
            Q(is_hidden=True) & ~Q(user_id=self.request.user.id))
        close_issue = Issue.objects.filter(
            domain__name__contains=self.kwargs["slug"]
        ).filter(status="closed", hunt=None).exclude(
            Q(is_hidden=True) & ~Q(user_id=self.request.user.id))
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
        return context


class StatsDetailView(TemplateView):
    template_name = "stats.html"

    def get_context_data(self, *args, **kwargs):
        context = super(StatsDetailView, self).get_context_data(*args, **kwargs)
        
        response = requests.get(settings.EXTENSION_URL)
        soup = BeautifulSoup(response.text)
        
        stats = ""
        for item in soup.findAll("span", {"class": "e-f-ih"}):
            stats = item.attrs["title"]
        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)
        context["extension_users"] = stats.replace(" users", "")
        context["bug_count"] = Issue.objects.all().count()
        context["user_count"] = User.objects.all().count()
        context["hunt_count"] = Hunt.objects.all().count()
        context["domain_count"] = Domain.objects.all().count()
        context["user_graph"] = (
            User.objects.annotate(month=ExtractMonth("date_joined"))
            .values("month")
            .annotate(c=Count("id"))
            .order_by()
        )
        context["graph"] = (
            Issue.objects.annotate(month=ExtractMonth("created"))
            .values("month")
            .annotate(c=Count("id"))
            .order_by()
        )
        context["pie_chart"] = (
            Issue.objects.values("label").annotate(c=Count("label")).order_by()
        )
        return context


class AllIssuesView(ListView):
    paginate_by = 20
    template_name = "list_view.html"

    def get_queryset(self):
        username = self.request.GET.get("user")
        if username is None:
            self.activities = Issue.objects.filter(hunt=None).exclude(
                Q(is_hidden=True) & ~Q(user_id=self.request.user.id))
        else:
            self.activities = Issue.objects.filter(user__username=username,
            hunt=None).exclude(Q(is_hidden=True) & ~Q(user_id=self.request.user.id))
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
           context["activity_screenshots"][activity] = IssueScreenshot.objects.filter(issue=activity).first()
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
                Q(is_hidden=True) & ~Q(user_id = self.request.user.id))
        elif statu != "none":
            self.activities = Issue.objects.filter(
                user__username=username, status=statu, hunt=None
            ).exclude(Q(is_hidden=True) & ~Q(
                user_id = self.request.user.id))
        else:
            self.activities = Issue.objects.filter(
                user__username=username, label=query, hunt=None
            ).exclude(Q(is_hidden=True) & ~Q(user_id = self.request.user.id))
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

class LeaderboardBase():
    '''
        get:
            1) ?monthly=true will give list of winners for current month
            2) ?year=2022 will give list of winner of every month from month 1-12 else None

    '''      
    def get_leaderboard(self,month=None,year=None,api=False):
        '''
            all user scores for specified month and year
        '''
        
        data = User.objects

        if year and not month:
            data = data.filter(points__created__year=year)

        if year and month:
            data = data.filter(
                Q(points__created__year=year) &
                Q(points__created__month=month)
                )

        
        data = (
                    data
                    .annotate(total_score=Sum('points__score'))
                    .order_by('-total_score')
                    .filter(
                        total_score__gt=0,
                    )
                )
        if api:
            return data.values('id','username','total_score')

        return data
    

    def current_month_leaderboard(self,api=False):
        '''
            leaderboard which includes current month users scores
        '''
        return (
            self.get_leaderboard(
                month=int(datetime.now().month),
                year=int(datetime.now().year),
                api=api
            )
        )

    def monthly_year_leaderboard(self,year,api=False):

        '''
            leaderboard which includes current year top user from each month
        '''

        monthly_winner = []

        # iterating over months 1-12
        for month in range(1,13):
            month_winner = self.get_leaderboard(month,year,api).first()
            monthly_winner.append(month_winner)
        
        return monthly_winner

class GlobalLeaderboardView(LeaderboardBase,ListView):

    '''
        Returns: All users:score data in descending order 
    '''

    
    model = User
    template_name = "leaderboard_global.html"

    def get_context_data(self, *args, **kwargs):      
        context = super(GlobalLeaderboardView, self).get_context_data(*args, **kwargs)

        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)
        context["leaderboard"] = self.get_leaderboard()
        return context


class EachmonthLeaderboardView(LeaderboardBase,ListView):

    '''
        Returns: Grouped user:score data in months for current year
    '''

    model = User
    template_name = "leaderboard_eachmonth.html"

    def get_context_data(self, *args, **kwargs):
        
        context = super(EachmonthLeaderboardView, self).get_context_data(*args, **kwargs)

        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)

        year = self.request.GET.get("year")

        if not year: year = datetime.now().year

        if isinstance(year,str) and not year.isdigit():
            raise Http404(f"Invalid query passed | Year:{year}")
        
        year = int(year)

        leaderboard = self.monthly_year_leaderboard(year)
        month_winners = []

        months = ["January","February","March","April","May","June","July","August","September","October","Novermber","December"]

        for month_indx,usr in enumerate(leaderboard):
            
            
            month_winner = {"user":usr,"month":months[month_indx]}
            month_winners.append(month_winner)

        context["leaderboard"] = month_winners

        return context

class SpecificMonthLeaderboardView(LeaderboardBase,ListView):

    '''
        Returns: leaderboard for filtered month and year requested in the query 
    '''

    model = User
    template_name = "leaderboard_specific_month.html"

    def get_context_data(self, *args, **kwargs):
       
        context = super(SpecificMonthLeaderboardView, self).get_context_data(*args, **kwargs)

        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)

        month = self.request.GET.get("month")
        year = self.request.GET.get("year")

        if not month: month = datetime.now().month
        if not year: year = datetime.now().year

        if isinstance(month,str) and not month.isdigit():
            raise Http404(f"Invalid query passed | Month:{month}")
        if isinstance(year,str) and not year.isdigit():
            raise Http404(f"Invalid query passed | Year:{year}")
        
        month = int(month)
        year = int(year)

        if not (month>=1 and month<=12):
            raise Http404(f"Invalid query passed | Month:{month}")

        context["leaderboard"] = self.get_leaderboard(month,year,api=False)
        return context


class ScoreboardView(ListView):
    model = Domain
    template_name = "scoreboard.html"
    paginate_by = 20

    def get_context_data(self, *args, **kwargs):
        context = super(ScoreboardView, self).get_context_data(*args, **kwargs)
        companies = sorted(Domain.objects.all(), key=lambda t: t.open_issues.count(), reverse = True)

        #companies = Domain.objects.all().order_by("-open_issues")
        paginator = Paginator(companies, self.paginate_by)
        page = self.request.GET.get("page")

        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)
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
            "issues": Issue.objects.filter(Q(description__icontains=query),
             hunt=None).exclude(Q(is_hidden=True) & ~Q(user_id=request.user.id))[
                0:20
            ],
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
            "users": UserProfile.objects.filter(
                Q(user__username__icontains=query), hunt=None
            )
            .annotate(total_score=Sum("user__points__score"))
            .order_by("-total_score")[0:20],
        }
    elif stype == "label":
        context = {
            "query": query,
            "type": stype,
            "issues": Issue.objects.filter(Q(label__icontains=query),
            hunt=None).exclude(Q(is_hidden=True) & ~Q(user_id=request.user.id))[0:20],
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
        context = {
            "query": query,
            "type": stype,
            "issues": Issue.objects.filter(Q(description__icontains=query),
            hunt=None).exclude(Q(is_hidden=True) & ~Q(user_id=request.user.id))[
                0:20
            ],
        }
    if request.user.is_authenticated:
        context["wallet"] = Wallet.objects.get(user=request.user)
    issues = serializers.serialize("json", context["issues"])
    issues = json.loads(issues)
    return HttpResponse(json.dumps({"issues": issues}), content_type="application/json")


class HuntCreate(CreateView):
    model = Hunt
    fields = ["url", "logo", "name", "description","prize", "plan"]
    template_name = "hunt.html"

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.user

        domain, created = Domain.objects.get_or_create(
            name=self.request.POST.get('url').replace("www.", ""),
            defaults={"url": "http://" + self.request.POST.get('url').replace("www.", "")},
        )
        self.object.domain = domain

        self.object.save()
        return super(HuntCreate, self).form_valid(form)

    def get_success_url(self):
        
        # return reverse('start_hunt')

        if self.request.POST.get("plan") == "Ant":
            return "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=TSZ84RQZ8RKKC"
        if self.request.POST.get("plan") == "Wasp":
            return "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=E3EELQQ6JLXKY"
        if self.request.POST.get("plan") == "Scorpion":
            return "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=9R3LPM3ZN8KCC"
        return "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=HH7MNY6KJGZFW"


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
        try:
            if self.request.user.is_authenticated:
                try:
                    objectget = IP.objects.get(
                        user=self.request.user, issuenumber=self.object.id
                    )
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
        except:
            messages.error(self.request, "That issue was not found.")
            return redirect("/")
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
        context["issue_count"] = Issue.objects.filter(
            url__contains=self.object.domain_name
        ).count()
        context["all_comment"] = self.object.comments.all
        context["all_users"] = User.objects.all()
        context["likes"] = UserProfile.objects.filter(issue_upvoted=self.object).count()
        context["likers"] = UserProfile.objects.filter(issue_upvoted=self.object)

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
            if (
                not link in new_urls
                and not link in processed_urls
                and link.find(domain_name) > 0
            ):
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
            except Exception as e:
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
                    "name": issue.user.username,
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
        send_mail(
            subject, msg_plain, mailer, [issue.domain.email], html_message=msg_html
        )
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


class CreateInviteFriend(CreateView):
    template_name = "invite_friend.html"
    model = InviteFriend
    form_class = FormInviteFriend
    success_url = reverse_lazy("invite_friend")

    def form_valid(self, form):
        from django.conf import settings
        from django.contrib.sites.shortcuts import get_current_site

        instance = form.save(commit=False)
        instance.sender = self.request.user
        instance.save()

        site = get_current_site(self.request)

        mail_status = send_mail(
            "Inivtation to {site} from {user}".format(
                site=site.name, user=self.request.user.username
            ),
            "You have been invited by {user} to join {site} community.".format(
                user=self.request.user.username, site=site.name
            ),
            settings.DEFAULT_FROM_EMAIL,
            [instance.recipient],
        )

        if (
            mail_status
            and InviteFriend.objects.filter(sender=self.request.user).count() == 2
        ):
            Points.objects.create(user=self.request.user, score=1)
            InviteFriend.objects.filter(sender=self.request.user).delete()

        messages.success(
            self.request,
            "An email has been sent to your friend. Keep inviting your friends and get points!",
        )
        return HttpResponseRedirect(self.success_url)


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
def like_issue(request, issue_pk):
    context = {}
    issue_pk = int(issue_pk)
    issue = Issue.objects.get(pk=issue_pk)
    userprof = UserProfile.objects.get(user=request.user)
    if userprof in UserProfile.objects.filter(issue_upvoted=issue):
        userprof.issue_upvoted.remove(issue)
    else:
        userprof.issue_upvoted.add(issue)
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

    userprof.save()
    total_votes = UserProfile.objects.filter(issue_upvoted=issue).count()
    context["object"] = issue
    context["likes"] = total_votes
    return render(request, "_likes.html", context)


@login_required(login_url="/accounts/login")
def save_issue(request, issue_pk):
    issue_pk = int(issue_pk)
    issue = Issue.objects.get(pk=issue_pk)
    userprof = UserProfile.objects.get(user=request.user)
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
    users = list()
    temp_users = (
        User.objects.annotate(total_score=Sum("points__score"))
        .order_by("-total_score")
        .filter(total_score__gt=0)
    )
    rank_user = 1
    for each in temp_users.all():
        temp = dict()
        temp["rank"] = rank_user
        temp["id"] = each.id
        temp["User"] = each.username
        temp["score"] = Points.objects.filter(user=each.id).aggregate(
            total_score=Sum("score")
        )
        temp["image"] = list(
            UserProfile.objects.filter(user=each.id).values("user_avatar")
        )[0]
        temp["title_type"] = list(
            UserProfile.objects.filter(user=each.id).values("title")
        )[0]
        temp["follows"] = list(
            UserProfile.objects.filter(user=each.id).values("follows")
        )[0]
        temp["savedissue"] = list(
            UserProfile.objects.filter(user=each.id).values("issue_saved")
        )[0]
        rank_user = rank_user + 1
        users.append(temp)
    return JsonResponse(users, safe=False)


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


def issue_count(request):
    open_issue = Issue.objects.filter(status="open").count()
    close_issue = Issue.objects.filter(status="closed").count()
    return JsonResponse({"open": open_issue, "closed": close_issue}, safe=False)

def contributors(request):
    contributors_file_path = os.path.join(settings.BASE_DIR,"contributors.json")

    with open(contributors_file_path,'r') as file:
        content = file.read()
    
    contributors_data = json.loads(content)
    return JsonResponse({"contributors": contributors_data})


def get_scoreboard(request):
    from PIL import Image

    scoreboard = list()
    temp_domain = Domain.objects.all()
    for each in temp_domain:
        temp = dict()
        temp["name"] = each.name
        temp["open"] = len(each.open_issues)
        temp["closed"] = len(each.closed_issues)
        temp["modified"] = each.modified
        temp["logo"] = each.logo
        if each.top_tester == None:
            temp["top"] = "None"
        else:
            temp["top"] = each.top_tester.username
        scoreboard.append(temp)
    paginator = Paginator(scoreboard, 10)
    domain_list = list()
    for data in scoreboard:
        domain_list.append(data)
    count = (Paginator(scoreboard, 10).count) % 10
    for i in range(10 - count):
        domain_list.append(None)
    temp = dict()
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
                        timedelta(
                            hours=int(int(offset) / 60), minutes=int(int(offset) % 60)
                        )
                    )
                    end_date = end_date - (
                        timedelta(
                            hours=int(int(offset) / 60), minutes=int(int(offset) % 60)
                        )
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
                hunt = self.model.objects.filter(
                    is_published=False, domain=domain_admin.domain
                )
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
                hunts = self.model.objects.filter(
                    is_published=True, domain=domain_admin.domain
                )
            new_hunt = list()
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
                hunts = self.model.objects.filter(
                    is_published=True, domain=domain_admin.domain
                )
            new_hunt = list()
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
                hunts = self.model.objects.filter(
                    is_published=True, domain=domain_admin.domain
                )
            new_hunt = list()
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
        form = UserProfileForm(
            request.POST, request.FILES, instance=request.user.userprofile
        )
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
        form = UserProfileForm(
            request.POST, request.FILES, instance=request.user.userprofile
        )
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
                        domain_admin.domain = Domain.objects.get(
                            pk=request.POST["domain@" + value]
                        )
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
                company.subscription = Subscription.objects.get(
                    name=request.POST["subscription"]
                )
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
def company_dashboard_domain_detail(
    request, pk, template="company_dashboard_domain_detail.html"
):
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
def company_dashboard_hunt_detail(
    request, pk, template="company_dashboard_hunt_detail.html"
):
    hunt = get_object_or_404(Hunt, pk=pk)
    return render(request, template, {"hunt": hunt})


@login_required(login_url="/accounts/login")
def company_dashboard_hunt_edit(
    request, pk, template="company_dashboard_hunt_edit.html"
):
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
                if account.payouts_enabled == True:
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
                    return JsonResponse(
                        {"redirect": account_links.url, "status": "success"}
                    )
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
                return JsonResponse(
                    {"redirect": account_links.url, "status": "success"}
                )
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
    if account.payouts_enabled == True:
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
        time_remaining = humanize.naturaltime(
            datetime.now(timezone.utc) - hunt.starts_on
        )
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
                    Q(is_hidden=True) & ~Q(user_id=request.user.id))
                return render(
                    request, template, {"hunt": hunt, "issue_list": issue_list}
                )
            parsed_url = urlparse(url)
            if parsed_url.scheme == "":
                url = "https://" + url
            parsed_url = urlparse(url)
            if parsed_url.netloc == "":
                issue_list = Issue.objects.filter(user=request.user, hunt=hunt).exclude(
                    Q(is_hidden=True) & ~Q(user_id=request.user.id))
                return render(
                    request, template, {"hunt": hunt, "issue_list": issue_list}
                )
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

                    request.FILES["screenshot"] = ContentFile(
                        decoded_file, name=complete_file_name
                    )
            issue = Issue()
            issue.label = label
            issue.url = url
            issue.user = request.user
            issue.description = description
            try:
                issue.screenshot = request.FILES["screenshot"]
            except:
                issue_list = Issue.objects.filter(user=request.user, hunt=hunt).exclude(
                    Q(is_hidden=True) & ~Q(user_id=request.user.id))
                return render(
                    request, template, {"hunt": hunt, "issue_list": issue_list}
                )
            issue.hunt = hunt
            issue.save()
            issue_list = Issue.objects.filter(user=request.user, hunt=hunt).exclude(
                Q(is_hidden=True) & ~Q(user_id=request.user.id))
            return render(request, template, {"hunt": hunt, "issue_list": issue_list})


@login_required(login_url="/accounts/login")
def hunt_results(request, pk, template="hunt_results.html"):
    hunt = get_object_or_404(Hunt, pk=pk)
    return render(request, template, {"hunt": hunt})


@login_required(login_url="/accounts/login")
def company_hunt_results(request, pk, template="company_hunt_results.html"):
    hunt = get_object_or_404(Hunt, pk=pk)
    issues = Issue.objects.filter(hunt=hunt).exclude(Q(is_hidden=True) & ~Q(user_id=request.user.id))
    context = {}
    if request.method == "GET":
        context["hunt"] = get_object_or_404(Hunt, pk=pk)
        context["issues"] = Issue.objects.filter(hunt=hunt).exclude(
            Q(is_hidden=True) & ~Q(user_id=request.user.id))
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
                    wallet, created = Wallet.objects.get_or_create(
                        user=winner.second_runner
                    )
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
            Q(is_hidden=True) & ~Q(user_id=request.user.id))
        return render(request, template, context)


def handler404(request, exception):
   return render(request, "404.html", {}, status=404)

def handler500(request, exception=None):
   return render(request, "500.html", {}, status=500)

def contributors_view(request,*args,**kwargs):

        

    contributors_file_path = os.path.join(settings.BASE_DIR,"contributors.json")

    with open(contributors_file_path,'r') as file:
        content = file.read()
    
    contributors = json.loads(content)

    contributor_id = request.GET.get("contributor",None)

    if contributor_id:
        
        contributor=None
        for i in contributors:
            if str(i["id"])==contributor_id:
                contributor = i
        
        if contributor==None:
            return HttpResponseNotFound("Contributor not found")
        
        return render(request,"contributors_detail.html",context={"contributor":contributor})


    context = {
        "contributors":contributors
    }

    return render(request,"contributors.html",context=context)


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
#                         if flag_word == False:
#                             url = word
#                             continue
#                         if flag_word == True:
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
#             if image == False:
#                 error = True
#             if error == True:
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
