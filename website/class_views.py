import base64
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import urlparse

import requests
import six
import stripe
import tweepy
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
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, Q, Sum
from django.db.models.functions import ExtractMonth
from django.db.transaction import atomic
from django.http import (
    Http404,
    HttpResponse,
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
from django.views.generic import DetailView, ListView, TemplateView, View
from django.views.generic.edit import CreateView
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from user_agents import parse

from blt import settings
from website.forms import CaptchaForm, GitHubURLForm, HuntForm, UserDeleteForm, UserProfileForm
from website.models import (
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
    Tag,
    Transaction,
    User,
    UserProfile,
    Wallet,
    Winner,
)
from website.utils import (
    get_client_ip,
    get_email_from_domain,
    image_validator,
    is_valid_https_url,
    rebuild_safe_url,
)


class ProjectDetailView(DetailView):
    model = Project

    def post(self, request, *args, **kwargs):
        if "update_project" in request.POST:
            from django.core.management import call_command

            project = self.get_object()  # Use get_object() to retrieve the current object
            call_command("update_projects", "--project_id", project.pk)
            messages.success(request, "Requested refresh to projects")
            return redirect("project_view", slug=project.slug)


class ProjectListView(ListView):
    model = Project
    context_object_name = "projects"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = GitHubURLForm()
        context["sort_by"] = self.request.GET.get("sort_by", "-created")
        context["order"] = self.request.GET.get("order", "desc")
        return context

    def post(self, request, *args, **kwargs):
        if "update_projects" in request.POST:
            print("Updating projects")
            from django.core.management import call_command  # Add this import

            call_command("update_projects")
            messages.success(request, "Requested refresh to projects")
            return redirect("project_list")

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

    def get_queryset(self):
        queryset = super().get_queryset()
        sort_by = self.request.GET.get("sort_by", "-created")
        order = self.request.GET.get("order", "desc")

        if order == "asc" and sort_by.startswith("-"):
            sort_by = sort_by[1:]
        elif order == "desc" and not sort_by.startswith("-"):
            sort_by = f"-{sort_by}"

        return queryset.order_by(sort_by)


class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        return self.request.build_absolute_uri(reverse("facebook_callback"))


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


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        return self.request.build_absolute_uri(reverse("google_callback"))


class GithubLogin(SocialLoginView):
    adapter_class = GitHubOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        return self.request.build_absolute_uri(reverse("github_callback"))


class FacebookConnect(SocialConnectView):
    adapter_class = FacebookOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        return self.request.build_absolute_uri(reverse("facebook_callback"))


class GithubConnect(SocialConnectView):
    adapter_class = GitHubOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        return self.request.build_absolute_uri(reverse("github_callback"))


class GoogleConnect(SocialConnectView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        return self.request.build_absolute_uri(reverse("google_callback"))


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

        paginator = Paginator(open_issue, 3)
        page = self.request.GET.get("open")
        try:
            openissue_paginated = paginator.page(page)
        except PageNotAnInteger:
            openissue_paginated = paginator.page(1)
        except EmptyPage:
            openissue_paginated = paginator.page(paginator.num_pages)

        paginator = Paginator(close_issue, 3)
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
        for i in range(0, 7):
            context["bug_type_" + str(i)] = Issue.objects.filter(
                domain=context["domain"], hunt=None, label=str(i)
            )
        context["total_bugs"] = Issue.objects.filter(domain=context["domain"], hunt=None).count()
        context["pie_chart"] = (
            Issue.objects.filter(domain=context["domain"], hunt=None)
            .values("label")
            .annotate(c=Count("label"))
            .order_by()
        )
        context["activities"] = Issue.objects.filter(domain=context["domain"], hunt=None).exclude(
            Q(is_hidden=True) & ~Q(user_id=self.request.user.id)
        )[0:3]
        context["activity_screenshots"] = {}
        for activity in context["activities"]:
            context["activity_screenshots"][activity] = IssueScreenshot.objects.filter(
                issue=activity.pk
            ).first()
        context["twitter_url"] = "https://twitter.com/%s" % domain.get_or_set_x_url(domain.get_name)

        return context


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

        context["sparklines_data"] = [
            get_cumulative_data(Issue.objects),
            get_cumulative_data(User.objects, date_field="date_joined"),
            get_cumulative_data(Hunt.objects),
            get_cumulative_data(Domain.objects),
            get_cumulative_data(Subscription.objects),
            get_cumulative_data(Company.objects),
            get_cumulative_data(HuntPrize.objects),
            get_cumulative_data(IssueScreenshot.objects),
            get_cumulative_data(Winner.objects),
            get_cumulative_data(Points.objects),
            get_cumulative_data(InviteFriend.objects),
            get_cumulative_data(UserProfile.objects),
            get_cumulative_data(IP.objects),
            get_cumulative_data(CompanyAdmin.objects),
            get_cumulative_data(Transaction.objects),
            get_cumulative_data(Payment.objects),
            get_cumulative_data(ContributorStats.objects),
            get_cumulative_data(Monitor.objects),
            get_cumulative_data(Bid.objects),
            get_cumulative_data(ChatBotLog.objects),
            get_cumulative_data(Suggestion.objects),
            get_cumulative_data(SuggestionVotes.objects),
            get_cumulative_data(Contributor.objects),
            get_cumulative_data(Project.objects),
            get_cumulative_data(Contribution.objects),
            get_cumulative_data(BaconToken.objects),
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
    def get_leaderboard(self, month=None, year=None, api=False):
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


class CustomObtainAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        response = super(CustomObtainAuthToken, self).post(request, *args, **kwargs)
        token = Token.objects.get(key=response.data["token"])
        return Response({"token": token.key, "id": token.user_id})


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
