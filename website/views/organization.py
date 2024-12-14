import ipaddress
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import urlparse

import humanize
import requests
import stripe
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, Q, Sum
from django.db.models.functions import ExtractMonth
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.decorators.http import require_POST
from django.views.generic import FormView, ListView, TemplateView, View
from django.views.generic.edit import CreateView
from rest_framework import status
from rest_framework.authtoken.models import Token

from blt import settings
from website.forms import CaptchaForm, HuntForm, IpReportForm, UserProfileForm
from website.models import (
    Activity,
    Company,
    CompanyAdmin,
    DailyStatusReport,
    Domain,
    Hunt,
    IpReport,
    Issue,
    IssueScreenshot,
    Subscription,
    TimeLog,
    User,
    UserBadge,
    Wallet,
    Winner,
)
from website.services.blue_sky_service import BlueSkyService
from website.utils import format_timedelta, get_client_ip, get_github_issue_title


def add_domain_to_company(request):
    if request.method == "POST":
        domain = request.POST.get("domain")
        domain = Domain.objects.get(id=domain)
        company_name = request.POST.get("company")
        company = Company.objects.filter(name=company_name).first()

        if not company:
            url = domain.url
            if not url.startswith(("http://", "https://")):
                url = "http://" + url
            response = requests.get(url)
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
        return redirect("home")


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

        open_issues = (
            Issue.objects.filter(domain__name__contains=self.kwargs["slug"])
            .filter(status="open", hunt=None)
            .exclude(Q(is_hidden=True) & ~Q(user_id=self.request.user.id))
        )

        closed_issues = (
            Issue.objects.filter(domain__name__contains=self.kwargs["slug"])
            .filter(status="closed", hunt=None)
            .exclude(Q(is_hidden=True) & ~Q(user_id=self.request.user.id))
        )
        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)

        context["name"] = parsed_url.netloc.split(".")[-2:][0].title()

        paginator = Paginator(open_issues, 3)
        page = self.request.GET.get("open")
        try:
            openissue_paginated = paginator.page(page)
        except PageNotAnInteger:
            openissue_paginated = paginator.page(1)
        except EmptyPage:
            openissue_paginated = paginator.page(paginator.num_pages)

        paginator = Paginator(closed_issues, 3)
        page = self.request.GET.get("close")
        try:
            closeissue_paginated = paginator.page(page)
        except PageNotAnInteger:
            closeissue_paginated = paginator.page(1)
        except EmptyPage:
            closeissue_paginated = paginator.page(paginator.num_pages)

        context["opened_net"] = open_issues
        context["opened"] = openissue_paginated
        context["closed_net"] = closed_issues
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


class ScoreboardView(ListView):
    model = Domain
    template_name = "scoreboard.html"
    paginate_by = 20

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        sort_by = self.request.GET.get("sort_by", "open_issues_count")
        sort_order = self.request.GET.get("sort_order", "desc")

        if sort_order == "asc":
            sort_by = sort_by
        else:
            sort_by = f"-{sort_by}"

        annotated_domains = Domain.objects.annotate(
            open_issues_count=Count("issue", filter=Q(issue__status="open")),
            closed_issues_count=Count("issue", filter=Q(issue__status="closed")),
        ).order_by(sort_by)

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
                domain = Domain.objects.get(email__iexact=event.get("email"))
                domain.email_event = event.get("event")
                if event.get("event") == "click":
                    domain.clicks = int(domain.clicks or 0) + 1
                domain.save()
            except Exception:
                pass

        return JsonResponse({"detail": "Inbound Sendgrid Webhook recieved"})


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

    return render(
        request, "sizzle/user_sizzle_report.html", {"response_data": response_data, "user": user}
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
                {"success": "true", "message": "Daily status report submitted successfully."}
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
    organizations_list_queryset = Company.objects.all().values("url", "name")
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
        TimeLog.objects.values("user__username")
        .annotate(total_duration=Sum("duration"))
        .order_by("-total_duration")
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
            all_data = TimeLog.objects.filter(
                user=request.user, created__date=last_data.created.date()
            ).order_by("created")

            total_duration = sum(
                (entry.duration for entry in all_data if entry.duration), timedelta()
            )

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
        request, "sizzle/sizzle.html", {"sizzle_data": sizzle_data, "leaderboard": leaderboard}
    )


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
def company_dashboard_hunt_detail(request, pk, template="company_dashboard_hunt_detail.html"):
    hunt = get_object_or_404(Hunt, pk=pk)
    return render(request, template, {"hunt": hunt})


@login_required(login_url="/accounts/login")
def hunt_results(request, pk, template="hunt_results.html"):
    hunt = get_object_or_404(Hunt, pk=pk)
    return render(request, template, {"hunt": hunt})


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
        recent_reports_count = IpReport.objects.filter(
            reporter_ip_address=reporter_ip, created=today
        ).count()

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
    if (
        UserBadge.objects.filter(user=user, badge__title="Mentor").exists()
        and not activity.is_approved
    ):
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

    return render(request, "sizzle/add_sizzle_checkin.html", {"yesterday_report": yesterday_report})


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

    # Return JSON if AJAX
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
