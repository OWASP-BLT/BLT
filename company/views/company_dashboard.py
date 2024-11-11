import json
import uuid
from datetime import timedelta
from urllib.parse import urlparse

from django.contrib import messages
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import ExtractMonth
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import View

from website.models import Company, Domain, Hunt, Issue
from .helper import validate_company_user

restricted_domain = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "proton.com"]

def get_email_domain(email):
    domain = email.split("@")[-1]
    return domain

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