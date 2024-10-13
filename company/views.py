import json
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlparse

import requests
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Count, OuterRef, Q, Subquery, Sum
from django.db.models.functions import ExtractMonth
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.generic import View

from website.models import Company, Domain, Hunt, HuntPrize, Issue, IssueScreenshot, Winner
from website.utils import is_valid_https_url, rebuild_safe_url

restricted_domain = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "proton.com"]


def get_email_domain(email):
    domain = email.split("@")[-1]
    return domain


def validate_company_user(func):
    def wrapper(self, request, id, *args, **kwargs):
        company = Company.objects.filter(id=id).first()

        if not company:
            return redirect("company_view")

        # Check if the user is the admin of the company
        if company.admin == request.user:
            return func(self, request, company.id, *args, **kwargs)

        # Check if the user is a manager of the company
        if company.managers.filter(id=request.user.id).exists():
            return func(self, request, company.id, *args, **kwargs)

        # Get all domains where the user is a manager
        user_domains = Domain.objects.filter(managers=request.user)

        # Check if any of these domains belong to the company
        if user_domains.filter(company=company).exists():
            return func(self, request, company.id, *args, **kwargs)

        return redirect("company_view")

    return wrapper


def check_company_or_manager(func):
    def wrapper(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return redirect("/accounts/login/")

        # Check if the user is an admin or manager of any company
        if not Company.objects.filter(Q(admin=user) | Q(managers=user)).exists():
            messages.error(request, "You are not authorized to access this resource.")
            return redirect("company_view")

        return func(self, request, *args, **kwargs)

    return wrapper


def company_view(request, *args, **kwargs):
    user = request.user

    if not user.is_active:
        messages.info(request, "Email not verified.")
        return redirect("/")

    if isinstance(user, AnonymousUser):
        messages.error(request, "Login with company or domain-provided email.")
        return redirect("/accounts/login/")

    domain = get_email_domain(user.email)

    if domain in restricted_domain:
        messages.error(request, "Login with company or domain provided email.")
        return redirect("/")

    user_companies = Company.objects.filter(Q(admin=user) | Q(managers=user))
    if not user_companies.exists():
        # Check if the user is a manager of any domain
        user_domains = Domain.objects.filter(managers=user)

        # Check if any of these domains belong to a company
        companies_with_user_domains = Company.objects.filter(domain__in=user_domains)
        if not companies_with_user_domains.exists():
            messages.error(request, "You do not have a company, create one.")
            return redirect("register_company")

    # Get the company to redirect to
    company = user_companies.first() or companies_with_user_domains.first()

    return redirect("company_analytics", id=company.id)


class RegisterCompanyView(View):
    def get(self, request, *args, **kwargs):
        return render(request, "company/register_company.html")

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.POST

        if not user.is_active:
            messages.info(request, "Email not verified.")
            return redirect("/")

        if user is None or isinstance(user, AnonymousUser):
            messages.error(request, "Login to create company")
            return redirect("/accounts/login/")

        user_domain = get_email_domain(user.email)
        company_name = data.get("company_name", "").strip().lower()

        if user_domain in restricted_domain:
            messages.error(request, "Login with company email in order to create the company.")
            return redirect("/")

        if user_domain != company_name:
            messages.error(request, "Company name doesn't match your email domain.")
            return redirect("register_company")

        if Company.objects.filter(name=company_name).exists():
            messages.error(request, "Company already exists.")
            return redirect("register_company")

        company_logo = request.FILES.get("logo")
        if company_logo:
            company_logo_file = company_logo.name.split(".")[0]
            extension = company_logo.name.split(".")[-1]
            company_logo.name = f"{company_logo_file[:99]}_{uuid.uuid4()}.{extension}"
            logo_path = default_storage.save(f"company_logos/{company_logo.name}", company_logo)
        else:
            logo_path = None

        try:
            with transaction.atomic():
                company = Company.objects.create(
                    admin=user,
                    name=company_name,
                    url=data["company_url"],
                    email=data["support_email"],
                    twitter=data.get("twitter_url", ""),
                    facebook=data.get("facebook_url", ""),
                    logo=logo_path,
                    is_active=True,
                )

                manager_emails = data.get("email", "").split(",")
                managers = User.objects.filter(email__in=manager_emails)
                company.managers.set(managers)
                company.save()

        except ValidationError as e:
            messages.error(request, f"Error saving company: {e}")
            if logo_path:
                default_storage.delete(logo_path)
            return render(request, "company/register_company.html")

        messages.success(request, "Company registered successfully.")
        return redirect("company_analytics", id=company.id)


class CompanyDashboardAnalyticsView(View):
    labels = {
        0: "General",
        1: "Number Error",
        2: "Functional",
        3: "Performance",
        4: "Security",
        5: "Typo",
        6: "Design",
        7: "Server Down",
    }
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def get_general_info(self, company):
        total_company_bugs = Issue.objects.filter(domain__company__id=company).count()
        total_bug_hunts = Hunt.objects.filter(domain__company__id=company).count()
        total_domains = Domain.objects.filter(company__id=company).count()
        # Step 1: Retrieve all hunt IDs associated with the specified company
        hunt_ids = Hunt.objects.filter(domain__company__id=company).values_list("id", flat=True)

        # Step 2: Sum the rewarded values from issues that have a hunt_id in the hunt_ids list
        total_money_distributed = Issue.objects.filter(hunt_id__in=hunt_ids).aggregate(
            total_money=Sum("rewarded")
        )["total_money"]
        total_money_distributed = 0 if total_money_distributed is None else total_money_distributed

        return {
            "total_company_bugs": total_company_bugs,
            "total_bug_hunts": total_bug_hunts,
            "total_domains": total_domains,
            "total_money_distributed": total_money_distributed,
        }

    def get_bug_report_type_piechart_data(self, company):
        bug_report_type = (
            Issue.objects.values("label")
            .filter(domain__company__id=company)
            .annotate(count=Count("label"))
        )
        bug_report_type_labels = []
        bug_report_type_data = []

        for issue_count in bug_report_type:
            bug_report_type_labels.append(self.labels[issue_count["label"]])
            bug_report_type_data.append(issue_count["count"])

        return {
            "bug_report_type_labels": json.dumps(
                bug_report_type_labels
            ),  # lst to be converted to json to avoid parsing errors
            "bug_report_type_data": json.dumps(bug_report_type_data),
        }

    def get_reports_on_domain_piechart_data(self, company):
        report_piechart = (
            Issue.objects.values("url")
            .filter(domain__company__id=company)
            .annotate(count=Count("url"))
        )

        report_labels = []
        report_data = []

        for domain_data in report_piechart:
            report_labels.append(domain_data["url"])
            report_data.append(domain_data["count"])

        return {
            "bug_report_on_domains_labels": json.dumps(report_labels),
            "bug_report_on_domains_data": json.dumps(report_data),
        }

    def get_current_year_monthly_reported_bar_data(self, company):
        # returns chart data on no of bugs reported monthly on this company for current year

        current_year = timezone.now().year
        data_monthly = (
            Issue.objects.filter(domain__company__id=company, created__year=current_year)
            .annotate(month=ExtractMonth("created"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        data = [0] * 12  # count

        for data_month in data_monthly:
            data[data_month["month"] - 1] = data_month["count"]

        # Define month labels
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
            "November",
            "December",
        ]

        return {
            "bug_monthly_report_labels": json.dumps(months),
            "bug_monthly_report_data": json.dumps(data),
            "max_count": max(data),
            "current_year": current_year,
        }

    def bug_rate_increase_descrease_weekly(self, company, is_accepted_bugs=False):
        # returns stats by comparing the count of past 8-15 days (1 week) activity to this (0 - 7) week.

        current_date = timezone.now().date()
        prev_week_start_date = current_date - timedelta(days=15)
        prev_week_end_date = current_date - timedelta(days=8)

        this_week_start_date = current_date - timedelta(days=7)
        this_week_end_date = current_date

        if is_accepted_bugs:
            prev_week_issue_count = Issue.objects.filter(
                domain__company__id=company,
                created__date__range=[prev_week_start_date, prev_week_end_date],
                verified=True,
            ).count()

            this_week_issue_count = Issue.objects.filter(
                domain__company__id=company,
                created__date__range=[this_week_start_date, this_week_end_date],
                verified=True,
            ).count()

        else:
            prev_week_issue_count = Issue.objects.filter(
                domain__company__id=company,
                created__date__range=[prev_week_start_date, prev_week_end_date],
            ).count()

            this_week_issue_count = Issue.objects.filter(
                domain__company__id=company,
                created__date__range=[this_week_start_date, this_week_end_date],
            ).count()

        if prev_week_issue_count == 0:
            percent_increase = this_week_issue_count * 100
        else:
            percent_increase = (
                (this_week_issue_count - prev_week_issue_count) / prev_week_issue_count
            ) * 100

        return {
            "percent_increase": percent_increase,
            "is_increasing": True
            if (this_week_issue_count - prev_week_issue_count) >= 0
            else False,
            "this_week_issue_count": this_week_issue_count,
        }

    def get_spent_on_bugtypes(self, company):
        spent_on_bugtypes = (
            Issue.objects.values("label")
            .filter(domain__company__id=company)
            .annotate(spent=Sum("rewarded"))
        )
        labels = list(self.labels.values())
        data = [0 for label in labels]  # make all labels spent 0 / init with 0

        for bugtype in spent_on_bugtypes:
            data[bugtype["label"]] = bugtype["spent"]

        return {
            "labels": json.dumps(labels),
            "data": json.dumps(data),
            "zipped_data": zip(labels, data),
        }

    @validate_company_user
    def get(self, request, id, *args, **kwargs):
        companies = (
            Company.objects.values("name", "id")
            .filter(Q(managers__in=[request.user]) | Q(admin=request.user))
            .distinct()
        )

        context = {
            "company": id,
            "companies": companies,
            "company_obj": Company.objects.filter(id=id).first(),
            "total_info": self.get_general_info(id),
            "bug_report_type_piechart_data": self.get_bug_report_type_piechart_data(id),
            "reports_on_domain_piechart_data": self.get_reports_on_domain_piechart_data(id),
            "get_current_year_monthly_reported_bar_data": self.get_current_year_monthly_reported_bar_data(
                id
            ),
            "bug_rate_increase_descrease_weekly": self.bug_rate_increase_descrease_weekly(id),
            "accepted_bug_rate_increase_descrease_weekly": self.bug_rate_increase_descrease_weekly(
                id, True
            ),
            "spent_on_bugtypes": self.get_spent_on_bugtypes(id),
        }
        self.get_spent_on_bugtypes(id)
        return render(request, "company/company_analytics.html", context=context)


class CompanyDashboardManageBugsView(View):
    @validate_company_user
    def get(self, request, id, *args, **kwargs):
        companies = (
            Company.objects.values("name", "id")
            .filter(Q(managers__in=[request.user]) | Q(admin=request.user))
            .distinct()
        )

        company_obj = Company.objects.filter(id=id).first()

        # get all domains of this company
        domains = Domain.objects.filter(company_id=id)

        # get all issues where the url is in the domains in descending order
        issues = Issue.objects.filter(domain__in=domains).order_by("-created")

        context = {
            "company": id,
            "companies": companies,
            "company_obj": company_obj,
            "issues": issues,
        }
        return render(request, "company/company_manage_bugs.html", context=context)


class CompanyDashboardManageDomainsView(View):
    @validate_company_user
    def get(self, request, id, *args, **kwargs):
        domains = (
            Domain.objects.values("id", "name", "url", "logo")
            .filter(company__id=id)
            .order_by("modified")
        )

        companies = (
            Company.objects.values("name", "id")
            .filter(Q(managers__in=[request.user]) | Q(admin=request.user))
            .distinct()
        )

        context = {
            "company": id,
            "companies": companies,
            "company_obj": Company.objects.filter(id=id).first(),
            "domains": domains,
        }

        return render(request, "company/company_manage_domains.html", context=context)


class AddDomainView(View):
    def dispatch(self, request, *args, **kwargs):
        method = self.request.POST.get("_method", "").lower()

        if method == "delete":
            return self.delete(request, *args, **kwargs)
        elif method == "put":
            return self.put(request, *args, **kwargs)

        return super().dispatch(request, *args, **kwargs)

    @validate_company_user
    def get(self, request, id, *args, **kwargs):
        companies = (
            Company.objects.values("name", "id")
            .filter(Q(managers__in=[request.user]) | Q(admin=request.user))
            .distinct()
        )

        users = User.objects.filter(is_active=True)
        domain_id = kwargs.get("domain_id")
        domain = Domain.objects.filter(id=domain_id).first() if domain_id else None
        context = {
            "company": id,
            "company_obj": Company.objects.filter(id=id).first(),
            "companies": companies,
            "users": users,
            "domain": domain,  # Pass the domain to the template if it exists
        }

        if domain:
            return render(request, "company/edit_domain.html", context=context)
        else:
            return render(request, "company/add_domain.html", context=context)

    @validate_company_user
    @check_company_or_manager
    def post(self, request, id, *args, **kwargs):
        domain_data = {
            "name": request.POST.get("domain_name", None),
            "url": request.POST.get("domain_url", None),
            "github": request.POST.get("github_url", None),
            "twitter": request.POST.get("twitter_url", None),
            "facebook": request.POST.get("facebook_url", None),
        }

        if domain_data["url"]:
            parsed_url = urlparse(domain_data["url"])
            if parsed_url.hostname is None:
                messages.error(request, "Invalid domain url")
                return redirect("add_domain", id=id)
            domain_data["url"] = parsed_url.netloc

        if domain_data["name"] is None:
            messages.error(request, "Enter domain name")
            return redirect("add_domain", id=id)

        if domain_data["url"] is None:
            messages.error(request, "Enter domain url")
            return redirect("add_domain", id=id)

        domain = (parsed_url.hostname).replace("www.", "")

        domain_data["name"] = domain_data["name"].lower()

        managers_list = request.POST.getlist("user")
        company_obj = Company.objects.get(id=id)

        domain_exist = Domain.objects.filter(
            Q(name=domain_data["name"]) | Q(url=domain_data["url"])
        ).exists()

        if domain_exist:
            messages.error(request, "Domain name or url already exist.")
            return redirect("add_domain", id=id)

        # validate domain url
        try:
            if is_valid_https_url(domain_data["url"]):
                safe_url = rebuild_safe_url(domain_data["url"])
                try:
                    response = requests.get(safe_url, timeout=5)
                    if response.status_code != 200:
                        raise Exception
                except requests.exceptions.RequestException:
                    messages.error(request, "Domain does not exist.")
                    return redirect("add_domain", id=id)
        except ValueError:
            messages.error(request, "URL validation error.")
            return redirect("add_domain", id=id)

        # validate domain email
        user_email_domain = request.user.email.split("@")[-1]

        if not domain.endswith(f".{user_email_domain}") and domain != user_email_domain:
            messages.error(request, "Your email does not match domain email. Action Denied!")
            return redirect("add_domain", id=id)

        for domain_manager_email in managers_list:
            manager_email_domain = domain_manager_email.split("@")[-1]
            if not domain.endswith(f".{manager_email_domain}") and domain != manager_email_domain:
                messages.error(
                    request, f"Manager: {domain_manager_email} does not match domain email."
                )
                return redirect("add_domain", id=id)

        if request.FILES.get("logo"):
            domain_logo = request.FILES.get("logo")
            domain_logo_file = domain_logo.name.split(".")[0]
            extension = domain_logo.name.split(".")[-1]
            domain_logo.name = domain_logo_file[:99] + str(uuid.uuid4()) + "." + extension
            default_storage.save(f"logos/{domain_logo.name}", domain_logo)
            logo_name = f"logos/{domain_logo.name}"
        else:
            logo_name = ""

        if request.FILES.get("webshot"):
            webshot_logo = request.FILES.get("webshot")
            webshot_logo_file = webshot_logo.name.split(".")[0]
            extension = webshot_logo.name.split(".")[-1]
            webshot_logo.name = webshot_logo_file[:99] + str(uuid.uuid4()) + "." + extension
            default_storage.save(f"webshots/{webshot_logo.name}", webshot_logo)
            webshot_logo_name = f"webshots/{webshot_logo.name}"
        else:
            webshot_logo_name = ""

        if domain_data["facebook"] and "facebook.com" not in domain_data["facebook"]:
            messages.error(request, "Facebook url should contain facebook.com")
            return redirect("add_domain", id=id)
        if domain_data["twitter"]:
            if (
                "twitter.com" not in domain_data["twitter"]
                and "x.com" not in domain_data["twitter"]
            ):
                messages.error(request, "Twitter url should contain twitter.com or x.com")
            return redirect("add_domain", id=id)
        if domain_data["github"] and "github.com" not in domain_data["github"]:
            messages.error(request, "Github url should contain github.com")
            return redirect("add_domain", id=id)

        domain_managers = User.objects.filter(email__in=managers_list, is_active=True)

        domain = Domain.objects.create(
            **domain_data,
            company=company_obj,
            logo=logo_name,
            webshot=webshot_logo_name,
        )

        domain.managers.set(domain_managers)
        domain.save()

        return redirect("company_manage_domains", id=id)

    @validate_company_user
    @check_company_or_manager
    def put(self, request, id, *args, **kwargs):
        domain_id = kwargs.get("domain_id")
        domain = get_object_or_404(Domain, id=domain_id)

        domain_data = {
            "name": request.POST.get("domain_name", None),
            "url": request.POST.get("domain_url", None),
            "github": request.POST.get("github_url", None),
            "twitter": request.POST.get("twitter_url", None),
            "facebook": request.POST.get("facebook_url", None),
        }

        if domain_data["name"] is None:
            messages.error(request, "Enter domain name")
            return redirect("edit_domain", id=id, domain_id=domain_id)

        if domain_data["url"] is None:
            messages.error(request, "Enter domain url")
            return redirect("edit_domain", id=id, domain_id=domain_id)

        parsed_url = urlparse(domain_data["url"])
        domain_name = (parsed_url.hostname).replace("www.", "")

        domain_data["name"] = domain_data["name"].lower()

        managers_list = request.POST.getlist("user")
        company_obj = Company.objects.get(id=id)

        domain_exist = (
            Domain.objects.filter(Q(name=domain_data["name"]) | Q(url=domain_data["url"]))
            .exclude(id=domain_id)
            .exists()
        )
        if domain_exist:
            messages.error(request, "Domain name or url already exist.")
            return redirect("edit_domain", id=id, domain_id=domain_id)

        # validate domain url
        try:
            if is_valid_https_url(domain_data["url"]):
                safe_url = rebuild_safe_url(domain_data["url"])
                try:
                    response = requests.get(safe_url, timeout=5, verify=False)
                    if response.status_code != 200:
                        raise Exception
                except requests.exceptions.RequestException:
                    messages.error(request, "Domain does not exist.")
                    return redirect("edit_domain", id=id, domain_id=domain_id)
        except ValueError:
            messages.error(request, "URL validation error.")
            return redirect("edit_domain", id=id, domain_id=domain_id)

        # validate domain email
        user_email_domain = request.user.email.split("@")[-1]

        if not domain_name.endswith(f".{user_email_domain}") and domain_name != user_email_domain:
            messages.error(request, "Your email does not match domain email. Action Denied!")
            return redirect("edit_domain", id=id, domain_id=domain_id)

        for domain_manager_email in managers_list:
            manager_email_domain = domain_manager_email.split("@")[-1]
            if (
                not domain_name.endswith(f".{manager_email_domain}")
                and domain_name != manager_email_domain
            ):
                messages.error(
                    request, f"Manager: {domain_manager_email} does not match domain email."
                )
                return redirect("edit_domain", id=id, domain_id=domain_id)

        if request.FILES.get("logo"):
            domain_logo = request.FILES.get("logo")
            domain_logo_file = domain_logo.name.split(".")[0]
            extension = domain_logo.name.split(".")[-1]
            domain_logo.name = domain_logo_file[:99] + str(uuid.uuid4()) + "." + extension
            default_storage.save(f"logos/{domain_logo.name}", domain_logo)
            domain.logo = f"logos/{domain_logo.name}"

        if request.FILES.get("webshot"):
            webshot_logo = request.FILES.get("webshot")
            webshot_logo_file = webshot_logo.name.split(".")[0]
            extension = webshot_logo.name.split(".")[-1]
            webshot_logo.name = webshot_logo_file[:99] + str(uuid.uuid4()) + "." + extension
            default_storage.save(f"webshots/{webshot_logo.name}", webshot_logo)
            domain.webshot = f"webshots/{webshot_logo.name}"

        if domain_data["facebook"] and "facebook.com" not in domain_data["facebook"]:
            messages.error(request, "Facebook url should contain facebook.com")
            return redirect("edit_domain", id=id, domain_id=domain_id)
        if domain_data["twitter"]:
            if (
                "twitter.com" not in domain_data["twitter"]
                and "x.com" not in domain_data["twitter"]
            ):
                messages.error(request, "Twitter url should contain twitter.com or x.com")
                return redirect("edit_domain", id=id, domain_id=domain_id)
        if domain_data["github"] and "github.com" not in domain_data["github"]:
            messages.error(request, "Github url should contain github.com")
            return redirect("edit_domain", id=id, domain_id=domain_id)

        domain.name = domain_data["name"]
        domain.url = domain_data["url"]
        domain.github = domain_data["github"]
        domain.twitter = domain_data["twitter"]
        domain.facebook = domain_data["facebook"]
        domain.company = company_obj

        domain_managers = User.objects.filter(email__in=managers_list, is_active=True)
        domain.managers.set(domain_managers)
        domain.save()

        return redirect("company_manage_domains", id=id)

    @validate_company_user
    @check_company_or_manager
    def delete(self, request, id, *args, **kwargs):
        domain_id = request.POST.get("domain_id", None)
        domain = get_object_or_404(Domain, id=domain_id)
        if domain is None:
            messages.error(request, "Domain not found.")
            return redirect("company_manage_domains", id=id)
        domain.delete()
        messages.success(request, "Domain deleted successfully")
        return redirect("company_manage_domains", id=id)


class DomainView(View):
    def get_current_year_monthly_reported_bar_data(self, domain_id):
        # returns chart data on no of bugs reported monthly on this company for current year

        current_year = timezone.now().year
        data_monthly = (
            Issue.objects.filter(domain__id=domain_id, created__year=current_year)
            .annotate(month=ExtractMonth("created"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        data = [0] * 12  # Initialize a list of 12 zeros for each month

        for data_month in data_monthly:
            data[data_month["month"] - 1] = data_month["count"]

        return data

    def get(self, request, pk, *args, **kwargs):
        domain = (
            Domain.objects.values(
                "id",
                "name",
                "url",
                "company__name",
                "created",
                "modified",
                "twitter",
                "facebook",
                "github",
                "logo",
                "webshot",
            )
            .filter(id=pk)
            .first()
        )

        if not domain:
            raise Http404("Domain not found")

        total_money_distributed = Issue.objects.filter(domain__id=domain["id"]).aggregate(
            total_money=Sum("rewarded")
        )["total_money"]
        total_money_distributed = 0 if total_money_distributed is None else total_money_distributed

        # Query the database for the exact domain
        total_bug_reported = Issue.objects.filter(domain__id=domain["id"]).count()
        total_bug_accepted = Issue.objects.filter(domain__id=domain["id"], verified=True).count()

        is_domain_manager = Domain.objects.filter(
            Q(id=domain["id"]) & Q(managers__in=[request.user])
        ).exists()
        if is_domain_manager:
            latest_issues = (
                Issue.objects.values(
                    "id",
                    "domain__name",
                    "url",
                    "description",
                    "user__id",
                    "user__username",
                    "user__userprofile__user_avatar",
                    "label",
                    "status",
                    "verified",
                    "rewarded",
                    "created",
                )
                .filter(domain__id=domain["id"])
                .annotate(
                    first_screenshot=Subquery(
                        IssueScreenshot.objects.filter(issue_id=OuterRef("pk")).values("image")[:1]
                    )
                )
                .order_by("-created")[:5]
            )
        else:
            latest_issues = (
                Issue.objects.values(
                    "id",
                    "domain__name",
                    "url",
                    "description",
                    "user__id",
                    "user__username",
                    "user__userprofile__user_avatar",
                    "label",
                    "status",
                    "verified",
                    "rewarded",
                    "created",
                )
                .filter(domain__id=domain["id"], is_hidden=False)
                .annotate(
                    first_screenshot=Subquery(
                        IssueScreenshot.objects.filter(issue_id=OuterRef("pk")).values("image")[:1]
                    )
                )
                .order_by("-created")[:5]
            )
        issue_labels = [label[-1] for label in Issue.labels]
        cleaned_issues = []
        for issue in latest_issues:
            cleaned_issues.append({**issue, "label": issue_labels[issue["label"]]})

        # get top testers
        top_testers = (
            Issue.objects.values("user__id", "user__username", "user__userprofile__user_avatar")
            .filter(domain__id=domain["id"], user__isnull=False)
            .annotate(count=Count("user__username"))
            .order_by("-count")[:5]
        )

        # Get first and last bugs
        first_bug = Issue.objects.filter(domain__id=domain["id"]).order_by("created").first()
        last_bug = Issue.objects.filter(domain__id=domain["id"]).order_by("-created").first()

        ongoing_bughunts = Hunt.objects.filter(domain__id=domain["id"]).annotate(
            total_prize=Sum("huntprize__value")
        )[:3]
        context = {
            **domain,
            "total_money_distributed": total_money_distributed,
            "total_bug_reported": total_bug_reported,
            "total_bug_accepted": total_bug_accepted,
            "latest_issues": cleaned_issues,
            "monthly_activity_chart": json.dumps(
                self.get_current_year_monthly_reported_bar_data(domain["id"])
            ),
            "top_testers": top_testers,
            "first_bug": first_bug,
            "last_bug": last_bug,
            "ongoing_bughunts": ongoing_bughunts,
        }

        return render(request, "company/view_domain.html", context)


class CompanyDashboardManageRolesView(View):
    @validate_company_user
    def get(self, request, id, *args, **kwargs):
        companies = (
            Company.objects.values("name", "id")
            .filter(Q(managers__in=[request.user]) | Q(admin=request.user))
            .distinct()
        )

        company_url = Company.objects.filter(id=id).first().url
        parsed_url = urlparse(company_url).netloc
        company_domain = parsed_url.replace("www.", "")
        company_users = User.objects.filter(email__endswith=f"@{company_domain}").values(
            "id", "username", "email"
        )

        # Convert company_users QuerySet to list of dicts
        company_users_list = list(company_users)

        domains = Domain.objects.filter(
            Q(company__id=id)
            & (Q(company__managers__in=[request.user]) | Q(company__admin=request.user))
            | Q(managers=request.user)
        ).distinct()

        domains_data = []
        for domain in domains:
            _id = domain.id
            name = domain.name
            company_admin = domain.company.admin
            # Convert managers QuerySet to list of dicts
            managers = list(domain.managers.values("id", "username", "userprofile__user_avatar"))
            domains_data.append(
                {"id": _id, "name": name, "managers": managers, "company_admin": company_admin}
            )

        context = {
            "company": id,
            "company_obj": Company.objects.filter(id=id).first(),
            "companies": list(companies),  # Convert companies QuerySet to list of dicts
            "domains": domains_data,
            "company_users": company_users_list,  # Use the converted list
        }

        return render(request, "company/company_manage_roles.html", context)

    def post(self, request, id, *args, **kwargs):
        domain = Domain.objects.filter(
            Q(company__id=id)
            & Q(id=request.POST.get("domain_id"))
            & (Q(company__admin=request.user) | Q(managers__in=[request.user]))
        ).first()

        if domain is None:
            messages.error("you are not manager of this domain.")
            return redirect("company_manage_roles", id)

        if not request.POST.getlist("user[]"):
            messages.error(request, "No user selected.")
            return redirect("company_manage_roles", id)

        managers_list = request.POST.getlist("user[]")
        domain_managers = User.objects.filter(username__in=managers_list, is_active=True)

        for manager in domain_managers:
            user_email_domain = manager.email.split("@")[-1]
            company_url = domain.company.url
            parsed_url = urlparse(company_url).netloc
            company_domain = parsed_url.replace("www.", "")
            if user_email_domain == company_domain:
                domain.managers.add(manager.id)
            else:
                messages.error(request, f"Manager: {manager.email} does not match domain email.")
                return redirect("company_manage_roles", id)

        messages.success(request, "successfully added the managers")
        return redirect("company_manage_roles", id)


class ShowBughuntView(View):
    def get(self, request, pk, *args, **kwargs):
        hunt_obj = get_object_or_404(Hunt, pk=pk)

        # get issues/reports that are done between hunt.start_date and hunt.end_date
        hunt_issues = Issue.objects.filter(hunt__id=hunt_obj.id)

        # total bugs reported in this bughunt
        total_bugs = hunt_issues.count()
        total_bug_accepted = hunt_issues.filter(verified=True).count()

        total_money_distributed = hunt_issues.aggregate(total_money=Sum("rewarded"))["total_money"]
        total_money_distributed = 0 if total_money_distributed is None else total_money_distributed

        bughunt_leaderboard = (
            hunt_issues.values("user__id", "user__username", "user__userprofile__user_avatar")
            .filter(user__isnull=False, verified=True)
            .annotate(count=Count("user__username"))
            .order_by("-count")[:16]
        )

        # Get the company associated with the domain of the hunt
        company = hunt_obj.domain.company

        # Check if the user is either a manager of the domain or the admin of the company
        is_hunt_manager = hunt_obj.domain.managers.filter(id=request.user.id).exists() or (
            company and company.admin == request.user
        )

        # get latest reported public issues
        if is_hunt_manager:
            latest_issues = (
                Issue.objects.values(
                    "id",
                    "domain__name",
                    "url",
                    "description",
                    "user__id",
                    "user__username",
                    "user__userprofile__user_avatar",
                    "label",
                    "status",
                    "verified",
                    "rewarded",
                    "created",
                )
                .filter(hunt__id=hunt_obj.id)
                .annotate(
                    first_screenshot=Subquery(
                        IssueScreenshot.objects.filter(issue_id=OuterRef("pk")).values("image")[:1]
                    )
                )
                .order_by("-created")
            )
        else:
            latest_issues = (
                Issue.objects.values(
                    "id",
                    "domain__name",
                    "url",
                    "description",
                    "user__id",
                    "user__username",
                    "user__userprofile__user_avatar",
                    "label",
                    "status",
                    "verified",
                    "rewarded",
                    "created",
                )
                .filter(hunt__id=hunt_obj.id, is_hidden=False)
                .annotate(
                    first_screenshot=Subquery(
                        IssueScreenshot.objects.filter(issue_id=OuterRef("pk")).values("image")[:1]
                    )
                )
                .order_by("-created")
            )

        issue_labels = [label[-1] for label in Issue.labels]
        cleaned_issues = []
        for issue in latest_issues:
            cleaned_issues.append({**issue, "label": issue_labels[issue["label"]]})

        # Get first and last bugs
        first_bug = Issue.objects.filter(hunt__id=hunt_obj.id).order_by("created").first()
        last_bug = Issue.objects.filter(hunt__id=hunt_obj.id).order_by("-created").first()

        # get top testers
        top_testers = (
            Issue.objects.values("user__id", "user__username", "user__userprofile__user_avatar")
            .filter(user__isnull=False)
            .annotate(count=Count("user__username"))
            .order_by("-count")[:5]
        )

        # bughunt prizes
        rewards = HuntPrize.objects.filter(hunt_id=hunt_obj.id)
        winners_count = {
            reward.id: Winner.objects.filter(prize_id=reward.id).count() for reward in rewards
        }

        # check winner have for this bughunt
        winners = Winner.objects.filter(hunt_id=hunt_obj.id).select_related("prize")

        context = {
            "hunt_obj": hunt_obj,
            "stats": {
                "total_rewarded": total_money_distributed,
                "total_bugs": total_bugs,
                "total_bug_accepted": total_bug_accepted,
            },
            "bughunt_leaderboard": bughunt_leaderboard,
            "top_testers": top_testers,
            "latest_issues": cleaned_issues,
            "rewards": rewards,
            "winners_count": winners_count,
            "first_bug": first_bug,
            "last_bug": last_bug,
            "winners": winners,
            "is_hunt_manager": is_hunt_manager,
        }

        return render(request, "company/bughunt/view_bughunt.html", context)


class EndBughuntView(View):
    def get(self, request, pk, *args, **kwargs):
        hunt = get_object_or_404(Hunt, pk=pk)

        # Get the company associated with the domain of the hunt
        company = hunt.domain.company

        # Check if the user is either a manager of the domain or the admin of the company
        is_hunt_manager = hunt.domain.managers.filter(id=request.user.id).exists() or (
            company and company.admin == request.user
        )

        if not is_hunt_manager:
            return Http404("User not allowed")

        hunt.result_published = True
        hunt.save()
        company = hunt.domain.company.id

        messages.success(request, f"successfully Ended Bughunt {hunt.name}")
        return redirect("company_manage_bughunts", id=company)


class AddHuntView(View):
    def edit(self, request, id, companies, domains, hunt_id, *args, **kwargs):
        hunt = get_object_or_404(Hunt, pk=hunt_id)
        prizes = HuntPrize.objects.values().filter(hunt__id=hunt_id)

        context = {
            "company": id,
            "company_obj": Company.objects.filter(id=id).first(),
            "companies": companies,
            "domains": domains,
            "hunt": hunt,
            "prizes": prizes,
            "markdown_value": hunt.description,
        }

        return render(request, "company/bughunt/edit_bughunt.html", context)

    @validate_company_user
    def get(self, request, id, *args, **kwargs):
        hunt_id = request.GET.get("hunt", None)

        companies = (
            Company.objects.values("name", "id")
            .filter(Q(managers__in=[request.user]) | Q(admin=request.user))
            .distinct()
        )

        domains = Domain.objects.values("id", "name").filter(company__id=id)

        if hunt_id is not None:
            return self.edit(request, id, companies, domains, hunt_id, *args, **kwargs)

        context = {
            "company": id,
            "company_obj": Company.objects.filter(id=id).first(),
            "companies": companies,
            "domains": domains,
        }

        return render(request, "company/bughunt/add_bughunt.html", context)

    @validate_company_user
    @check_company_or_manager
    def post(self, request, id, *args, **kwargs):
        data = request.POST

        hunt_id = data.get("hunt_id", None)  # when post is for edit hunt
        is_edit = True if hunt_id is not None else False

        if is_edit:
            hunt = get_object_or_404(Hunt, pk=hunt_id)

        domain = Domain.objects.filter(id=data.get("domain", None)).first()

        if domain is None:
            messages.error(request, "Domain Does not exists")
            return redirect("add_bughunt", id)

        start_date = data.get("start_date", datetime.now().strftime("%m/%d/%Y"))
        end_date = data.get("end_date", datetime.now().strftime("%m/%d/%Y"))

        try:
            start_date = datetime.strptime(start_date, "%m/%d/%Y").strftime("%Y-%m-%d %H:%M")
            end_date = datetime.strptime(end_date, "%m/%d/%Y").strftime("%Y-%m-%d %H:%M")
        except ValueError:
            messages.error(request, "Invalid Date Format")
            return redirect("add_bughunt", id)

        # apply validation for date not valid
        if start_date > end_date:
            messages.error(request, "Start date should be less than end date")
            return redirect("add_bughunt", id)

        hunt_logo = request.FILES.get("logo", None)
        if hunt_logo is not None:
            hunt_logo_file = hunt_logo.name.split(".")[0]
            extension = hunt_logo.name.split(".")[-1]
            hunt_logo.name = hunt_logo_file[:99] + str(uuid.uuid4()) + "." + extension
            default_storage.save(f"logos/{hunt_logo.name}", hunt_logo)

        banner_logo = request.FILES.get("banner", None)
        if banner_logo is not None:
            banner_logo_file = banner_logo.name.split(".")[0]
            extension = banner_logo.name.split(".")[-1]
            banner_logo.name = banner_logo_file[:99] + str(uuid.uuid4()) + "." + extension
            default_storage.save(f"banners/{banner_logo.name}", banner_logo)

        if is_edit:
            hunt.domain = domain
            hunt.url = data.get("domain_url", "")
            hunt.description = data.get("markdown-description", "")

            if not hunt.is_published:
                hunt.name = data.get("bughunt_name", "")
                hunt.starts_on = start_date

            hunt.end_on = end_date
            hunt.is_published = False if data["publish_bughunt"] == "false" else True

            if hunt_logo is not None:
                hunt.logo = f"logos/{hunt_logo.name}"
            if banner_logo is not None:
                hunt.banner = f"banners/{banner_logo.name}"

            hunt.save()

        else:
            hunt = Hunt.objects.create(
                name=data.get("bughunt_name", ""),
                domain=domain,
                url=data.get("domain_url", ""),
                description=data.get("markdown-description", ""),
                starts_on=start_date,
                end_on=end_date,
                is_published=False if data["publish_bughunt"] == "false" else True,
            )

        prizes = json.loads(data.get("prizes", "[]"))

        for prize in prizes:
            if prize.get("prize_name", "").strip() == "":
                continue

            HuntPrize.objects.create(
                hunt=hunt,
                name=prize["prize_name"],
                value=prize.get("cash_value", 0),
                no_of_eligible_projects=prize.get("number_of_winning_projects", 1),
                valid_submissions_eligible=prize.get("every_valid_submissions", False),
                prize_in_crypto=prize.get("paid_in_cryptocurrency", False),
                description=prize.get("prize_description", ""),
            )

        messages.success(request, "successfully added the managers")
        return redirect("company_manage_bughunts", id)


class CompanyDashboardManageBughuntView(View):
    @validate_company_user
    def get(self, request, id, *args, **kwargs):
        companies = (
            Company.objects.values("name", "id")
            .filter(Q(managers__in=[request.user]) | Q(admin=request.user))
            .distinct()
        )

        query = Hunt.objects.values(
            "id",
            "name",
            "prize",
            "is_published",
            "result_published",
            "starts_on__day",
            "starts_on__month",
            "starts_on__year",
            "end_on__day",
            "end_on__month",
            "end_on__year",
        ).filter(domain__company__id=id)
        filtered_bughunts = {
            "all": query,
            "ongoing": query.filter(result_published=False, is_published=True),
            "ended": query.filter(result_published=True),
            "draft": query.filter(result_published=False, is_published=False),
        }

        filter_type = request.GET.get("filter", "all")

        context = {
            "company": id,
            "company_obj": Company.objects.filter(id=id).first(),
            "companies": companies,
            "bughunts": filtered_bughunts.get(filter_type, []),
        }

        return render(request, "company/bughunt/company_manage_bughunts.html", context)


@require_http_methods(["DELETE"])
def delete_prize(request, prize_id, company_id):
    if not request.user.company_set.filter(id=company_id).exists():
        return JsonResponse({"success": False, "error": "User not allowed"})
    try:
        prize = HuntPrize.objects.get(id=prize_id)
        prize.delete()
        return JsonResponse({"success": True})
    except HuntPrize.DoesNotExist:
        return JsonResponse({"success": False, "error": "Prize not found"})


@require_http_methods(["PUT"])
def edit_prize(request, prize_id, company_id):
    if not request.user.company_set.filter(id=company_id).exists():
        return JsonResponse({"success": False, "error": "User not allowed"})

    try:
        prize = HuntPrize.objects.get(id=prize_id)
    except HuntPrize.DoesNotExist:
        return JsonResponse({"success": False, "error": "Prize not found"})

    data = json.loads(request.body)
    prize.name = data.get("prize_name", prize.name)
    prize.value = data.get("cash_value", prize.value)
    prize.no_of_eligible_projects = data.get(
        "number_of_winning_projects", prize.no_of_eligible_projects
    )
    prize.valid_submissions_eligible = data.get(
        "every_valid_submissions", prize.valid_submissions_eligible
    )
    prize.description = data.get("prize_description", prize.description)
    prize.save()

    return JsonResponse({"success": True})


def accept_bug(request, issue_id, reward_id=None):
    with transaction.atomic():
        issue = get_object_or_404(Issue, id=issue_id)

        if reward_id == "no_reward":
            issue.verified = True
            issue.rewarded = 0
            issue.save()
            Winner(
                hunt_id=issue.hunt.id, prize_id=None, winner_id=issue.user.id, prize_amount=0
            ).save()
        else:
            reward = get_object_or_404(HuntPrize, id=reward_id)
            issue.verified = True
            issue.rewarded = reward.value
            issue.save()
            Winner(
                hunt_id=issue.hunt.id,
                prize_id=reward.id,
                winner_id=issue.user.id,
                prize_amount=reward.value,
            ).save()

        return redirect("show_bughunt", pk=issue.hunt.id)


@require_http_methods(["DELETE"])
def delete_manager(request, manager_id, domain_id):
    try:
        domain = Domain.objects.get(id=domain_id)
        manager = User.objects.get(id=manager_id)

        # Ensure the request user is allowed to perform this action
        if not (request.user == domain.company.admin):
            # return error with not permission msg
            return JsonResponse(
                {"success": False, "message": "You do not have permission to delete this manager."},
                status=403,
            )

        if manager in domain.managers.all():
            domain.managers.remove(manager)
            return JsonResponse({"success": True})

        return JsonResponse({"success": False, "message": "Manager not found in domain."})

    except Domain.DoesNotExist:
        return JsonResponse({"success": False, "message": "Domain not found."})
    except User.DoesNotExist:
        return JsonResponse({"success": False, "message": "User not found."})
