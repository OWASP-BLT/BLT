import ipaddress
import json
import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, Prefetch, Q, Sum
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.utils.timezone import now
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, FormView, ListView, TemplateView, View
from django.views.generic.edit import CreateView
from rest_framework import status
from rest_framework.authtoken.models import Token

from website.forms import CaptchaForm, HuntForm, IpReportForm, RoomForm, UserProfileForm
from website.models import (
    IP,
    Activity,
    DailyStatusReport,
    Domain,
    GitHubIssue,
    Hunt,
    IpReport,
    Issue,
    IssueScreenshot,
    Message,
    Organization,
    OrganizationAdmin,
    Repo,
    Room,
    Subscription,
    Tag,
    TimeLog,
    Trademark,
    UserBadge,
    Wallet,
    Winner,
)
from website.services.blue_sky_service import BlueSkyService
from website.utils import format_timedelta, get_client_ip, get_github_issue_title

logger = logging.getLogger(__name__)


def add_domain_to_organization(request):
    if request.method == "POST":
        try:
            domain = Domain.objects.get(id=request.POST.get("domain"))
            organization_name = request.POST.get("organization")
            organization = Organization.objects.filter(name=organization_name).first()

            if not organization:
                url = domain.url
                if not url.startswith(("http://", "https://")):
                    url = "http://" + url

                # SSRF Protection: Validate the URL before making the request
                parsed_url = urlparse(url)
                hostname = parsed_url.netloc.split(":")[0]

                # Check if hostname is a private/internal address
                is_private = False

                # Check for localhost and special domains
                private_domains = [".local", ".internal", ".localhost"]
                if hostname == "localhost" or any(hostname.endswith(domain) for domain in private_domains):
                    is_private = True

                # Try to parse as IP address
                if not is_private:
                    try:
                        ip = ipaddress.ip_address(hostname)
                        # Check if IP is private
                        is_private = ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local
                    except ValueError:
                        # Not a valid IP address, continue with hostname checks
                        pass

                if is_private:
                    messages.error(request, "Invalid domain: Cannot use internal or private addresses")
                    return redirect("domain", slug=domain.url)

                try:
                    response = requests.get(url, timeout=5)
                    soup = BeautifulSoup(response.text, "html.parser")
                    if organization_name in soup.get_text():
                        organization = Organization.objects.create(name=organization_name)
                        domain.organization = organization
                        domain.save()
                        messages.success(request, "Organization added successfully")
                        return redirect("domain", slug=domain.url)
                    else:
                        messages.error(request, "Organization not found in the domain")
                        return redirect("domain", slug=domain.url)
                except requests.RequestException:
                    messages.error(request, "Could not connect to the domain")
                    return redirect("domain", slug=domain.url)
            else:
                domain.organization = organization
                domain.save()
                messages.success(request, "Organization added successfully")
                return redirect("domain", slug=domain.url)
        except Domain.DoesNotExist:
            messages.error(request, "Domain does not exist")
            return redirect("home")
        except requests.RequestException:
            messages.error(request, "Could not connect to the domain")
            return redirect("home")
    else:
        return redirect("home")


@login_required(login_url="/accounts/login")
def organization_dashboard(request, template="index_organization.html"):
    try:
        organization_admin = OrganizationAdmin.objects.get(user=request.user)
        if not organization_admin.is_active:
            return HttpResponseRedirect("/")
        hunts = Hunt.objects.filter(is_published=True, domain=organization_admin.domain)
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
    except OrganizationAdmin.DoesNotExist:
        return redirect("/")


@login_required(login_url="/accounts/login")
def admin_organization_dashboard(request, template="admin_dashboard_organization.html"):
    user = request.user
    if user.is_superuser:
        if not user.is_active:
            return HttpResponseRedirect("/")
        organization = Organization.objects.all()
        context = {"organizations": organization}
        return render(request, template, context)
    else:
        return redirect("/")


@login_required(login_url="/accounts/login")
def admin_organization_dashboard_detail(request, pk, template="admin_dashboard_organization_detail.html"):
    user = request.user
    if user.is_superuser:
        if not user.is_active:
            return HttpResponseRedirect("/")
        organization = get_object_or_404(Organization, pk=pk)
        return render(request, template, {"organization": organization})
    else:
        return redirect("/")


def weekly_report(request):
    domains = Domain.objects.all()
    report_data = ["Hey This is a weekly report from OWASP BLT regarding the bugs reported for your organization!"]
    try:
        for domain in domains:
            open_issues = domain.open_issues
            closed_issues = domain.closed_issues
            total_issues = open_issues.count() + closed_issues.count()
            issues = Issue.objects.filter(domain=domain)
            email = domain.email
            report_data.append(
                "Hey This is a weekly report from OWASP BLT regarding the bugs reported for your organization!"
                f"\n\norganization Name: {domain.name}"
                f"Open issues: {open_issues.count()}"
                f"Closed issues: {closed_issues.count()}"
                f"Total issues: {total_issues}"
            )
            for issue in issues:
                description = issue.description
                views = issue.views
                label = issue.get_label_display()
                report_data.append(f"\n Description: {description} \n Views: {views} \n Labels: {label} \n")

        report_string = "".join(report_data)
        send_mail(
            "Weekly Report!!!",
            report_string,
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )
    except Exception as e:
        return HttpResponse(f"An error occurred while sending the weekly report: {str(e)}")

    return HttpResponse("Weekly report sent successfully.")


@login_required(login_url="/accounts/login")
def organization_hunt_results(request, pk, template="organization_hunt_results.html"):
    hunt = get_object_or_404(Hunt, pk=pk)
    issues = (
        Issue.objects.filter(hunt=hunt).exclude(Q(is_hidden=True) & ~Q(user_id=request.user.id)).order_by("-created")
    )

    context = {}
    if request.method == "GET":
        context["hunt"] = hunt
        context["issues"] = issues
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
                except KeyError:
                    pass
                issue.save()

        if request.POST["submit"] == "save":
            pass
        elif request.POST["submit"] == "publish":
            issue.save()
            winner = Winner()
            issue_with_score = (
                Issue.objects.filter(hunt=hunt, verified=True)
                .values("user")
                .order_by("user")
                .annotate(total_score=Sum("score"))
            )

            for index, obj in enumerate(issue_with_score, 1):
                user = User.objects.get(pk=obj["user"])
                if index == 1:
                    winner.winner = user
                elif index == 2:
                    winner.runner = user
                elif index == 3:
                    winner.second_runner = user
                elif index == 4:
                    break

            winner.prize_distributed = True
            winner.hunt = hunt
            winner.save()
            hunt.result_published = True
            hunt.save()
            context["winner"] = winner

        context["hunt"] = hunt
        context["issues"] = issues
        return render(request, template, context)


class DomainListView(ListView):
    model = Domain
    paginate_by = 100
    template_name = "domain_list.html"

    def get_queryset(self):
        return Domain.objects.all().order_by("-created")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        domain = self.get_queryset()

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


class DomainList(TemplateView):
    model = Domain
    template_name = "organization_domain_lists.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        domain_admin = OrganizationAdmin.objects.get(user=request.user)
        if not domain_admin.is_active:
            return HttpResponseRedirect("/")
        domain = []
        if domain_admin.role == 0:
            domain = self.model.objects.filter(organization=domain_admin.organization).order_by("-created")
        else:
            domain = self.model.objects.filter(pk=domain_admin.domain.pk).order_by("-created")
        context = {"domains": domain}
        return render(request, self.template_name, context)


class Joinorganization(TemplateView):
    model = Organization
    template_name = "join.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        organization_name = request.GET.get("organization", "")
        context = {"wallet": wallet, "organization_name": organization_name}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        name = request.POST["organization"]
        try:
            Organization.objects.get(name=name)
            return JsonResponse({"status": "Organization already exists"})
        except Organization.DoesNotExist:
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
                organization = Organization()
                organization.admin = request.user
                organization.name = name
                organization.url = url
                organization.email = email
                organization.subscription = sub
                organization.save()
                admin = OrganizationAdmin()
                admin.user = request.user
                admin.role = 0
                admin.organization = organization
                admin.is_active = True
                admin.save()
                return JsonResponse(
                    {
                        "status": "Success",
                        "redirect_url": reverse("organization_detail", kwargs={"slug": organization.slug}),
                    }
                )
            elif paymentType == "card":
                organization = Organization()
                organization.admin = request.user
                organization.name = name
                organization.url = url
                organization.email = email
                organization.subscription = sub
                organization.save()
                admin = OrganizationAdmin()
                admin.user = request.user
                admin.role = 0
                admin.organization = organization
                admin.is_active = True
                admin.save()
                return JsonResponse(
                    {
                        "status": "Success",
                        "redirect_url": reverse("organization_detail", kwargs={"slug": organization.slug}),
                    }
                )
            else:
                return JsonResponse({"status": "There was some error"})


class Listbounties(TemplateView):
    model = Hunt
    template_name = "bounties_list.html"

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

        filtered_Bug Bountys = {
            "all": hunts,
            "ongoing": hunts.filter(result_published=False, is_published=True),
            "ended": hunts.filter(result_published=True),
            "draft": hunts.filter(result_published=False, is_published=False),
        }

        hunts = filtered_Bug Bountys.get(hunt_type, hunts)

        if search.strip():
            hunts = hunts.filter(Q(name__icontains=search))

        if start_date:
            start_date = datetime.strptime(start_date, "%m/%d/%Y").strftime("%Y-%m-%d %H:%M")
            hunts = hunts.filter(starts_on__gte=start_date)

        if end_date:
            end_date = datetime.strptime(end_date, "%m/%d/%Y").strftime("%Y-%m-%d %H:%M")
            hunts = hunts.filter(end_on__gte=end_date)

        if domain and domain != "Select Domain":
            domain = Domain.objects.filter(id=domain).first()
            hunts = hunts.filter(domain=domain)

        # Fetch GitHub issues with $5 label for first page
        issue_state = request.GET.get("issue_state", "open")

        try:
            github_issues = self.github_issues_with_bounties("$5", issue_state=issue_state)

            # For closed issues, fetch related PRs from database
            if issue_state == "closed":
                for issue in github_issues:
                    issue_number = issue.get("number")

                    try:
                        related_prs = []
                        prs = GitHubIssue.objects.filter(
                            type="pull_request",
                            is_merged=True,
                            body__iregex=r"([Cc]loses|[Ff]ixes|[Rr]esolves|[Cc]lose|[Ff]ix|[Ff]fixed|[Cc]losed|[Rr]esolve|[Rr]esolved)\s+#"
                            + str(issue_number),
                        ).order_by("-merged_at")[:3]

                        for pr in prs:
                            related_prs.append(
                                {
                                    "number": pr.issue_id,
                                    "title": pr.title,
                                    "url": pr.url,
                                    "user": pr.user_profile.user.username
                                    if pr.user_profile and pr.user_profile.user
                                    else None,
                                }
                            )

                        issue["related_prs"] = related_prs
                    except Exception as e:
                        logger.error(f"Error fetching PRs from database for issue #{issue_number}: {str(e)}")
                        issue["related_prs"] = []
        except Exception as e:
            logger.error(f"Error fetching GitHub issues: {str(e)}")
            github_issues = []

        context = {
            "hunts": hunts,
            "domains": Domain.objects.values("id", "name").all(),
            "github_issues": github_issues,
            "current_page": 1,
            "selected_issue_state": issue_state,
        }

        return render(request, self.template_name, context)

    def github_issues_with_bounties(self, label, issue_state="open", page=1, per_page=10):
        cache_key = f"github_issues_{label}_{issue_state}_page_{page}"
        cached_issues = cache.get(cache_key)

        if cached_issues is not None:
            return cached_issues

        params = {"labels": label, "state": issue_state, "per_page": per_page, "page": page}

        headers = {}
        github_token = getattr(settings, "GITHUB_API_TOKEN", None)
        if github_token:
            headers["Authorization"] = f"token {github_token}"

        try:
            response = requests.get(
                "https://api.github.com/repos/OWASP-BLT/BLT/issues", params=params, headers=headers, timeout=5
            )

            response.raise_for_status()

            issues = response.json()
            formatted_issues = []

            for issue in issues:
                related_prs = []

                # Only include issues, not PRs in the response
                if issue.get("pull_request") is None:
                    formatted_issue = {
                        "id": issue.get("id"),
                        "number": issue.get("number"),
                        "title": issue.get("title"),
                        "url": issue.get("html_url"),
                        "repository": "OWASP-BLT/BLT",
                        "created_at": issue.get("created_at"),
                        "updated_at": issue.get("updated_at"),
                        "labels": [label.get("name") for label in issue.get("labels", [])],
                        "user": issue.get("user", {}).get("login") if issue.get("user") else None,
                        "state": issue.get("state"),
                        "related_prs": related_prs,
                        "closed_at": issue.get("closed_at"),
                    }

                    formatted_issues.append(formatted_issue)

            # Cache for 5 minutes
            cache.set(cache_key, formatted_issues, timeout=300)
            return formatted_issues

        except requests.RequestException as e:
            logger.error(f"GitHub API request failed: {str(e)}")
            return []


def load_more_issues(request):
    page = int(request.GET.get("page", 1))
    state = request.GET.get("state", "open")

    try:
        view = Listbounties()
        issues = view.github_issues_with_bounties("$5", issue_state=state, page=page)

        # For closed issues, fetch related PRs from database for other than first batch of issues
        if issues and state == "closed":
            for issue in issues:
                issue_number = issue.get("number")

                try:
                    related_prs = []
                    prs = GitHubIssue.objects.filter(
                        type="pull_request",
                        is_merged=True,
                        body__iregex=r"([Cc]loses|[Ff]ixes|[Rr]esolves|[Cc]lose|[Ff]ix|[Ff]fixed|[Cc]losed|[Rr]esolve|[Rr]esolved)\s+#"
                        + str(issue_number),
                    ).order_by("-merged_at")[:3]

                    for pr in prs:
                        related_prs.append(
                            {
                                "number": pr.issue_id,
                                "title": pr.title,
                                "url": pr.url,
                                "user": pr.user_profile.user.username
                                if pr.user_profile and pr.user_profile.user
                                else None,
                            }
                        )

                    issue["related_prs"] = related_prs
                except Exception as e:
                    logger.error(f"Error fetching PRs from database for issue #{issue_number}: {str(e)}")
                    issue["related_prs"] = []

        return JsonResponse({"success": True, "issues": issues, "next_page": page + 1 if issues else None})
    except Exception as e:
        logger.error(f"Error loading more issues: {str(e)}")
        return JsonResponse({"success": False, "error": "An unexpected error occurred."})


class DraftHunts(TemplateView):
    model = Hunt
    fields = ["url", "logo", "domain", "plan", "prize", "txn_id"]
    template_name = "hunt_drafts.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        try:
            domain_admin = OrganizationAdmin.objects.get(user=request.user)
            if not domain_admin.is_active:
                return HttpResponseRedirect("/")
            if domain_admin.role == 0:
                hunt = self.model.objects.filter(is_published=False)
            else:
                hunt = self.model.objects.filter(is_published=False, domain=domain_admin.domain)
            context = {"hunts": hunt}
            return render(request, self.template_name, context)
        except OrganizationAdmin.DoesNotExist:
            return HttpResponseRedirect("/")


class UpcomingHunts(TemplateView):
    model = Hunt
    fields = ["url", "logo", "domain", "plan", "prize", "txn_id"]
    template_name = "hunt_upcoming.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        try:
            domain_admin = OrganizationAdmin.objects.get(user=request.user)
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
        except OrganizationAdmin.DoesNotExist:
            return HttpResponseRedirect("/")


class OngoingHunts(TemplateView):
    model = Hunt
    fields = ["url", "logo", "domain", "plan", "prize", "txn_id"]
    template_name = "hunt_ongoing.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        try:
            domain_admin = OrganizationAdmin.objects.get(user=request.user)
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
        except OrganizationAdmin.DoesNotExist:
            return HttpResponseRedirect("/")


class PreviousHunts(TemplateView):
    model = Hunt
    fields = ["url", "logo", "domain", "plan", "prize", "txn_id"]
    template_name = "hunt_previous.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        try:
            domain_admin = OrganizationAdmin.objects.get(user=request.user)
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
        except OrganizationAdmin.DoesNotExist:
            return HttpResponseRedirect("/")

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
        if form.is_valid():
            form.save()
        return redirect(reverse("profile", kwargs={"slug": kwargs.get("slug")}))


class OrganizationSettings(TemplateView):
    model = OrganizationAdmin
    fields = ["user", "domain", "role", "is_active"]
    template_name = "organization_settings.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        try:
            domain_admin = OrganizationAdmin.objects.get(user=request.user)
            if not domain_admin.is_active:
                return HttpResponseRedirect("/")
            domain_admins = []
            domain_list = Domain.objects.filter(organization=domain_admin.organization)
            if domain_admin.role == 0:
                domain_admins = OrganizationAdmin.objects.filter(organization=domain_admin.organization, is_active=True)
            else:
                domain_admins = OrganizationAdmin.objects.filter(domain=domain_admin.domain, is_active=True)
            context = {
                "admins": domain_admins,
                "user": domain_admin,
                "domain_list": domain_list,
            }
            return render(request, self.template_name, context)
        except OrganizationAdmin.DoesNotExist:
            return HttpResponseRedirect("/")

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
        if form.is_valid():
            form.save()
        return redirect(reverse("profile", kwargs={"slug": kwargs.get("slug")}))


class DomainDetailView(ListView):
    template_name = "domain.html"
    model = Issue
    paginate_by = 3

    def get_domain_from_slug(self, slug):
        """Helper method to find domain from a slug that might be a URL."""
        if not slug:
            raise Http404("No domain specified")

        # Clean the slug
        slug = slug.strip().lower()

        # First try direct name match
        try:
            return Domain.objects.get(name=slug)
        except Domain.DoesNotExist:
            pass

        # Try to parse as URL
        if "//" not in slug:
            slug = "http://" + slug

        try:
            parsed = urlparse(slug)
            hostname = parsed.netloc or parsed.path
            # Remove www. prefix if present
            hostname = hostname.replace("www.", "")
            # Remove any remaining path components
            hostname = hostname.split("/")[0]

            # Try to find domain by name or URL
            try:
                return Domain.objects.get(name=hostname)
            except Domain.DoesNotExist:
                try:
                    return Domain.objects.get(url__icontains=hostname)
                except Domain.DoesNotExist:
                    # Try one last time with the original slug
                    try:
                        return Domain.objects.get(url__icontains=slug)
                    except Domain.DoesNotExist:
                        # If we've tried everything and still can't find it, return 404
                        raise Http404(f"No domain found matching '{slug}'")
        except Http404:
            # Re-raise Http404 exceptions
            raise
        except Exception as e:
            # Log the error but return a 404 instead of propagating the exception
            logger.error(f"Error parsing domain slug '{slug}': {str(e)}")
            raise Http404("Invalid domain format")

    def get_queryset(self):
        return Issue.objects.none()  # We'll handle the queryset in get_context_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            # Get the slug and clean it
            slug = self.kwargs.get("slug", "").strip().split("?")[0]

            # Find the domain
            domain = self.get_domain_from_slug(slug)
            context["domain"] = domain

            # Get view count
            view_count = IP.objects.filter(path=self.request.path).count()
            context["view_count"] = view_count

            # Set the name for display
            context["name"] = domain.get_name or domain.name

            # Fetch the related organization
            organization = domain.organization
            if organization is None:
                organizations = Organization.objects.filter(name__iexact=domain.get_name)
                if organizations.exists():
                    organization = organizations.first()

            context["organization"] = organization

            if organization:
                # Fetch related trademarks for the organization, ordered by filing date
                trademarks = Trademark.objects.filter(organization=organization).order_by("-filing_date")
                context["trademarks"] = trademarks

            # Get open and closed issues
            open_issues = (
                Issue.objects.filter(domain=domain, status="open", hunt=None)
                .exclude(Q(is_hidden=True) & ~Q(user_id=self.request.user.id))
                .order_by("-created")
            )

            closed_issues = (
                Issue.objects.filter(domain=domain, status="closed", hunt=None)
                .exclude(Q(is_hidden=True) & ~Q(user_id=self.request.user.id))
                .order_by("-created")
            )

            if self.request.user.is_authenticated:
                context["wallet"] = Wallet.objects.get(user=self.request.user)

            # Handle pagination for open issues
            open_paginator = Paginator(open_issues, self.paginate_by)
            open_page = self.request.GET.get("open")
            try:
                openissue_paginated = open_paginator.page(open_page)
            except PageNotAnInteger:
                openissue_paginated = open_paginator.page(1)
            except EmptyPage:
                openissue_paginated = open_paginator.page(open_paginator.num_pages)

            # Handle pagination for closed issues
            closed_paginator = Paginator(closed_issues, self.paginate_by)
            closed_page = self.request.GET.get("close")
            try:
                closeissue_paginated = closed_paginator.page(closed_page)
            except PageNotAnInteger:
                closeissue_paginated = closed_paginator.page(1)
            except EmptyPage:
                closeissue_paginated = closed_paginator.page(closed_paginator.num_pages)

            context.update(
                {
                    "opened_net": open_issues,
                    "opened": openissue_paginated,
                    "closed_net": closed_issues,
                    "closed": closeissue_paginated,
                    "leaderboard": (
                        User.objects.filter(issue__domain=domain).annotate(total=Count("issue")).order_by("-total")
                    ),
                    "current_month": datetime.now().month,
                    "domain_graph": (
                        Issue.objects.filter(
                            domain=domain,
                            hunt=None,
                            created__month__gte=(datetime.now().month - 6),
                            created__month__lte=datetime.now().month,
                        ).order_by("created")
                    ),
                    "total_bugs": Issue.objects.filter(domain=domain, hunt=None).count(),
                    "pie_chart": (
                        Issue.objects.filter(domain=domain, hunt=None)
                        .values("label")
                        .annotate(c=Count("label"))
                        .order_by("label")
                    ),
                    "activities": (
                        Issue.objects.filter(domain=domain, hunt=None)
                        .exclude(Q(is_hidden=True) & ~Q(user_id=self.request.user.id))
                        .order_by("-created")
                    ),
                }
            )

            # Add bug types to context
            for i in range(0, 7):
                context[f"bug_type_{i}"] = Issue.objects.filter(domain=domain, hunt=None, label=str(i)).order_by(
                    "-created"
                )

            # Add activity screenshots
            context["activity_screenshots"] = {
                activity: IssueScreenshot.objects.filter(issue=activity.pk).first()
                for activity in context["activities"]
            }

            # Add Twitter URL
            context["twitter_url"] = f"https://twitter.com/{domain.get_or_set_x_url(domain.get_name)}"

            return context
        except Http404:
            # Re-raise Http404 exceptions directly
            raise
        except Exception as e:
            # Log the error but return a 404 instead of propagating the exception
            logger.error(f"Error in DomainDetailView: {str(e)}")
            raise Http404("Domain not found")


class ScoreboardView(ListView):
    model = Domain
    template_name = "scoreboard.html"
    paginate_by = 20
    context_object_name = "scoreboard"

    def get_queryset(self):
        sort_by = self.request.GET.get("sort_by", "open_issues_count")
        sort_order = self.request.GET.get("sort_order", "desc")

        if sort_order == "asc":
            sort_by = sort_by
        else:
            sort_by = f"-{sort_by}"

        return Domain.objects.annotate(
            open_issues_count=Count("issue", filter=Q(issue__status="open")),
            closed_issues_count=Count("issue", filter=Q(issue__status="closed")),
        ).order_by(sort_by)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["user"] = self.request.GET.get("user")
        context["sort_by"] = self.request.GET.get("sort_by", "open_issues_count")
        context["sort_order"] = self.request.GET.get("sort_order", "desc")
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
                # Try to find a matching domain first
                domain = Domain.objects.filter(email__iexact=event.get("email")).first()
                if domain:
                    domain.email_event = event.get("event")
                    if event.get("event") == "click":
                        domain.clicks = int(domain.clicks or 0) + 1
                    domain.save()

                # Try to find a matching user profile
                user = User.objects.filter(email__iexact=event.get("email")).first()
                if user and hasattr(user, "userprofile"):
                    profile = user.userprofile
                    event_type = event.get("event")

                    # Update email status and last event
                    profile.email_status = event_type
                    profile.email_last_event = event_type
                    profile.email_last_event_time = timezone.now()

                    # Handle specific event types
                    if event_type == "bounce":
                        profile.email_bounce_reason = event.get("reason", "")
                    elif event_type == "spamreport":
                        profile.email_spam_report = True
                    elif event_type == "unsubscribe":
                        profile.email_unsubscribed = True
                    elif event_type == "click":
                        profile.email_click_count = profile.email_click_count + 1
                    elif event_type == "open":
                        profile.email_open_count = profile.email_open_count + 1

                    profile.save()

            except (Domain.DoesNotExist, User.DoesNotExist, AttributeError, ValueError, json.JSONDecodeError) as e:
                logger.error(f"Error processing SendGrid webhook event: {str(e)}")

        return JsonResponse({"detail": "Inbound Sendgrid Webhook received"})


class CreateHunt(TemplateView):
    model = Hunt
    fields = ["url", "logo", "domain", "plan", "prize", "txn_id"]
    template_name = "create_hunt.html"

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        try:
            domain_admin = OrganizationAdmin.objects.get(user=request.user)
            if not domain_admin.is_active:
                return HttpResponseRedirect("/")
            domain = []
            if domain_admin.role == 0:
                domain = Domain.objects.filter(organization=domain_admin.organization)
            else:
                domain = Domain.objects.filter(pk=domain_admin.domain.pk)

            context = {"domains": domain, "hunt_form": HuntForm()}
            return render(request, self.template_name, context)
        except OrganizationAdmin.DoesNotExist:
            return HttpResponseRedirect("/")

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        try:
            domain_admin = OrganizationAdmin.objects.get(user=request.user)
            if (
                domain_admin.role == 1
                and (str(domain_admin.domain.pk) == ((request.POST["domain"]).split("-"))[0].replace(" ", ""))
            ) or domain_admin.role == 0:
                wallet, created = Wallet.objects.get_or_create(user=request.user)
                total_amount = (
                    Decimal(request.POST["prize_winner"])
                    + Decimal(request.POST["prize_runner"])
                    + Decimal(request.POST["prize_second_runner"])
                )
                if total_amount > wallet.current_balance:
                    return HttpResponse("Insufficient balance")
                hunt = Hunt()
                hunt.domain = Domain.objects.get(pk=(request.POST["domain"]).split("-")[0].replace(" ", ""))
                data = {}
                data["content"] = request.POST["content"]
                data["start_date"] = request.POST["start_date"]
                data["end_date"] = request.POST["end_date"]
                form = HuntForm(data)
                if not form.is_valid():
                    return HttpResponse("Invalid form data")
                if not domain_admin.is_active:
                    return HttpResponse("Inactive domain admin")
                if domain_admin.role == 1:
                    if hunt.domain != domain_admin.domain:
                        return HttpResponse("Domain mismatch")
                hunt.domain = Domain.objects.get(pk=(request.POST["domain"]).split("-")[0].replace(" ", ""))
                tzsign = 1
                offset = request.POST["tzoffset"]
                if int(offset) < 0:
                    offset = int(offset) * (-1)
                    tzsign = -1
                start_date = form.cleaned_data["start_date"]
                end_date = form.cleaned_data["end_date"]
                if tzsign > 0:
                    start_date = start_date + timedelta(hours=int(int(offset) / 60), minutes=int(int(offset) % 60))
                    end_date = end_date + timedelta(hours=int(int(offset) / 60), minutes=int(int(offset) % 60))
                else:
                    start_date = start_date - timedelta(hours=int(int(offset) / 60), minutes=int(int(offset) % 60))
                    end_date = end_date - timedelta(hours=int(int(offset) / 60), minutes=int(int(offset) % 60))
                hunt.starts_on = start_date
                hunt.prize_winner = Decimal(request.POST["prize_winner"])
                hunt.prize_runner = Decimal(request.POST["prize_runner"])
                hunt.prize_second_runner = Decimal(request.POST["prize_second_runner"])
                hunt.end_on = end_date
                hunt.name = request.POST["name"]
                hunt.description = form.cleaned_data["content"]
                wallet.withdraw(total_amount)
                wallet.save()
                try:
                    hunt.is_published = request.POST.get("publish", False) == "on"
                except KeyError:
                    hunt.is_published = False
                hunt.save()
                return HttpResponse("success")
            else:
                return HttpResponse("failed")
        except (OrganizationAdmin.DoesNotExist, Domain.DoesNotExist, ValueError, KeyError) as e:
            return HttpResponse(f"Error: {str(e)}")


@login_required
def user_sizzle_report(request, username):
    user = get_object_or_404(User, username=username)
    time_logs = TimeLog.objects.filter(user=user).order_by("-start_time")

    grouped_logs = defaultdict(list)
    for log in time_logs:
        date_str = log.created.strftime("%Y-%m-%d")
        grouped_logs[date_str].append(log)

    response_data = []
    for date, logs in grouped_logs.items():
        first_log = logs[0]
        total_duration = sum((log.duration for log in logs if log.duration), timedelta())

        total_duration_seconds = total_duration.total_seconds()
        formatted_duration = f"{int(total_duration_seconds // 60)} min {int(total_duration_seconds % 60)} sec"

        issue_title = get_github_issue_title(first_log.github_issue_url)

        start_time = first_log.start_time.strftime("%I:%M %p")
        end_time = first_log.end_time.strftime("%I:%M %p")
        formatted_date = first_log.created.strftime("%d %B %Y")

        day_data = {
            "issue_title": issue_title,
            "duration": formatted_duration,
            "start_time": start_time,
            "end_time": end_time,
            "date": formatted_date,
        }

        response_data.append(day_data)

    return render(
        request,
        "sizzle/user_sizzle_report.html",
        {"response_data": response_data, "user": user},
    )


@login_required
def sizzle_daily_log(request):
    try:
        if request.method == "GET":
            reports = DailyStatusReport.objects.filter(user=request.user).order_by("-date")
            return render(request, "sizzle/sizzle_daily_status.html", {"reports": reports})

        if request.method == "POST":
            previous_work = request.POST.get("previous_work")
            next_plan = request.POST.get("next_plan")
            blockers = request.POST.get("blockers")
            goal_accomplished = request.POST.get("goal_accomplished") == "on"
            current_mood = request.POST.get("feeling")
            print(previous_work, next_plan, blockers, goal_accomplished, current_mood)

            DailyStatusReport.objects.create(
                user=request.user,
                date=now().date(),
                previous_work=previous_work,
                next_plan=next_plan,
                blockers=blockers,
                goal_accomplished=goal_accomplished,
                current_mood=current_mood,
            )

            messages.success(request, "Daily status report submitted successfully.")
            return JsonResponse(
                {
                    "success": "true",
                    "message": "Daily status report submitted successfully.",
                }
            )

    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect("sizzle")

    return HttpResponseBadRequest("Invalid request method.")


@login_required
def TimeLogListView(request):
    time_logs = TimeLog.objects.filter(user=request.user).order_by("-start_time")
    active_time_log = time_logs.filter(end_time__isnull=True).first()

    # print the all details of the active time log
    token, created = Token.objects.get_or_create(user=request.user)
    organizations_list_queryset = Organization.objects.all().values("url", "name")
    organizations_list = list(organizations_list_queryset)
    organization_url = None
    if active_time_log and active_time_log.organization:
        organization_url = active_time_log.organization.url
    return render(
        request,
        "sizzle/time_logs.html",
        {
            "time_logs": time_logs,
            "active_time_log": active_time_log,
            "token": token.key,
            "organizations_list": organizations_list,
            "organization_url": organization_url,
        },
    )


def TimeLogListAPIView(request):
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

    time_logs = TimeLog.objects.filter(user=request.user, created__range=[start_date, end_date]).order_by("created")

    grouped_logs = defaultdict(list)
    for log in time_logs:
        date_str = log.created.strftime("%Y-%m-%d")
        grouped_logs[date_str].append(log)

    response_data = []
    for date, logs in grouped_logs.items():
        first_log = logs[0]
        total_duration = sum((log.duration for log in logs if log.duration), timedelta())

        total_duration_seconds = total_duration.total_seconds()
        formatted_duration = f"{int(total_duration_seconds // 60)} min {int(total_duration_seconds % 60)} sec"

        issue_title = get_github_issue_title(first_log.github_issue_url)

        start_time = first_log.start_time.strftime("%I:%M %p")
        formatted_date = first_log.created.strftime("%d %B %Y")

        day_data = {
            "id": first_log.id,
            "issue_title": issue_title,
            "duration": formatted_duration,
            "start_time": start_time,
            "date": formatted_date,
        }

        response_data.append(day_data)

    return JsonResponse(response_data, safe=False, status=status.HTTP_200_OK)


def sizzle_docs(request):
    return render(request, "sizzle/sizzle_docs.html")


def sizzle(request):
    # Aggregate leaderboard data: username and total_duration
    leaderboard_qs = (
        TimeLog.objects.values("user__username").annotate(total_duration=Sum("duration")).order_by("-total_duration")
    )

    # Process leaderboard to include formatted_duration
    leaderboard = []
    for entry in leaderboard_qs:
        username = entry["user__username"]
        total_duration = entry["total_duration"] or timedelta()  # Handle None
        formatted_duration = format_timedelta(total_duration)
        leaderboard.append(
            {
                "username": username,
                "formatted_duration": formatted_duration,
            }
        )

    # Initialize sizzle_data
    sizzle_data = None

    if request.user.is_authenticated:
        last_data = TimeLog.objects.filter(user=request.user).order_by("-created").first()

        if last_data:
            all_data = TimeLog.objects.filter(user=request.user, created__date=last_data.created.date()).order_by(
                "created"
            )

            total_duration = sum((entry.duration for entry in all_data if entry.duration), timedelta())

            formatted_duration = format_timedelta(total_duration)

            github_issue_url = all_data.first().github_issue_url
            issue_title = get_github_issue_title(github_issue_url)

            start_time = all_data.first().start_time.strftime("%I:%M %p")
            date = last_data.created.strftime("%d %B %Y")

            sizzle_data = {
                "id": last_data.id,
                "issue_title": issue_title,
                "duration": formatted_duration,
                "start_time": start_time,
                "date": date,
            }

    return render(
        request,
        "sizzle/sizzle.html",
        {"sizzle_data": sizzle_data, "leaderboard": leaderboard},
    )


def trademark_detailview(request, slug):
    if settings.USPTO_API is None:
        return HttpResponse("API KEY NOT SETUP")

    trademark_available_url = "https://uspto-trademark.p.rapidapi.com/v1/trademarkAvailable/%s" % (slug)
    headers = {
        "x-rapidapi-host": "uspto-trademark.p.rapidapi.com",
        "x-rapidapi-key": settings.USPTO_API,
    }
    trademark_available_response = requests.get(trademark_available_url, headers=headers)
    ta_data = trademark_available_response.json()

    if trademark_available_response.status_code == 429:
        error_message = "You have exceeded the rate limit for USPTO API requests. Please try again later."
        return render(request, "trademark_detailview.html", {"error_message": error_message, "query": slug})

    if not isinstance(ta_data, list) or len(ta_data) == 0:
        error_message = "Invalid response from USPTO API."
        return render(request, "trademark_detailview.html", {"error_message": error_message, "query": slug})

    if ta_data[0].get("available") == "no":
        trademark_search_url = "https://uspto-trademark.p.rapidapi.com/v1/trademarkSearch/%s/active" % (slug)
        trademark_search_response = requests.get(trademark_search_url, headers=headers)
        ts_data = trademark_search_response.json()
        context = {"count": ts_data.get("count"), "items": ts_data.get("items"), "query": slug}
    else:
        context = {"available": ta_data[0].get("available"), "query": slug}

    return render(request, "trademark_detailview.html", context)


def trademark_search(request, **kwargs):
    if request.method == "POST":
        slug = request.POST.get("query")
        return redirect("trademark_detailview", slug=slug)
    return render(request, "trademark_search.html")


@login_required(login_url="/accounts/login")
def view_hunt(request, pk, template="view_hunt.html"):
    hunt = get_object_or_404(Hunt, pk=pk)
    time_remaining = None
    if ((hunt.starts_on - datetime.now(timezone.utc)).total_seconds()) > 0:
        hunt_active = False
        hunt_completed = False
        time_remaining = naturaltime(datetime.now(timezone.utc) - hunt.starts_on)
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
def organization_dashboard_hunt_edit(request, pk, template="organization_dashboard_hunt_edit.html"):
    if request.method == "GET":
        hunt = get_object_or_404(Hunt, pk=pk)
        domain_admin = OrganizationAdmin.objects.get(user=request.user)
        if not domain_admin.is_active:
            return HttpResponseRedirect("/")
        if domain_admin.role == 1:
            if hunt.domain != domain_admin.domain:
                return HttpResponseRedirect("/")
        domain = []
        if domain_admin.role == 0:
            domain = Domain.objects.filter(organization=domain_admin.organization)
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
            return HttpResponse("Invalid form data")
        hunt = get_object_or_404(Hunt, pk=pk)
        domain_admin = OrganizationAdmin.objects.get(user=request.user)
        if not domain_admin.is_active:
            return HttpResponse("Inactive domain admin")
        if domain_admin.role == 1:
            if hunt.domain != domain_admin.domain:
                return HttpResponse("Domain mismatch")
        hunt.domain = Domain.objects.get(pk=(request.POST["domain"]).split("-")[0].replace(" ", ""))
        tzsign = 1
        offset = request.POST["tzoffset"]
        if int(offset) < 0:
            offset = int(offset) * (-1)
            tzsign = -1
        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]
        if tzsign > 0:
            start_date = start_date + timedelta(hours=int(int(offset) / 60), minutes=int(int(offset) % 60))
            end_date = end_date + timedelta(hours=int(int(offset) / 60), minutes=int(int(offset) % 60))
        else:
            start_date = start_date - timedelta(hours=int(int(offset) / 60), minutes=int(int(offset) % 60))
            end_date = end_date - timedelta(hours=int(int(offset) / 60), minutes=int(int(offset) % 60))
        hunt.starts_on = start_date
        hunt.end_on = end_date
        hunt.name = request.POST["name"]
        hunt.description = form.cleaned_data["content"]
        hunt.is_published = request.POST.get("publish", False) == "on"
        hunt.save()
        return HttpResponse("success")


@login_required(login_url="/accounts/login")
def organization_dashboard_hunt_detail(request, pk, template="organization_dashboard_hunt_detail.html"):
    hunt = get_object_or_404(Hunt, pk=pk)
    return render(request, template, {"hunt": hunt})


@login_required(login_url="/accounts/login")
def hunt_results(request, pk, template="hunt_results.html"):
    hunt = get_object_or_404(Hunt, pk=pk)
    return render(request, template, {"hunt": hunt})


@login_required(login_url="/accounts/login")
def organization_dashboard_domain_detail(request, pk, template="organization_dashboard_domain_detail.html"):
    user = request.user
    try:
        domain_admin = OrganizationAdmin.objects.get(user=request.user)
        domain = Domain.objects.get(pk=pk)

        if domain == domain_admin.domain:
            if not user.is_active:
                return HttpResponseRedirect("/")
            return render(request, template, {"domain": domain})
        return redirect("/")

    except (OrganizationAdmin.DoesNotExist, Domain.DoesNotExist) as e:
        logger.error(f"Error in organization_dashboard_domain_detail: {str(e)}")
        return redirect("/")


@login_required(login_url="/accounts/login")
def add_or_update_domain(request):
    if request.method == "POST":
        try:
            organization_admin = OrganizationAdmin.objects.get(user=request.user)
            subscription = organization_admin.organization.subscription
            count_domain = Domain.objects.filter(organization=organization_admin.organization).count()

            try:
                domain_pk = request.POST["id"]
                domain = Domain.objects.get(pk=domain_pk)
                domain.name = request.POST["name"]
                domain.email = request.POST["email"]
                domain.github = request.POST["github"]
                try:
                    domain.logo = request.FILES["logo"]
                except KeyError:
                    pass
                domain.save()
                return HttpResponse("Domain Updated")
            except Domain.DoesNotExist:
                if count_domain == subscription.number_of_domains:
                    return HttpResponse("Domains Reached Limit")
                else:
                    if organization_admin.role == 0:
                        domain = Domain()
                        domain.name = request.POST["name"]
                        domain.url = request.POST["url"]
                        domain.email = request.POST["email"]
                        domain.github = request.POST["github"]
                        try:
                            domain.logo = request.FILES["logo"]
                        except KeyError:
                            pass
                        domain.organization = organization_admin.organization
                        domain.save()
                        return HttpResponse("Domain Created")
                    else:
                        return HttpResponse("Unauthorized: Only admin can create domains")
        except (OrganizationAdmin.DoesNotExist, KeyError) as e:
            return HttpResponse(f"Error: {str(e)}")


@login_required(login_url="/accounts/login")
def add_or_update_organization(request):
    if not request.user.is_superuser:
        return HttpResponse("Unauthorized: Superuser access required")

    if not request.user.is_active:
        return HttpResponseRedirect("/")

    if request.method == "POST":
        try:
            domain_pk = request.POST["id"]
            organization = Organization.objects.get(pk=domain_pk)
            user = organization.admin
            new_admin = User.objects.get(email=request.POST["admin"])

            if user != new_admin:
                try:
                    admin = OrganizationAdmin.objects.get(user=user)
                    admin.user = new_admin
                    admin.save()
                except OrganizationAdmin.DoesNotExist:
                    admin = OrganizationAdmin.objects.create(
                        user=new_admin, role=0, organization=organization, is_active=True
                    )

            organization.name = request.POST["name"]
            organization.email = request.POST["email"]
            organization.url = request.POST["url"]
            organization.admin = new_admin
            organization.github = request.POST["github"]
            organization.is_active = request.POST.get("verify") == "on"

            try:
                organization.subscription = Subscription.objects.get(name=request.POST["subscription"])
            except (Subscription.DoesNotExist, KeyError):
                pass

            try:
                organization.logo = request.FILES["logo"]
            except KeyError:
                pass

            organization.save()
            return HttpResponse("Organization updated successfully")

        except (Organization.DoesNotExist, User.DoesNotExist, KeyError) as e:
            logger.error(f"Error updating organization: {str(e)}")
            return HttpResponse(
                "Error updating organization. Either organization or user "
                "doesn't exist or there was a key error. Please try again later."
            )
    else:
        return HttpResponse("Invalid request method")


@login_required(login_url="/accounts/login")
def add_role(request):
    if request.method == "POST":
        try:
            domain_admin = OrganizationAdmin.objects.get(user=request.user)
            if domain_admin.role != 0 or not domain_admin.is_active:
                return HttpResponse("Unauthorized: Only active admin can add roles")

            email = request.POST["email"]
            user = User.objects.get(email=email)

            if request.user == user:
                return HttpResponse("Cannot modify your own role")

            try:
                admin = OrganizationAdmin.objects.get(user=user)
                if admin.organization == domain_admin.organization:
                    admin.is_active = True
                    admin.save()
                    return HttpResponse("Role updated successfully")
                else:
                    return HttpResponse("User is already admin of another organization")
            except OrganizationAdmin.DoesNotExist:
                OrganizationAdmin.objects.create(
                    user=user, role=1, organization=domain_admin.organization, is_active=True
                )
                return HttpResponse("Role added successfully")

        except (OrganizationAdmin.DoesNotExist, User.DoesNotExist, KeyError) as e:
            logger.error(f"Error adding role: {str(e)}")
            return HttpResponse(
                "Error updating organization. Either organization or user "
                "doesn't exist or there was a key error. Please try again later."
            )
    else:
        return HttpResponse("Invalid request method")


@login_required(login_url="/accounts/login")
def update_role(request):
    if request.method == "POST":
        domain_admin = OrganizationAdmin.objects.get(user=request.user)
        if domain_admin.role == 0 and domain_admin.is_active:
            for key, value in request.POST.items():
                if key.startswith("user@"):
                    user = User.objects.get(username=value)
                    if domain_admin.organization.admin == request.user:
                        pass
                    domain_admin = OrganizationAdmin.objects.get(user=user)
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
                    if domain_admin.organization.admin == request.user:
                        pass
                    domain_admin = OrganizationAdmin.objects.get(user=user)
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
    return HttpResponse(json.dumps(domain.object_list, default=str), content_type="application/json")


@require_POST
@login_required
def delete_time_entry(request):
    entry_id = request.POST.get("id")
    try:
        time_entry = TimeLog.objects.get(id=entry_id, user=request.user)
        time_entry.delete()
        return JsonResponse({"success": True})
    except TimeLog.DoesNotExist:
        return JsonResponse({"success": False, "error": "Time entry not found"})


class ReportIpView(FormView):
    template_name = "report_ip.html"
    form_class = IpReportForm
    captcha = CaptchaForm()

    def is_valid_ip(self, ip_address, ip_type):
        """
        Validates an IP address format based on the specified type (IPv4 or IPv6).
        """
        try:
            if ip_type == "ipv4":
                ipaddress.IPv4Address(ip_address)
                return True
            elif ip_type == "ipv6":
                ipaddress.IPv6Address(ip_address)
                return True
            else:
                return False
        except ValueError:
            return False

    def post(self, request, *args, **kwargs):
        # Check CAPTCHA
        captcha_form = CaptchaForm(request.POST)
        if not captcha_form.is_valid():
            messages.error(request, "Invalid CAPTCHA. Please try again.")
            return render(
                request,
                self.template_name,
                {
                    "form": self.get_form(),
                    "captcha_form": captcha_form,
                },
            )

        # Process form and duplicate IP check
        form = self.get_form()
        if form.is_valid():
            ip_address = form.cleaned_data.get("ip_address")
            ip_type = form.cleaned_data.get("ip_type")
            print(ip_address + " " + ip_type)

            if not self.is_valid_ip(ip_address, ip_type):
                messages.error(request, f"Invalid {ip_type} address format.")
                return render(
                    request,
                    self.template_name,
                    {
                        "form": form,
                        "captcha_form": captcha_form,
                    },
                )
            if IpReport.objects.filter(ip_address=ip_address, ip_type=ip_type).exists():
                messages.error(request, "This IP address has already been reported.")
                return render(
                    request,
                    self.template_name,
                    {
                        "form": form,
                        "captcha_form": captcha_form,
                    },
                )

            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        # Check daily report limit per IP
        reporter_ip = get_client_ip(self.request)
        limit = 50 if self.request.user.is_authenticated else 30
        today = now().date()
        recent_reports_count = IpReport.objects.filter(reporter_ip_address=reporter_ip, created=today).count()

        if recent_reports_count >= limit:
            messages.error(self.request, "You have reached the daily limit for IP reports.")
            return render(
                self.request,
                self.template_name,
                {
                    "form": self.get_form(),
                    "captcha_form": CaptchaForm(),
                },
            )

        form.instance.reporter_ip_address = reporter_ip
        form.instance.user = self.request.user if self.request.user.is_authenticated else None
        form.save()
        messages.success(self.request, "IP report successfully submitted.")

        return redirect("reported_ips_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["captcha_form"] = CaptchaForm()
        return context


class ReportedIpListView(ListView):
    model = IpReport
    template_name = "reported_ips_list.html"
    context_object_name = "reported_ips"
    paginate_by = 10

    def get_queryset(self):
        return IpReport.objects.all().order_by("-created")


def feed(request):
    activities = Activity.objects.all().order_by("-timestamp")
    paginator = Paginator(activities, 10)  # Show 10 activities per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Determine if pagination is required
    is_paginated = page_obj.has_other_pages()

    # Check if the user has the mentor badge
    if request.user.is_authenticated:
        is_mentor = UserBadge.objects.filter(user=request.user, badge__title="Mentor").exists()
    else:
        is_mentor = False

    return render(
        request,
        "feed.html",
        {
            "page_obj": page_obj,
            "is_paginated": is_paginated,  # Pass this flag to the template
            "is_mentor": is_mentor,  # Add is_mentor to the context
        },
    )


@login_required
@require_POST
def like_activity(request, id):
    activity = get_object_or_404(Activity, id=id)
    user = request.user

    if activity.dislikes.filter(id=user.id).exists():
        activity.dislikes.remove(user)
        activity.dislike_count -= 1

    if activity.likes.filter(id=user.id).exists():
        activity.likes.remove(user)
        activity.like_count -= 1
    else:
        activity.likes.add(user)
        activity.like_count += 1

    activity.save()

    # Check if the activity meets the approval criteria
    if activity.like_count >= 3 and activity.dislike_count < 3 and not activity.is_approved:
        activity.is_approved = True
        activity.save()

        # Trigger posting on BlueSky
        blue_sky_service = BlueSkyService()
        try:
            activity.post_to_bluesky(blue_sky_service)
        except Exception:
            return JsonResponse({"success": False})

    return JsonResponse(
        {
            "success": True,
            "like_count": activity.like_count,
            "dislike_count": activity.dislike_count,
        }
    )


@login_required
@require_POST
def dislike_activity(request, id):
    activity = get_object_or_404(Activity, id=id)
    user = request.user

    if activity.likes.filter(id=user.id).exists():
        activity.likes.remove(user)
        activity.like_count -= 1

    if activity.dislikes.filter(id=user.id).exists():
        activity.dislikes.remove(user)
        activity.dislike_count -= 1
    else:
        activity.dislikes.add(user)
        activity.dislike_count += 1

    activity.save()

    # Check if the activity meets the approval criteria
    if activity.like_count >= 3 and activity.dislike_count < 3 and not activity.is_approved:
        activity.is_approved = True
        activity.save()

        # Trigger posting on BlueSky
        blue_sky_service = BlueSkyService()
        try:
            activity.post_to_bluesky(blue_sky_service)
        except Exception:
            return JsonResponse({"success": False})

    return JsonResponse(
        {
            "success": True,
            "like_count": activity.like_count,
            "dislike_count": activity.dislike_count,
        }
    )


@login_required
@require_POST
def approve_activity(request, id):
    activity = get_object_or_404(Activity, id=id)
    user = request.user

    # Check if the user has the "Mentor" badge
    if UserBadge.objects.filter(user=user, badge__title="Mentor").exists() and not activity.is_approved:
        activity.is_approved = True
        activity.save()

        # Trigger posting on BlueSky
        blue_sky_service = BlueSkyService()
        try:
            activity.post_to_bluesky(blue_sky_service)
            return JsonResponse({"success": True, "is_approved": activity.is_approved})
        except Exception:
            return JsonResponse({"success": False})
    else:
        return JsonResponse({"success": False, "error": "Not authorized"})


def truncate_text(text, length=15):
    return text if len(text) <= length else text[:length] + "..."


@login_required
def add_sizzle_checkIN(request):
    # Fetch yesterday's report
    yesterday = now().date() - timedelta(days=1)
    yesterday_report = DailyStatusReport.objects.filter(user=request.user, date=yesterday).first()

    return render(
        request,
        "sizzle/add_sizzle_checkin.html",
        {"yesterday_report": yesterday_report},
    )


def checkIN(request):
    from datetime import date

    # Find the most recent date that has data
    last_report = DailyStatusReport.objects.order_by("-date").first()
    if last_report:
        default_start_date = last_report.date
        default_end_date = last_report.date
    else:
        # If no data at all, fallback to today
        default_start_date = date.today()
        default_end_date = date.today()

    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = default_start_date
            end_date = default_end_date
    else:
        # No date range provided, use the default (most recent date with data)
        start_date = default_start_date
        end_date = default_end_date

    reports = (
        DailyStatusReport.objects.filter(date__range=(start_date, end_date))
        .select_related("user")
        .order_by("date", "created")
    )

    data = []
    for r in reports:
        data.append(
            {
                "id": r.id,
                "username": r.user.username,
                "previous_work": truncate_text(r.previous_work),
                "next_plan": truncate_text(r.next_plan),
                "blockers": truncate_text(r.blockers),
                "goal_accomplished": r.goal_accomplished,  # Add this line
                "current_mood": r.current_mood,  # Add this line
                "date": r.date.strftime("%d %B %Y"),
            }
        )

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(data, safe=False)

    # Render template with initial data if needed
    return render(
        request,
        "sizzle/checkin.html",
        {
            "data": data,
            "default_start_date": default_start_date.isoformat(),
            "default_end_date": default_end_date.isoformat(),
        },
    )


def checkIN_detail(request, report_id):
    report = get_object_or_404(DailyStatusReport, pk=report_id)
    context = {
        "username": report.user.username,
        "date": report.date.strftime("%d %B %Y"),
        "previous_work": report.previous_work,
        "next_plan": report.next_plan,
        "blockers": report.blockers,
    }
    return render(request, "sizzle/checkin_detail.html", context)


class RoomsListView(ListView):
    model = Room
    template_name = "rooms_list.html"
    context_object_name = "rooms"
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = RoomForm()

        # Add message count and last 3 messages for each room (newest first)
        for room in context["rooms"]:
            room.message_count = room.messages.count()
            # Get messages in reverse chronological order (newest first)
            room.recent_messages = room.messages.all().order_by("-timestamp")[:3]

        # Add breadcrumbs
        context["breadcrumbs"] = [{"title": "Discussion Rooms", "url": None}]

        return context


class RoomCreateView(CreateView):
    model = Room
    form_class = RoomForm
    template_name = "room_form.html"
    success_url = reverse_lazy("rooms_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["is_anonymous"] = self.request.user.is_anonymous
        return kwargs

    def form_valid(self, form):
        if self.request.user.is_anonymous:
            # Get or create session key
            if not self.request.session.session_key:
                self.request.session.create()
            session_key = self.request.session.session_key
            form.instance.session_key = session_key
        else:
            form.instance.admin = self.request.user
        return super().form_valid(form)


def join_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    # Ensure session key exists for anonymous users
    if request.user.is_anonymous and not request.session.session_key:
        request.session.create()
    # Get messages ordered by timestamp in descending order (most recent first)
    room_messages = room.messages.all().order_by("-timestamp")

    # Add breadcrumbs context
    breadcrumbs = [{"title": "Discussion Rooms", "url": reverse("rooms_list")}, {"title": room.name, "url": None}]

    return render(request, "join_room.html", {"room": room, "room_messages": room_messages, "breadcrumbs": breadcrumbs})


@login_required(login_url="/accounts/login")
@require_POST
def delete_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)

    # Check if the user is the admin or the anonymous creator
    is_admin = request.user.is_authenticated and room.admin == request.user
    is_anon_creator = request.user.is_anonymous and room.session_key == request.session.session_key

    if not (is_admin or is_anon_creator):
        messages.error(request, "You don't have permission to delete this room.")
        return redirect("rooms_list")

    room.delete()
    messages.success(request, "Room deleted successfully.")
    return redirect("rooms_list")


class OrganizationDetailView(DetailView):
    model = Organization
    template_name = "organization/organization_detail.html"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related(
                Prefetch("domain_set", queryset=Domain.objects.prefetch_related("issue_set")),
                Prefetch(
                    "domain_set__issue_set",
                    queryset=Issue.objects.filter(status="open"),
                    to_attr="open_issues_list",
                ),
                Prefetch(
                    "domain_set__issue_set",
                    queryset=Issue.objects.filter(status="closed"),
                    to_attr="closed_issues_list",
                ),
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.object

        # Get top 10 projects based on total pull requests
        top_projects = []
        total_repos = 0

        # Count repositories directly from the related repos
        total_repos = organization.repos.count()

        for project in organization.projects.all():
            project_repos = project.repos.all()
            # We don't need to add to total_repos here since we're counting directly from organization.repos

            total_prs = sum(repo.open_pull_requests + repo.closed_pull_requests for repo in project_repos)
            total_contributors = sum(repo.contributor_count for repo in project_repos)
            top_projects.append({"project": project, "total_prs": total_prs, "total_contributors": total_contributors})

        # Sort by total PRs and get top 10
        top_projects.sort(key=lambda x: x["total_prs"], reverse=True)
        context["top_projects"] = top_projects[:10]

        # Get all domains for this organization
        domains = organization.domain_set.all()

        # Calculate statistics
        total_open_issues = sum(len(domain.open_issues_list) for domain in domains)
        total_closed_issues = sum(len(domain.closed_issues_list) for domain in domains)

        # Get view count
        view_count = IP.objects.filter(path=self.request.path).count()

        # Check if GitHub URL exists
        github_url = None
        if organization.source_code and "github.com" in organization.source_code:
            github_url = organization.source_code

        context.update(
            {
                "total_domains": domains.count(),
                "total_open_issues": total_open_issues,
                "total_closed_issues": total_closed_issues,
                "total_issues": total_open_issues + total_closed_issues,
                "view_count": view_count,
                "total_repos": total_repos,
                "github_url": github_url,
            }
        )

        return context


class OrganizationListView(ListView):
    model = Organization
    template_name = "organization/organization_list.html"
    context_object_name = "organizations"
    paginate_by = 100

    def get_queryset(self):
        queryset = (
            Organization.objects.prefetch_related(
                "domain_set",
                "projects",
                "projects__repos",
                "repos",
                "tags",
                Prefetch(
                    "domain_set__issue_set", queryset=Issue.objects.filter(status="open"), to_attr="open_issues_list"
                ),
                Prefetch(
                    "domain_set__issue_set",
                    queryset=Issue.objects.filter(status="closed"),
                    to_attr="closed_issues_list",
                ),
            )
            .annotate(
                domain_count=Count("domain", distinct=True),
                total_issues=Count("domain__issue", distinct=True),
                open_issues=Count("domain__issue", filter=Q(domain__issue__status="open"), distinct=True),
                closed_issues=Count("domain__issue", filter=Q(domain__issue__status="closed"), distinct=True),
                project_count=Count("projects", distinct=True),
            )
            .select_related("admin")
            .order_by("-created")
        )

        # Filter by tag if provided in the URL
        tag_slug = self.request.GET.get("tag")
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get recently viewed organizations efficiently using a single query
        recent_org_paths = (
            IP.objects.filter(
                path__startswith="/organization/",
                path__regex=r"^/organization/[^/]+/$",  # Only match exact organization paths
            )
            .exclude(
                path="/organizations/"  # Exclude the main organizations list page
            )
            .order_by("-created")
            .values_list("path", flat=True)
            .distinct()[:5]
        )

        # Extract slugs and get organizations in a single query
        slugs = [path.split("/")[2] for path in recent_org_paths if len(path.split("/")) > 2]
        recently_viewed = (
            Organization.objects.filter(slug__in=slugs).prefetch_related("domain_set").order_by("-created")[:5]
        )

        context["recently_viewed"] = recently_viewed

        # Get most popular organizations by counting their view paths for today only
        today = timezone.now().date()
        orgs_with_views = []
        for org in self.get_queryset():
            view_count = IP.objects.filter(path=f"/organization/{org.slug}/", created__date=today).count()
            orgs_with_views.append((org, view_count))

        # Sort by view count and get top 5
        most_popular = [org for org, _ in sorted(orgs_with_views, key=lambda x: x[1], reverse=True)[:5]]
        context["most_popular"] = most_popular

        # Get total count using cached queryset
        context["total_organizations"] = Organization.objects.count()

        # Get top tags by usage count
        top_tags = (
            Tag.objects.annotate(org_count=Count("organization")).filter(org_count__gt=0).order_by("-org_count")[:10]
        )

        context["top_tags"] = top_tags

        # Get the currently selected tag if any
        tag_slug = self.request.GET.get("tag")
        if tag_slug:
            context["selected_tag"] = Tag.objects.filter(slug=tag_slug).first()

        # Add top testers for each domain
        for org in context["organizations"]:
            for domain in org.domain_set.all():
                domain.top_testers = (
                    User.objects.filter(issue__domain=domain)
                    .annotate(issue_count=Count("issue"))
                    .order_by("-issue_count")[:1]
                )

        return context


@login_required
def update_organization_repos(request, slug):
    """Update repositories for an organization from GitHub."""
    try:
        organization = get_object_or_404(Organization, slug=slug)

        # Check if repositories were updated in the last 24 hours
        one_day_ago = timezone.timedelta(days=1)
        if organization.repos_updated_at and timezone.now() < organization.repos_updated_at + one_day_ago:
            time_since_update = timezone.now() - organization.repos_updated_at
            hours_remaining = 24 - (time_since_update.total_seconds() / 3600)
            messages.warning(
                request,
                f"Repositories were updated recently. Please wait {int(hours_remaining)} hours before updating again.",
            )
            return redirect("organization_detail", slug=slug)

        # Check if the organization has a GitHub URL
        if not organization.source_code:
            # If GitHub URL was submitted in the form
            if request.method == "POST" and request.POST.get("github_url"):
                github_url = request.POST.get("github_url")
                # Validate GitHub URL
                if not re.match(r"https?://github\.com/([^/]+)/?.*", github_url):
                    messages.error(
                        request,
                        "Invalid GitHub URL. Please ensure it's in the format: https://github.com/organization-name",
                    )
                    return redirect("organization_detail", slug=slug)

                # Save the GitHub URL
                organization.source_code = github_url
                organization.save()
                messages.success(request, "GitHub URL added successfully.")
            else:
                messages.error(request, "This organization doesn't have a GitHub URL set.")
                return redirect("organization_detail", slug=slug)

        # Extract GitHub organization name from URL
        github_url_pattern = r"https?://github\.com/([^/]+)/?.*"
        match = re.match(github_url_pattern, organization.source_code)
        if not match:
            messages.error(
                request, "Invalid GitHub URL. Please ensure it's in the format: https://github.com/organization-name"
            )
            return redirect("organization_detail", slug=slug)

        github_org_name = match.group(1)

        # Check if GitHub token is set
        if not hasattr(settings, "GITHUB_TOKEN") or not settings.GITHUB_TOKEN:
            logger.error("GitHub token not set in settings")
            messages.error(
                request,
                "GitHub API token not configured. Please contact the administrator.",
            )
            return redirect("organization_detail", slug=slug)

        # Update the repos_updated_at timestamp
        organization.repos_updated_at = timezone.now()
        organization.save()

        def error_stream():
            yield "data: $ Starting repository update for organization: %s\n\n" % organization.name
            yield "data: $ Using GitHub organization: %s\n\n" % github_org_name

        def event_stream():
            try:
                # Test GitHub API token validity
                yield "data: $ Testing GitHub API token...\n\n"
                try:
                    rate_limit_url = "https://api.github.com/rate_limit"
                    response = requests.get(
                        rate_limit_url,
                        headers={
                            "Authorization": f"token {settings.GITHUB_TOKEN}",
                            "Accept": "application/vnd.github.v3+json",
                        },
                        timeout=10,
                    )

                    if response.status_code == 200:
                        rate_data = response.json()
                        core_rate = rate_data.get("resources", {}).get("core", {})
                        remaining = core_rate.get("remaining", 0)
                        limit = core_rate.get("limit", 0)
                        reset_time = core_rate.get("reset", 0)
                        reset_datetime = datetime.fromtimestamp(reset_time)
                        reset_str = reset_datetime.strftime("%Y-%m-%d %H:%M:%S")

                        yield (
                            f"data: $ GitHub API token is valid. Rate limit: {remaining}/{limit}, "
                            f"resets at {reset_str}\n\n"
                        )

                        if remaining < 50:
                            yield "data: $ Warning: GitHub API rate limit is low. Updates may be incomplete.\n\n"
                    else:
                        response_text = response.text[:200] + "..." if len(response.text) > 200 else response.text
                        yield f"data: $ Error: GitHub API returned {response.status_code}. Response: {response_text}\n\n"
                        yield "data: DONE\n\n"
                        return
                except requests.exceptions.RequestException as e:
                    yield f"data: $ Error testing GitHub API: {str(e)[:50]}\n\n"
                    yield "data: DONE\n\n"
                    return

                # Fetch organization details
                try:
                    org_api_url = f"https://api.github.com/orgs/{github_org_name}"
                    yield f"data: $ Fetching organization details: {org_api_url}\n\n"

                    response = requests.get(
                        org_api_url,
                        headers={
                            "Authorization": f"token {settings.GITHUB_TOKEN}",
                            "Accept": "application/vnd.github.v3+json",
                        },
                        timeout=10,
                    )

                    if response.status_code == 404:
                        yield f"data: $ Error: GitHub organization '{github_org_name}' not found\n\n"
                        yield "data: DONE\n\n"
                        return
                    elif response.status_code == 401:
                        yield "data: $ Error: GitHub authentication failed\n\n"
                        yield "data: DONE\n\n"
                        return
                    elif response.status_code != 200:
                        response_text = response.text[:200] + "..." if len(response.text) > 200 else response.text
                        yield (
                            f"data: $ Error: GitHub API returned {response.status_code}. "
                            f"Response: {response_text}\n\n"
                        )
                        yield "data: DONE\n\n"
                        return

                    org_data = response.json()

                    # Update organization logo if not already set
                    if not organization.logo and org_data.get("avatar_url"):
                        try:
                            yield "data: $ Updating organization logo...\n\n"
                            logo_url = org_data["avatar_url"]
                            logo_response = requests.get(logo_url, timeout=10)
                            if logo_response.status_code == 200:
                                from django.core.files.base import ContentFile

                                logo_filename = f"{github_org_name}_logo.png"
                                logo_content = ContentFile(logo_response.content)
                                organization.logo.save(logo_filename, logo_content, save=True)
                                yield "data: $ Organization logo updated successfully\n\n"
                            else:
                                yield f"data: $ Failed to fetch logo: {logo_response.status_code}\n\n"
                        except Exception as e:
                            yield f"data: $ Error updating logo: {str(e)[:50]}\n\n"
                except requests.exceptions.RequestException:
                    yield "data: $ Error: Failed to connect to GitHub\n\n"
                    yield "data: DONE\n\n"
                    return

                # Fetch repositories
                page = 1
                repos_processed = 0
                repos_updated = 0
                repos_created = 0

                while True:
                    try:
                        repos_api_url = f"https://api.github.com/orgs/{github_org_name}/repos"
                        yield f"data: $ Fetching: {repos_api_url}?page={page}\n\n"

                        response = requests.get(
                            repos_api_url,
                            params={"page": page, "per_page": 100, "type": "public"},
                            headers={
                                "Authorization": f"token {settings.GITHUB_TOKEN}",
                                "Accept": "application/vnd.github.v3+json",
                            },
                            timeout=10,
                        )

                        if response.status_code == 403:
                            response_text = response.text[:200] + "..." if len(response.text) > 200 else response.text
                            if "rate limit" in response.text.lower():
                                yield (
                                    f"data: $ Error: GitHub API rate limit exceeded. " f"Response: {response_text}\n\n"
                                )
                            else:
                                yield (
                                    f"data: $ Error: GitHub API access forbidden (403). "
                                    f"Response: {response_text}\n\n"
                                )
                            break
                        elif response.status_code == 401:
                            response_text = response.text[:200] + "..." if len(response.text) > 200 else response.text
                            yield (
                                f"data: $ Error: GitHub authentication failed (401). " f"Response: {response_text}\n\n"
                            )
                            yield "data: DONE\n\n"
                            return
                        elif response.status_code != 200:
                            response_text = response.text[:200] + "..." if len(response.text) > 200 else response.text
                            yield (
                                f"data: $ Error: GitHub API returned {response.status_code}. "
                                f"Response: {response_text}\n\n"
                            )
                            yield "data: DONE\n\n"
                            return

                        repos = response.json()
                        if not repos:
                            break

                        for repo_data in repos:
                            repos_processed += 1
                            repo_name = repo_data.get("name", "Unknown")

                            try:
                                # Check if repo already exists
                                repo, created = Repo.objects.update_or_create(
                                    repo_url=repo_data["html_url"],
                                    defaults={
                                        "name": repo_name,
                                        "description": repo_data.get("description") or "",
                                        "primary_language": repo_data.get("language") or "",
                                        "organization": organization,
                                        "stars": repo_data.get("stargazers_count", 0),
                                        "forks": repo_data.get("forks_count", 0),
                                        "open_issues": repo_data.get("open_issues_count", 0),
                                        "watchers": repo_data.get("watchers_count", 0),
                                        "is_archived": repo_data.get("archived", False),
                                        "size": repo_data.get("size", 0),
                                    },
                                )

                                # Create slug if it doesn't exist
                                if not repo.slug:
                                    base_slug = slugify(repo.name)
                                    repo.slug = base_slug
                                    repo.save()

                                if created:
                                    repos_created += 1
                                    yield f"data: $ {repo.name} [created]\n\n"
                                else:
                                    repos_updated += 1
                                    yield f"data: $ {repo.name} [updated]\n\n"

                                # Add topics as tags (without verbose output)
                                if repo_data.get("topics"):
                                    for topic in repo_data["topics"]:
                                        tag_slug = slugify(topic)
                                        tag, _ = Tag.objects.get_or_create(slug=tag_slug, defaults={"name": topic})
                                        repo.tags.add(tag)

                            except Exception as e:
                                yield f"data: $ Error with {repo_name}: {str(e)[:50]}\n\n"

                    except requests.exceptions.RequestException as e:
                        yield f"data: $ Network error: {str(e)[:50]}\n\n"
                        break

                    page += 1
                    time.sleep(1)  # Avoid hitting rate limits

                # Final status message
                yield (
                    f"data: $ Done. Processed: {repos_processed}, Updated: {repos_updated}, "
                    f"Created: {repos_created}\n\n"
                )
                yield "data: DONE\n\n"

            except Exception as e:
                yield f"data: $ Unexpected error: {str(e)[:50]}\n\n"
                yield "data: DONE\n\n"

        return StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)[:100]}")
        return redirect("organization_detail", slug=slug)


@require_POST
def send_message_api(request):
    """API endpoint for sending messages from the rooms list page"""
    if not request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": False, "error": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body)
        room_id = data.get("room_id")
        message_content = data.get("message")

        if not room_id or not message_content:
            return JsonResponse({"success": False, "error": "Missing required fields"}, status=400)

        room = get_object_or_404(Room, id=room_id)

        # Create the message
        if request.user.is_authenticated:
            username = request.user.username
            user = request.user
            session_key = None
        else:
            # Ensure session key exists for anonymous users
            if not request.session.session_key:
                request.session.create()
            session_key = request.session.session_key
            username = f"anon_{session_key[-4:]}"
            user = None

        message = Message.objects.create(
            room=room, user=user, username=username, content=message_content, session_key=session_key
        )

        return JsonResponse({"success": True, "message_id": message.id, "timestamp": message.timestamp.isoformat()})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def room_messages_api(request, room_id):
    """API endpoint for getting room messages"""
    room = get_object_or_404(Room, id=room_id)
    messages = room.messages.all().order_by("-timestamp")[:10]  # Get the 10 most recent messages

    message_data = []
    for message in messages:
        message_data.append(
            {
                "id": message.id,
                "username": message.username,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "timestamp_display": naturaltime(message.timestamp),
            }
        )

    return JsonResponse({"success": True, "count": room.messages.count(), "messages": message_data})

