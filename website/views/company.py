import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import FieldError, ValidationError
from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, F, OuterRef, Q, Subquery, Sum
from django.db.models.functions import ExtractMonth
from django.http import Http404, HttpResponseBadRequest, HttpResponseServerError, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.generic import View
from slack_bolt import App

from website.models import (
    DailyStatusReport,
    Domain,
    Hunt,
    HuntPrize,
    Integration,
    IntegrationServices,
    Issue,
    IssueScreenshot,
    Organization,
    OrganizationAdmin,
    SlackIntegration,
    Winner,
)
from website.utils import check_security_txt, is_valid_https_url, rebuild_safe_url

logger = logging.getLogger("slack_bolt")
logger.setLevel(logging.WARNING)


def validate_organization_user(func):
    def wrapper(self, request, id, *args, **kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            messages.error(request, "Please login to access this page.")
            return redirect("/accounts/login/")

        # Get organization and verify it exists
        organization = Organization.objects.filter(id=id).first()
        if not organization:
            messages.error(request, "Organization does not exist.")
            return redirect("/")

        # Check if user is admin or manager of the organization
        is_member = organization.admin == request.user or organization.managers.filter(id=request.user.id).exists()

        if not is_member:
            messages.error(request, "You do not have permission to access this organization's integrations.")
            return redirect("/")

        return func(self, request, id, *args, **kwargs)

    return wrapper


def check_organization_or_manager(func):
    def wrapper(self, request, *args, **kwargs):
        # Allow public access - no authentication required
        return func(self, request, *args, **kwargs)

    return wrapper


def _get_user_organization(user):
    """Helper function to find and return a user's organization."""
    if not user.is_active:
        return None, "Email not verified."

    if isinstance(user, AnonymousUser):
        return None, "Please login to access your organization."

    user_organizations = Organization.objects.filter(Q(admin=user) | Q(managers=user))
    if not user_organizations.exists():
        # Check if the user is a manager of any domain
        user_domains = Domain.objects.filter(managers=user)

        # Check if any of these domains belong to a organization
        organizations_with_user_domains = Organization.objects.filter(domain__in=user_domains)
        if not organizations_with_user_domains.exists():
            return None, "You do not have a organization, create one."

    # Get the organization to redirect to
    organization = user_organizations.first() or organizations_with_user_domains.first()
    return organization, None


def Organization_view(request, *args, **kwargs):
    user = request.user

    organization, error_message = _get_user_organization(user)
    if error_message:
        messages.error(request, error_message)
        if error_message == "Email not verified.":
            return redirect("/")
        elif error_message == "Please login to access your organization.":
            return redirect("/accounts/login/")
        else:
            return redirect("register_organization")

    return redirect("organization_detail", slug=organization.slug)


def dashboard_view(request, *args, **kwargs):
    user = request.user

    organization, error_message = _get_user_organization(user)
    if error_message:
        messages.error(request, error_message)
        if error_message == "Email not verified.":
            return redirect("/")
        elif error_message == "Please login to access your organization.":
            return redirect("/accounts/login/")
        else:
            return redirect("register_organization")

    # Redirect to organization dashboard
    return redirect("organization_analytics", id=organization.id)


class RegisterOrganizationView(View):
    def get(self, request, *args, **kwargs):
        recent_organizations = Organization.objects.filter(is_active=True).order_by("-created")[:5]
        context = {"recent_organizations": recent_organizations}
        return render(request, "organization/register_organization.html", context)

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.POST

        if not user.is_active:
            messages.info(request, "Email not verified.")
            return redirect("/")

        if user is None or isinstance(user, AnonymousUser):
            messages.error(request, "Login to create organization")
            return redirect("/accounts/login/")

        organization_name = data.get("organization_name", "")
        organization_url = data.get("organization_url", "")
        support_email = data.get("support_email", "")
        twitter_url = data.get("twitter_url", "")
        facebook_url = data.get("facebook_url", "")

        if organization_name == "" or Organization.objects.filter(name=organization_name).exists():
            messages.error(request, "organization name is invalid or already exists.")
            return redirect("register_organization")

        if organization_url == "" or Organization.objects.filter(url=organization_url).exists():
            messages.error(request, "organization URL is invalid or already exists.")
            return redirect("register_organization")

        # Database constraint set to 255 char
        if len(organization_url) > 255:
            messages.error(request, "Organization URL is too long (maximum 255 characters).")
            return redirect("register_organization")

        organization_logo = request.FILES.get("logo")
        if organization_logo:
            organization_logo_file = organization_logo.name.split(".")[0]
            extension = organization_logo.name.split(".")[-1]
            organization_logo.name = f"{organization_logo_file[:99]}_{uuid.uuid4()}.{extension}"
            logo_path = default_storage.save(f"organization_logos/{organization_logo.name}", organization_logo)
        else:
            logo_path = None

        try:
            with transaction.atomic():
                organization = Organization.objects.create(
                    admin=user,
                    name=organization_name,
                    url=organization_url,
                    email=support_email,
                    twitter=twitter_url,
                    facebook=facebook_url,
                    logo=logo_path,
                    is_active=True,
                )

                manager_emails = data.get("email", "").split(",")
                managers = User.objects.filter(email__in=manager_emails)
                organization.managers.set(managers)
                organization.save()

        except ValidationError as e:
            messages.error(request, f"Error saving organization: {e}")
            if logo_path:
                default_storage.delete(logo_path)
            return render(request, "organization/register_organization.html")
        except Exception as e:
            if "value too long" in str(e):
                messages.error(
                    request,
                    "One of the entered values is too long. Please check that all URLs and text fields are within the allowed length limits.",
                )
            else:
                messages.error(request, f"Error creating organization: {e}")
            if logo_path:
                default_storage.delete(logo_path)
            return render(request, "organization/register_organization.html")

        messages.success(request, "organization registered successfully.")
        return redirect("organization_detail", slug=organization.slug)


class OrganizationDashboardAnalyticsView(View):
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
    months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    def get_security_incidents_summary(self, organization):
        # Get all security-related issues (label=4)
        security_issues = Issue.objects.filter(
            domain__organization__id=organization,
            label=4,  # Security label
        )

        # Calculate severity distribution
        # Note: Check if the severity field exists - currently not defined in the Issue model
        try:
            severity_counts = security_issues.values("severity").annotate(count=Count("id"))
        except FieldError:
            # Severity field doesn't exist, provide empty list
            severity_counts = []

        # Get recent security incidents (last 30 days)
        recent_incidents = security_issues.filter(created__gte=timezone.now() - timedelta(days=30))

        # Calculate average resolution time
        resolved_issues = security_issues.filter(status="resolved")
        resolved_issues = resolved_issues.filter(closed_date__isnull=False)
        avg_resolution_time = resolved_issues.aggregate(avg_time=Avg(F("closed_date") - F("created")))["avg_time"]

        return {
            "total_security_issues": security_issues.count(),
            "recent_incidents": recent_incidents.count(),
            "severity_distribution": list(severity_counts),
            "avg_resolution_time": avg_resolution_time,
            "top_affected_domains": security_issues.values("domain__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:5],
        }

    def get_threat_intelligence(self, organization):
        """Gets threat intelligence data for the organization."""
        security_issues = Issue.objects.filter(
            domain__organization__id=organization,
            label=4,  # Security label
        )

        # Get trending attack types based on issue labels/tags instead
        attack_vectors = (
            security_issues.filter(created__gte=timezone.now() - timedelta(days=90))
            .values("label")  # Use label instead of vulnerability_type
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        # Calculate risk score (0-100)
        total_issues = security_issues.count()
        critical_issues = security_issues.filter(cve_score__gte=8).count()  # Use cve_score instead of severity
        risk_score = min(100, (critical_issues / total_issues * 100) if total_issues > 0 else 0)

        return {
            "attack_vectors": [
                {
                    "vulnerability_type": self.get_label_name(vector["label"]),  # Convert label to readable name
                    "count": vector["count"],
                }
                for vector in attack_vectors
            ],
            "risk_score": int(risk_score),
            "recent_alerts": security_issues.filter(
                created__gte=timezone.now() - timedelta(days=7),
                cve_score__gte=7,  # Use cve_score for severity
            ).order_by("-created")[:5],
        }

    def get_label_name(self, label_id):
        """Convert label ID to human-readable name."""
        return self.labels.get(label_id, "Other")

    def get_general_info(self, organization):
        total_organization_bugs = Issue.objects.filter(domain__organization__id=organization).count()
        total_bug_hunts = Hunt.objects.filter(domain__organization__id=organization).count()
        total_domains = Domain.objects.filter(organization__id=organization).count()
        # Step 1: Retrieve all hunt IDs associated with the specified organization
        hunt_ids = Hunt.objects.filter(domain__organization__id=organization).values_list("id", flat=True)

        # Step 2: Sum the rewarded values from issues that have a hunt_id in the hunt_ids list
        total_money_distributed = Issue.objects.filter(hunt_id__in=hunt_ids).aggregate(total_money=Sum("rewarded"))[
            "total_money"
        ]
        total_money_distributed = 0 if total_money_distributed is None else total_money_distributed

        return {
            "total_organization_bugs": total_organization_bugs,
            "total_bug_hunts": total_bug_hunts,
            "total_domains": total_domains,
            "total_money_distributed": total_money_distributed,
        }

    def get_bug_report_type_piechart_data(self, organization):
        bug_report_type = (
            Issue.objects.values("label").filter(domain__organization__id=organization).annotate(count=Count("label"))
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

    def get_reports_on_domain_piechart_data(self, organization):
        report_piechart = (
            Issue.objects.values("url").filter(domain__organization__id=organization).annotate(count=Count("url"))
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

    def get_current_year_monthly_reported_bar_data(self, organization):
        # returns chart data on no of bugs reported monthly on this organization for current year

        current_year = timezone.now().year
        data_monthly = (
            Issue.objects.filter(domain__organization__id=organization, created__year=current_year)
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

    def bug_rate_increase_descrease_weekly(self, organization, is_accepted_bugs=False):
        # returns stats by comparing the count of past 8-15 days (1 week) activity to this (0 - 7) week.

        current_date = timezone.now().date()
        prev_week_start_date = current_date - timedelta(days=15)
        prev_week_end_date = current_date - timedelta(days=8)

        this_week_start_date = current_date - timedelta(days=7)
        this_week_end_date = current_date

        if is_accepted_bugs:
            prev_week_issue_count = Issue.objects.filter(
                domain__organization__id=organization,
                created__date__range=[prev_week_start_date, prev_week_end_date],
                verified=True,
            ).count()

            this_week_issue_count = Issue.objects.filter(
                domain__organization__id=organization,
                created__date__range=[this_week_start_date, this_week_end_date],
                verified=True,
            ).count()

        else:
            prev_week_issue_count = Issue.objects.filter(
                domain__organization__id=organization,
                created__date__range=[prev_week_start_date, prev_week_end_date],
            ).count()

            this_week_issue_count = Issue.objects.filter(
                domain__organization__id=organization,
                created__date__range=[this_week_start_date, this_week_end_date],
            ).count()

        if prev_week_issue_count == 0:
            percent_increase = this_week_issue_count * 100
        else:
            percent_increase = ((this_week_issue_count - prev_week_issue_count) / prev_week_issue_count) * 100

        return {
            "percent_increase": percent_increase,
            "is_increasing": (True if (this_week_issue_count - prev_week_issue_count) >= 0 else False),
            "this_week_issue_count": this_week_issue_count,
        }

    def get_spent_on_bugtypes(self, organization):
        spent_on_bugtypes = (
            Issue.objects.values("label").filter(domain__organization__id=organization).annotate(spent=Sum("rewarded"))
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

    @validate_organization_user
    def get(self, request, id, *args, **kwargs):
        # For authenticated users, show all organizations they have access to
        if request.user.is_authenticated:
            organizations = (
                Organization.objects.values("name", "id")
                .filter(Q(managers__in=[request.user]) | Q(admin=request.user))
                .distinct()
            )
        else:
            # For unauthenticated users, don't show organization list
            organizations = []

        # Get the organization object
        organization_obj = Organization.objects.filter(id=id).first()
        if not organization_obj:
            messages.error(request, "Organization does not exist")
            return redirect("home")

        context = {
            "organization": id,
            "organizations": organizations,
            "organization_obj": organization_obj,
            "total_info": self.get_general_info(id),
            "bug_report_type_piechart_data": self.get_bug_report_type_piechart_data(id),
            "reports_on_domain_piechart_data": self.get_reports_on_domain_piechart_data(id),
            "get_current_year_monthly_reported_bar_data": self.get_current_year_monthly_reported_bar_data(id),
            "bug_rate_increase_descrease_weekly": self.bug_rate_increase_descrease_weekly(id),
            "accepted_bug_rate_increase_descrease_weekly": self.bug_rate_increase_descrease_weekly(id, True),
            "spent_on_bugtypes": self.get_spent_on_bugtypes(id),
            "security_incidents_summary": self.get_security_incidents_summary(id),
        }
        context.update({"threat_intelligence": self.get_threat_intelligence(id)})
        return render(request, "organization/dashboard/organization_analytics.html", context=context)


class OrganizationDashboardIntegrations(View):
    @validate_organization_user
    def get(self, request, id, *args, **kwargs):
        # For authenticated users, show organizations they have access to
        if request.user.is_authenticated:
            organizations = (
                Organization.objects.values("name", "id")
                .filter(Q(managers__in=[request.user]) | Q(admin=request.user))
                .distinct()
            )
        else:
            # For unauthenticated users, don't show organization list
            organizations = []

        # Get the organization object
        organization_obj = Organization.objects.filter(id=id).first()
        if not organization_obj:
            messages.error(request, "Organization does not exist")
            return redirect("home")

        # Get slack integration if it exists
        slack_integration = SlackIntegration.objects.filter(
            integration__organization_id=id,
            integration__service_name=IntegrationServices.SLACK.value,
        ).first()

        context = {
            "organization": id,
            "organizations": organizations,
            "organization_obj": organization_obj,
            "slack_integration": slack_integration,
        }
        return render(request, "organization/dashboard/organization_integrations.html", context=context)


class OrganizationDashboardTeamOverviewView(View):
    @validate_organization_user
    def get(self, request, id, *args, **kwargs):
        # For authenticated users, show organizations they have access to
        if request.user.is_authenticated:
            organizations = (
                Organization.objects.values("name", "id")
                .filter(Q(managers__in=[request.user]) | Q(admin=request.user))
                .distinct()
            )
        else:
            # For unauthenticated users, don't show organization list
            organizations = []

        organization_obj = Organization.objects.filter(id=id).first()

        if not organization_obj:
            messages.error(request, "Organization does not exist")
            return redirect("home")

        # Get team members from organization's admin and managers
        team_member_users = []
        if organization_obj.admin:
            team_member_users.append(organization_obj.admin)

        # Add all managers
        managers = organization_obj.managers.all()
        team_member_users.extend(managers)

        # Remove duplicates while preserving order
        seen = set()
        unique_team_members = []
        for user in team_member_users:
            if user.id not in seen:
                seen.add(user.id)
                unique_team_members.append(user)

        team_member_users = unique_team_members

        # Get UserProfile objects for template rendering
        team_members = []
        for user in team_member_users:
            try:
                profile = user.userprofile
                # Create a wrapper object with expected attributes
                member_data = type(
                    "obj",
                    (object,),
                    {
                        "user": user,
                        "user_avatar": profile.user_avatar if hasattr(profile, "user_avatar") else None,
                        "role": "Admin" if user == organization_obj.admin else "Manager",
                    },
                )()
                team_members.append(member_data)
            except Exception:
                # If userprofile doesn't exist, create basic member data
                member_data = type(
                    "obj",
                    (object,),
                    {
                        "user": user,
                        "user_avatar": None,
                        "role": "Admin" if user == organization_obj.admin else "Manager",
                    },
                )()
                team_members.append(member_data)

        # Handle AJAX requests for filtered status reports
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            try:
                filter_type = request.GET.get("filter_type")
                filter_value = request.GET.get("filter_value")

                logger.info(
                    f"AJAX request for team overview: filter_type={filter_type}, filter_value={filter_value}, team_size={len(team_member_users)}"
                )

                reports = DailyStatusReport.objects.filter(user__in=team_member_users).order_by("-date")

                logger.info(f"Total reports before filter: {reports.count()}")

                if filter_type == "user" and filter_value:
                    reports = reports.filter(user_id=filter_value)
                elif filter_type == "date" and filter_value:
                    reports = reports.filter(date=filter_value)
                elif filter_type == "goal" and filter_value:
                    reports = reports.filter(goal_accomplished=filter_value == "true")
                elif filter_type == "task" and filter_value:
                    reports = reports.filter(previous_work__icontains=filter_value)

                logger.info(f"Reports after filter: {reports.count()}")

                data = []
                for report in reports:
                    try:
                        avatar_url = (
                            report.user.userprofile.user_avatar.url if report.user.userprofile.user_avatar else None
                        )
                    except Exception as e:
                        logger.warning(f"Error getting avatar for user {report.user.username}: {e}")
                        avatar_url = None

                    data.append(
                        {
                            "username": report.user.username,
                            "avatar_url": avatar_url,
                            "date": report.date.strftime("%B %d, %Y"),
                            "previous_work": report.previous_work,
                            "next_plan": report.next_plan,
                            "blockers": report.blockers,
                            "goal_accomplished": report.goal_accomplished,
                            "current_mood": report.current_mood,
                        }
                    )

                logger.info(f"Returning {len(data)} reports")
                return JsonResponse({"data": data})

            except Exception as e:
                logger.error(f"Error in team overview AJAX: {e}", exc_info=True)
                return JsonResponse({"error": "An error occurred while fetching reports", "data": []}, status=500)

        # Get daily status reports ordered by date (most recent first)
        daily_status_reports = DailyStatusReport.objects.filter(user__in=team_member_users).order_by("-date")

        logger.info(
            f"Team overview page load: org_id={id}, members={len(team_members)}, reports={daily_status_reports.count()}"
        )

        context = {
            "organization": id,
            "organizations": organizations,
            "organization_obj": organization_obj,
            "team_members": team_members,
            "daily_status_reports": daily_status_reports,
        }

        return render(request, "organization/dashboard/organization_team_overview.html", context=context)


class OrganizationDashboardManageBugsView(View):
    @validate_organization_user
    def get(self, request, id, *args, **kwargs):
        # For authenticated users, show all organizations they have access to
        if request.user.is_authenticated:
            organizations = (
                Organization.objects.values("name", "id")
                .filter(Q(managers__in=[request.user]) | Q(admin=request.user))
                .distinct()
            )
        else:
            # For unauthenticated users, don't show organization list
            organizations = []

        # Get the organization object
        organization_obj = Organization.objects.filter(id=id).first()
        if not organization_obj:
            messages.error(request, "Organization does not exist")
            return redirect("home")

        # Get all issues for this organization, ordered by creation date
        issues = Issue.objects.filter(domain__organization_id=id).order_by("-created")

        context = {
            "organization": id,
            "organizations": organizations,
            "organization_obj": organization_obj,
            "issues": issues,
        }
        return render(request, "organization/dashboard/organization_manage_bugs.html", context=context)


class OrganizationDashboardManageDomainsView(View):
    @validate_organization_user
    def get(self, request, id, *args, **kwargs):
        # Get domains for this organization
        organization = Organization.objects.filter(id=id).first()
        if not organization:
            raise Http404("Organization does not exist")

        # Get the filter parameter for security.txt
        security_txt_filter = request.GET.get("security_txt")

        # Base query for domains
        domains_query = Domain.objects.filter(organization=organization)

        # Apply filter if provided
        if security_txt_filter:
            if security_txt_filter == "yes":
                domains_query = domains_query.filter(has_security_txt=True)
            elif security_txt_filter == "no":
                domains_query = domains_query.filter(Q(has_security_txt=False) | Q(has_security_txt__isnull=True))

        # Get all domains for this organization
        domains = domains_query.values(
            "id", "name", "url", "logo", "is_active", "has_security_txt", "security_txt_checked_at"
        ).order_by("name")

        # If user has access to organizations
        if request.user.is_authenticated:
            organizations = (
                Organization.objects.values("name", "id")
                .filter(Q(managers__in=[request.user]) | Q(admin=request.user))
                .distinct()
            )
        else:
            organizations = []

        context = {
            "organization": id,
            "organization_object": organization,
            "domains": domains,
            "organizations": organizations,
            "security_txt_filter": security_txt_filter,
            "security_txt_yes_count": Domain.objects.filter(organization=organization, has_security_txt=True).count(),
            "security_txt_no_count": Domain.objects.filter(organization=organization)
            .filter(Q(has_security_txt=False) | Q(has_security_txt__isnull=True))
            .count(),
        }

        return render(request, "organization/dashboard/organization_manage_domains.html", context)


class AddDomainView(View):
    def dispatch(self, request, *args, **kwargs):
        method = self.request.POST.get("_method", "").lower()

        if method == "delete":
            return self.delete(request, *args, **kwargs)
        elif method == "put":
            logger.debug("=" * 100)
            return self.put(request, *args, **kwargs)

        return super().dispatch(request, *args, **kwargs)

    @validate_organization_user
    def get(self, request, id, *args, **kwargs):
        organizations = (
            Organization.objects.values("name", "id")
            .filter(Q(managers__in=[request.user]) | Q(admin=request.user))
            .distinct()
        )

        users = User.objects.filter(is_active=True)
        domain_id = kwargs.get("domain_id")
        domain = Domain.objects.filter(id=domain_id).first() if domain_id else None
        context = {
            "organization": id,
            "organization_obj": Organization.objects.filter(id=id).first(),
            "organizations": organizations,
            "users": users,
            "domain": domain,  # Pass the domain to the template if it exists
        }

        if domain:
            return render(request, "organization/dashboard/edit_domain.html", context=context)
        else:
            return render(request, "organization/dashboard/add_domain.html", context=context)

    @validate_organization_user
    @check_organization_or_manager
    def post(self, request, id, *args, **kwargs):
        domain_data = {
            "name": request.POST.get("domain_name", None),
            "url": request.POST.get("domain_url", None),
            "github": request.POST.get("github_url", None),
            "twitter": request.POST.get("twitter_url", None),
            "facebook": request.POST.get("facebook_url", None),
        }

        # Validate required fields first
        if not domain_data["name"]:
            messages.error(request, "Enter domain name")
            return redirect("add_domain", id=id)

        if not domain_data["url"]:
            messages.error(request, "Enter domain url")
            return redirect("add_domain", id=id)

        # Parse and validate URL
        try:
            parsed_url = urlparse(domain_data["url"])
            if not parsed_url.hostname:
                messages.error(request, "Invalid domain url")
                return redirect("add_domain", id=id)
            domain_data["url"] = parsed_url.netloc
        except Exception:
            messages.error(request, "Invalid domain url format")
            return redirect("add_domain", id=id)

        # Extract domain hostname and normalize to lowercase for consistency
        normalized_domain = parsed_url.hostname.replace("www.", "").lower()
        # Ensure the domain name is consistent with the URL processing
        # If user didn't provide a custom name, use the normalized domain
        if domain_data["name"].lower().replace("www.", "") == normalized_domain:
            domain_data["name"] = normalized_domain
        else:
            domain_data["name"] = domain_data["name"].strip()

        managers_list = request.POST.getlist("user")
        organization_obj = Organization.objects.get(id=id)

        domain_exist = Domain.objects.filter(Q(name=domain_data["name"]) | Q(url=domain_data["url"])).exists()

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
                except requests.exceptions.RequestException as e:
                    messages.error(request, "Domain does not exist.")
                    return redirect("add_domain", id=id)
        except ValueError:
            messages.error(request, "URL validation error.")
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
            if "twitter.com" not in domain_data["twitter"] and "x.com" not in domain_data["twitter"]:
                messages.error(request, "Twitter url should contain twitter.com or x.com")
                return redirect("add_domain", id=id)
        if domain_data["github"] and "github.com" not in domain_data["github"]:
            messages.error(request, "Github url should contain github.com")
            return redirect("add_domain", id=id)

        domain_managers = User.objects.filter(email__in=managers_list, is_active=True)

        domain = Domain.objects.create(
            **domain_data,
            organization=organization_obj,
            logo=logo_name,
            webshot=webshot_logo_name,
        )

        domain.managers.set(domain_managers)
        domain.save()

        return redirect("organization_manage_domains", id=id)

    @validate_organization_user
    @check_organization_or_manager
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
        # Normalize domain name to lowercase for consistent validation
        domain_name = (parsed_url.hostname).replace("www.", "").lower()

        domain_data["name"] = domain_data["name"].lower()

        managers_list = request.POST.getlist("user")
        organization_obj = Organization.objects.get(id=id)

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
            if "twitter.com" not in domain_data["twitter"] and "x.com" not in domain_data["twitter"]:
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
        domain.organization = organization_obj

        domain_managers = User.objects.filter(email__in=managers_list, is_active=True)
        domain.managers.set(domain_managers)
        domain.save()

        return redirect("organization_manage_domains", id=id)

    @validate_organization_user
    @check_organization_or_manager
    def delete(self, request, id, *args, **kwargs):
        domain_id = request.POST.get("domain_id", None)
        domain = get_object_or_404(Domain, id=domain_id)
        if domain is None:
            messages.error(request, "Domain not found.")
            return redirect("organization_manage_domains", id=id)
        domain.delete()
        messages.success(request, "Domain deleted successfully")
        return redirect("organization_manage_domains", id=id)


class AddSlackIntegrationView(View):
    @validate_organization_user
    def get(self, request, id, *args, **kwargs):
        slack_integration = (
            SlackIntegration.objects.filter(
                integration__organization_id=id,
                integration__service_name=IntegrationServices.SLACK.value,
            )
            .select_related("integration")
            .first()
        )

        if slack_integration:
            bot_token = slack_integration.bot_access_token
            app = App(token=bot_token)
            channels_list = self.get_channel_names(app)

            hours = range(24)
            return render(
                request,
                "organization/dashboard/add_slack_integration.html",
                context={
                    "organization": id,
                    "slack_integration": slack_integration,
                    "channels": channels_list,
                    "hours": hours,
                    "welcome_message": slack_integration.welcome_message,
                },
            )

        # Redirect to Slack OAuth flow if no integration exists
        client_id = os.getenv("SLACK_ID_CLIENT")
        scopes = "channels:read,chat:write,groups:read,channels:join,im:write,users:read,team:read,commands"
        host = request.get_host()
        scheme = request.META.get("HTTP_X_FORWARDED_PROTO", request.scheme)
        redirect_uri = f"{scheme}://{host}/oauth/slack/callback"
        allowed_redirect_uris = [
            f"{scheme}://{host}/oauth/slack/callback",
        ]

        if redirect_uri not in allowed_redirect_uris:
            raise ValueError("Invalid redirect URI")

        state = urlencode({"organization_id": id})

        auth_url = (
            f"https://slack.com/oauth/v2/authorize"
            f"?client_id={client_id}&scope={scopes}"
            f"&state={state}&redirect_uri={redirect_uri}"
        )

        return redirect(auth_url)

    def get_channel_names(self, app):
        """Fetches channel names from Slack."""
        cursor = None
        channels = []
        try:
            while True:
                response = app.client.conversations_list(cursor=cursor)
                if response["ok"]:
                    channels.extend(channel["name"] for channel in response["channels"])
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
        except Exception as e:
            logger.error(f"Error fetching channels: {e}")
        return channels

    @validate_organization_user
    def post(self, request, id, *args, **kwargs):
        if request.POST.get("_method") == "delete":
            return self.delete(request, id, *args, **kwargs)

        slack_data = {
            "default_channel": request.POST.get("target_channel"),
            "daily_sizzle_timelogs_status": request.POST.get("daily_sizzle_timelogs_status"),
            "daily_sizzle_timelogs_hour": request.POST.get("daily_sizzle_timelogs_hour"),
            "welcome_message": request.POST.get("welcome_message"),  # Add this
        }
        slack_integration = (
            SlackIntegration.objects.filter(
                integration__organization_id=id,
                integration__service_name=IntegrationServices.SLACK.value,
            )
            .select_related("integration")
            .first()
        )

        if slack_integration:
            app = App(token=slack_integration.bot_access_token)
            if slack_data["default_channel"]:
                slack_integration.default_channel_id = self.get_channel_id(app, slack_data["default_channel"])
                slack_integration.default_channel_name = slack_data["default_channel"]
            slack_integration.daily_updates = bool(slack_data["daily_sizzle_timelogs_status"])
            slack_integration.daily_update_time = slack_data["daily_sizzle_timelogs_hour"]
            # Add welcome message
            slack_integration.welcome_message = slack_data["welcome_message"]
            slack_integration.save()

        return redirect("organization_manage_integrations", id=id)

    def get_channel_id(self, app, channel_name):
        """Fetches a Slack channel ID by name."""
        cursor = None
        try:
            while True:
                response = app.client.conversations_list(cursor=cursor)
                for channel in response["channels"]:
                    if channel["name"] == channel_name.strip("#"):
                        return channel["id"]
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
        except Exception as e:
            logger.error(f"Error fetching channel ID: {e}")
        return None

    @validate_organization_user
    def delete(self, request, id, *args, **kwargs):
        """Deletes the Slack integration."""
        slack_integration = (
            SlackIntegration.objects.filter(
                integration__organization_id=id,
                integration__service_name=IntegrationServices.SLACK.value,
            )
            .select_related("integration")
            .first()
        )

        if slack_integration:
            slack_integration.delete()

        return redirect("organization_manage_integrations", id=id)


class SlackCallbackView(View):
    def get(self, request, *args, **kwargs):
        try:
            # Extract parameters
            code = request.GET.get("code")
            state = request.GET.get("state")

            if not code:
                logger.error("Missing 'code' parameter in OAuth callback.")
                return HttpResponseBadRequest("Missing 'code' parameter")

            if not state:
                logger.error("Missing 'state' parameter in OAuth callback.")
                return HttpResponseBadRequest("Missing 'state' parameter")

            # Safely parse state
            state_data = parse_qs(state)
            organization_id = state_data.get("organization_id", [None])[0]

            if not organization_id or not organization_id.isdigit():
                logger.error(f"Invalid organization_id received: {organization_id}")
                return HttpResponseBadRequest("Invalid organization ID")

            organization_id = int(organization_id)  # Convert to integer after validation

            # Exchange code for access token
            token_data = self.exchange_code_for_token(code, request)

            if not token_data or "access_token" not in token_data or "team" not in token_data:
                logger.error(f"Invalid token data received from Slack: {token_data}")
                return HttpResponseServerError("Failed to retrieve token from Slack")

            # Store integration data in the database
            integration = Integration.objects.create(
                organization_id=organization_id,
                service_name=IntegrationServices.SLACK.value,
            )
            SlackIntegration.objects.create(
                integration=integration,
                bot_access_token=token_data["access_token"],
                workspace_name=token_data["team"]["id"],
            )

            # Redirect to the organization's integration dashboard
            dashboard_url = reverse("organization_manage_integrations", args=[organization_id])
            return redirect(dashboard_url)

        except Exception as e:
            logger.exception(f"Error during Slack OAuth callback: {e}")
            return HttpResponseServerError("An unexpected error occurred during Slack OAuth.")

    def exchange_code_for_token(self, code, request):
        """Exchanges OAuth code for Slack access token."""
        client_id = os.getenv("SLACK_ID_CLIENT")
        client_secret = os.getenv("SLACK_SECRET_CLIENT")
        host = request.get_host()
        scheme = request.META.get("HTTP_X_FORWARDED_PROTO", request.scheme)
        redirect_uri = os.environ.get(
            "OAUTH_REDIRECT_URL",
            f"{request.scheme}://{request.get_host()}/oauth/slack/callback",
        )

        url = "https://slack.com/api/oauth.v2.access"
        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
        }

        response = requests.post(url, data=data)
        token_data = response.json()

        if token_data.get("ok"):
            return token_data  # Return the full token data instead of just the access token
        else:
            raise Exception(f"Error exchanging code for token: {token_data.get('error')}")


class DomainView(View):
    def get_current_year_monthly_reported_bar_data(self, domain_id):
        # returns chart data on no of bugs reported monthly on this organization for current year

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
                "organization__name",
                "created",
                "modified",
                "twitter",
                "facebook",
                "github",
                "logo",
                "webshot",
                "has_security_txt",
                "security_txt_checked_at",
            )
            .filter(id=pk)
            .first()
        )

        if not domain:
            raise Http404("Domain not found")

        total_money_distributed = Issue.objects.filter(domain__id=domain["id"]).aggregate(total_money=Sum("rewarded"))[
            "total_money"
        ]
        total_money_distributed = 0 if total_money_distributed is None else total_money_distributed

        # Query the database for the exact domain
        total_bug_reported = Issue.objects.filter(domain__id=domain["id"]).count()
        total_bug_accepted = Issue.objects.filter(domain__id=domain["id"], verified=True).count()

        is_domain_manager = Domain.objects.filter(Q(id=domain["id"]) & Q(managers__in=[request.user])).exists()
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

        ongoing_bughunts = Hunt.objects.filter(domain__id=domain["id"]).annotate(total_prize=Sum("huntprize__value"))[
            :3
        ]
        context = {
            **domain,
            "total_money_distributed": total_money_distributed,
            "total_bug_reported": total_bug_reported,
            "total_bug_accepted": total_bug_accepted,
            "latest_issues": cleaned_issues,
            "monthly_activity_chart": json.dumps(self.get_current_year_monthly_reported_bar_data(domain["id"])),
            "top_testers": top_testers,
            "first_bug": first_bug,
            "last_bug": last_bug,
            "ongoing_bughunts": ongoing_bughunts,
        }

        return render(request, "organization/dashboard/view_domain.html", context)


class OrganizationDashboardManageRolesView(View):
    @validate_organization_user
    def get(self, request, id, *args, **kwargs):
        # Get the organization object
        organization_obj = Organization.objects.filter(id=id).first()
        if not organization_obj:
            messages.error(request, "Organization does not exist")
            return redirect("home")

        # Check if user is admin or manager of this organization
        is_org_admin = organization_obj.admin == request.user
        is_org_manager = organization_obj.managers.filter(id=request.user.id).exists()

        if not (is_org_admin or is_org_manager):
            messages.error(request, "You don't have permission to manage roles for this organization")
            return redirect("organization_dashboard_overview", id=id)

        # Get user's own role to determine permissions
        try:
            current_user_role = OrganizationAdmin.objects.get(
                user=request.user, organization=organization_obj, is_active=True
            )
            user_role_level = current_user_role.role  # 0=Admin, 1=Moderator
        except OrganizationAdmin.DoesNotExist:
            # Organization owner has full access
            if is_org_admin:
                user_role_level = 0
            else:
                messages.error(request, "You don't have an active role in this organization")
                return redirect("organization_dashboard_overview", id=id)

        # Only admins (role=0) or org owner can manage roles
        if user_role_level != 0 and not is_org_admin:
            messages.error(request, "Only administrators can manage roles")
            return redirect("organization_dashboard_overview", id=id)

        # Get all active roles in the organization
        org_roles = (
            OrganizationAdmin.objects.filter(organization=organization_obj, is_active=True)
            .select_related("user", "user__userprofile", "domain")
            .order_by("role", "created")
        )

        # Get organization domains for assignment
        domains = Domain.objects.filter(organization=organization_obj).order_by("name")

        # Get users from organization email domain for quick add
        organization_url = organization_obj.url
        # Handle both with and without scheme
        if "://" not in organization_url:
            organization_url = f"https://{organization_url}"
        parsed_url = urlparse(organization_url)
        organization_domain = parsed_url.netloc.replace("www.", "").strip()

        # Try to get users matching organization email domain
        if organization_domain:
            available_users = (
                User.objects.filter(email__endswith=f"@{organization_domain}", is_active=True)
                .exclude(id__in=org_roles.values_list("user_id", flat=True))
                .values("id", "username", "email", "first_name", "last_name")[:100]
            )

            # If no users found with matching email domain, show all active users
            if not available_users.exists():
                available_users = (
                    User.objects.filter(is_active=True)
                    .exclude(id__in=org_roles.values_list("user_id", flat=True))
                    .values("id", "username", "email", "first_name", "last_name")[:100]
                )
        else:
            # If no valid domain, show all active users
            available_users = (
                User.objects.filter(is_active=True)
                .exclude(id__in=org_roles.values_list("user_id", flat=True))
                .values("id", "username", "email", "first_name", "last_name")[:100]
            )

        # Format roles data for template
        roles_data = []
        admin_count = 0
        moderator_count = 0

        for org_role in org_roles:
            role_info = {
                "id": org_role.id,
                "user": org_role.user,
                "user_id": org_role.user.id if org_role.user else None,
                "username": org_role.user.username if org_role.user else "Unknown",
                "email": org_role.user.email if org_role.user else "",
                "avatar": org_role.user.userprofile.user_avatar
                if org_role.user and hasattr(org_role.user, "userprofile")
                else None,
                "role": org_role.role,
                "role_display": "Administrator" if org_role.role == 0 else "Moderator",
                "domain": org_role.domain,
                "domain_name": org_role.domain.name if org_role.domain else None,
                "created": org_role.created,
                "is_active": org_role.is_active,
                "is_owner": organization_obj.admin == org_role.user,
            }
            roles_data.append(role_info)

            if org_role.role == 0:
                admin_count += 1
            else:
                moderator_count += 1

        context = {
            "organization": id,
            "organization_obj": organization_obj,
            "roles": roles_data,
            "domains": list(domains.values("id", "name")),
            "available_users": list(available_users),
            "is_org_admin": is_org_admin,
            "user_role_level": user_role_level,
            "admin_count": admin_count,
            "moderator_count": moderator_count,
            "role_choices": [{"value": 0, "label": "Administrator"}, {"value": 1, "label": "Moderator"}],
        }

        return render(request, "organization/dashboard/organization_manage_roles.html", context)

    def post(self, request, id, *args, **kwargs):
        # Get the organization
        organization_obj = Organization.objects.filter(id=id).first()
        if not organization_obj:
            messages.error(request, "Organization does not exist")
            return redirect("home")

        # Check permissions
        is_org_admin = organization_obj.admin == request.user
        try:
            current_user_role = OrganizationAdmin.objects.get(
                user=request.user, organization=organization_obj, is_active=True
            )
            user_role_level = current_user_role.role
        except OrganizationAdmin.DoesNotExist:
            if not is_org_admin:
                messages.error(request, "You don't have permission to manage roles")
                return redirect("organization_manage_roles", id=id)
            user_role_level = 0

        # Only admins can manage roles
        if user_role_level != 0 and not is_org_admin:
            messages.error(request, "Only administrators can manage roles")
            return redirect("organization_manage_roles", id=id)

        action = request.POST.get("action")

        if action == "add_role":
            user_id = request.POST.get("user_id")
            email = request.POST.get("email")
            role = request.POST.get("role", 1)  # Default to Moderator
            domain_id = request.POST.get("domain_id")

            try:
                # Find user by ID or email
                if user_id:
                    user = User.objects.get(id=user_id, is_active=True)
                elif email:
                    user = User.objects.get(email=email, is_active=True)
                else:
                    messages.error(request, "Please provide a user ID or email")
                    return redirect("organization_manage_roles", id=id)

                # Check if user already has an active role
                existing_role = OrganizationAdmin.objects.filter(
                    user=user, organization=organization_obj, is_active=True
                ).first()

                if existing_role:
                    messages.error(request, f"{user.username} already has an active role in this organization")
                    return redirect("organization_manage_roles", id=id)

                # Check if user is trying to assign themselves
                if user == request.user:
                    messages.error(request, "You cannot modify your own role")
                    return redirect("organization_manage_roles", id=id)

                # Get domain if specified
                domain = None
                if domain_id:
                    domain = Domain.objects.filter(id=domain_id, organization=organization_obj).first()

                # Create the role
                OrganizationAdmin.objects.create(
                    user=user, organization=organization_obj, domain=domain, role=int(role), is_active=True
                )

                role_name = "Administrator" if int(role) == 0 else "Moderator"
                messages.success(request, f"Successfully assigned {role_name} role to {user.username}")

            except User.DoesNotExist:
                messages.error(request, "User not found or inactive")
            except (ValidationError, IntegrityError) as e:
                logger.exception(f"Error adding role: {e!s}")
                messages.error(request, "An error occurred while adding the role. Please try again.")

        elif action == "update_role":
            role_id = request.POST.get("role_id")
            new_role = request.POST.get("role")
            domain_id = request.POST.get("domain_id")

            try:
                org_role = OrganizationAdmin.objects.get(id=role_id, organization=organization_obj, is_active=True)

                # Prevent modifying own role
                if org_role.user == request.user:
                    messages.error(request, "You cannot modify your own role")
                    return redirect("organization_manage_roles", id=id)

                # Prevent modifying organization owner's role
                if org_role.user == organization_obj.admin:
                    messages.error(request, "Cannot modify the organization owner's role")
                    return redirect("organization_manage_roles", id=id)

                # Update role
                if new_role is not None:
                    org_role.role = int(new_role)

                # Update domain assignment
                if domain_id:
                    domain = Domain.objects.filter(id=domain_id, organization=organization_obj).first()
                    org_role.domain = domain
                elif domain_id == "":
                    org_role.domain = None

                org_role.save()
                messages.success(request, f"Successfully updated role for {org_role.user.username}")

            except OrganizationAdmin.DoesNotExist:
                messages.error(request, "Role not found")
            except ValueError as e:
                logger.error(f"Invalid value provided when updating role: {str(e)}")
                messages.error(request, str(e))
            except ValidationError as e:
                logger.error(f"Validation error when updating role: {str(e)}")
                messages.error(request, str(e))
            except IntegrityError as e:
                logger.error(f"Database integrity error when updating role: {str(e)}")
                messages.error(request, "Database integrity error: Unable to update role due to conflicting data")
            except Exception as e:
                logger.exception("Error updating role")
                messages.error(request, "An error occurred while updating the role. " + str(e))

        elif action == "remove_role":
            role_id = request.POST.get("role_id")

            try:
                org_role = OrganizationAdmin.objects.get(id=role_id, organization=organization_obj)

                # Prevent removing own role
                if org_role.user == request.user:
                    messages.error(request, "You cannot remove your own role")
                    return redirect("organization_manage_roles", id=id)

                # Prevent removing organization owner's role
                if org_role.user == organization_obj.admin:
                    messages.error(request, "Cannot remove the organization owner's role")
                    return redirect("organization_manage_roles", id=id)

                # Deactivate the role instead of deleting
                org_role.is_active = False
                org_role.save()

                messages.success(request, f"Successfully removed role from {org_role.user.username}")

            except OrganizationAdmin.DoesNotExist:
                messages.error(request, "Role not found")
            except (ValidationError, ValueError) as e:
                logger.exception(f"Error removing role: {e!s}")
                messages.error(request, "An error occurred while removing the role. Please try again.")

        return redirect("organization_manage_roles", id=id)


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

        # Get the organization associated with the domain of the hunt
        organization = hunt_obj.domain.organization

        # Check if the user is either a manager of the domain or the admin of the organization
        is_hunt_manager = hunt_obj.domain.managers.filter(id=request.user.id).exists() or (
            organization and organization.admin == request.user
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
        winners_count = {reward.id: Winner.objects.filter(prize_id=reward.id).count() for reward in rewards}

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

        return render(request, "organization/bughunt/view_bughunt.html", context)


class EndBughuntView(View):
    def get(self, request, pk, *args, **kwargs):
        hunt = get_object_or_404(Hunt, pk=pk)

        # Get the organization associated with the domain of the hunt
        organization = hunt.domain.organization

        # Check if the user is either a manager of the domain or the admin of the organization
        is_hunt_manager = hunt.domain.managers.filter(id=request.user.id).exists() or (
            organization and organization.admin == request.user
        )

        if not is_hunt_manager:
            return Http404("User not allowed")

        hunt.result_published = True
        hunt.save()
        organization = hunt.domain.organization.id

        messages.success(request, f"successfully Ended Bughunt {hunt.name}")
        return redirect("organization_manage_bughunts", id=organization)


class AddHuntView(View):
    def edit(self, request, id, organizations, domains, hunt_id, *args, **kwargs):
        hunt = get_object_or_404(Hunt, pk=hunt_id)
        prizes = HuntPrize.objects.values().filter(hunt__id=hunt_id)

        context = {
            "organization": id,
            "organization_obj": Organization.objects.filter(id=id).first(),
            "organizations": organizations,
            "domains": domains,
            "hunt": hunt,
            "prizes": prizes,
            "markdown_value": hunt.description,
        }

        return render(request, "organization/bughunt/edit_bughunt.html", context)

    @validate_organization_user
    def get(self, request, id, *args, **kwargs):
        hunt_id = request.GET.get("hunt", None)

        organizations = (
            Organization.objects.values("name", "id")
            .filter(Q(managers__in=[request.user]) | Q(admin=request.user))
            .distinct()
        )

        domains = Domain.objects.values("id", "name").filter(organization__id=id)

        if hunt_id is not None:
            return self.edit(request, id, organizations, domains, hunt_id, *args, **kwargs)

        context = {
            "organization": id,
            "organization_obj": Organization.objects.filter(id=id).first(),
            "organizations": organizations,
            "domains": domains,
        }

        return render(request, "organization/bughunt/add_bughunt.html", context)

    @validate_organization_user
    @check_organization_or_manager
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

        # Expect dates in MM/DD/YYYY format from the form
        start_date = data.get("start_date", datetime.now().strftime("%m/%d/%Y"))
        end_date = data.get("end_date", datetime.now().strftime("%m/%d/%Y"))

        try:
            # Parse MM/DD/YYYY format and convert to database format
            start_date = datetime.strptime(start_date, "%m/%d/%Y").strftime("%Y-%m-%d %H:%M")
            end_date = datetime.strptime(end_date, "%m/%d/%Y").strftime("%Y-%m-%d %H:%M")
        except ValueError:
            messages.error(request, "Please enter dates in MM/DD/YYYY format (e.g., 12/25/2024)")
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
        return redirect("organization_manage_bughunts", id)


class OrganizationDashboardManageBughuntView(View):
    @validate_organization_user
    def get(self, request, id, *args, **kwargs):
        # For authenticated users, show all organizations they have access to
        if request.user.is_authenticated:
            organizations = (
                Organization.objects.values("name", "id")
                .filter(Q(managers__in=[request.user]) | Q(admin=request.user))
                .distinct()
            )
        else:
            # For unauthenticated users, don't show organization list
            organizations = []

        # Get the organization object
        organization_obj = Organization.objects.filter(id=id).first()
        if not organization_obj:
            messages.error(request, "Organization does not exist")
            return redirect("home")

        query = (
            Hunt.objects.values(
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
                "url",
                "logo",
            )
            .annotate(total_prize=Sum("huntprize__value"))
            .filter(domain__organization__id=id)
        )
        filtered_bughunts = {
            "all": query,
            "ongoing": query.filter(result_published=False, is_published=True),
            "ended": query.filter(result_published=True),
            "draft": query.filter(result_published=False, is_published=False),
        }

        filter_type = request.GET.get("filter", "all")

        context = {
            "organization": id,
            "organization_obj": organization_obj,
            "organizations": organizations,
            "bughunts": filtered_bughunts.get(filter_type, []),
        }

        return render(request, "organization/bughunt/organization_manage_bughunts.html", context)


@require_http_methods(["DELETE"])
def delete_prize(request, prize_id, organization_id):
    if not request.user.organization_set.filter(id=organization_id).exists():
        return JsonResponse({"success": False, "error": "User not allowed"})
    try:
        prize = HuntPrize.objects.get(id=prize_id)
        prize.delete()
        return JsonResponse({"success": True})
    except HuntPrize.DoesNotExist:
        return JsonResponse({"success": False, "error": "Prize not found"})


@require_http_methods(["PUT"])
def edit_prize(request, prize_id, organization_id):
    if not request.user.organization_set.filter(id=organization_id).exists():
        return JsonResponse({"success": False, "error": "User not allowed"})

    try:
        prize = HuntPrize.objects.get(id=prize_id)
    except HuntPrize.DoesNotExist:
        return JsonResponse({"success": False, "error": "Prize not found"})

    data = json.loads(request.body)
    prize.name = data.get("prize_name", prize.name)
    prize.value = data.get("cash_value", prize.value)
    prize.no_of_eligible_projects = data.get("number_of_winning_projects", prize.no_of_eligible_projects)
    prize.valid_submissions_eligible = data.get("every_valid_submissions", prize.valid_submissions_eligible)
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
                hunt_id=issue.hunt.id,
                prize_id=None,
                winner_id=issue.user.id,
                prize_amount=0,
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
        if not (request.user == domain.organization.admin):
            # return error with not permission msg
            return JsonResponse(
                {
                    "success": False,
                    "message": "You do not have permission to delete this manager.",
                },
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


@login_required
@require_http_methods(["POST"])
def check_domain_security_txt(request):
    domain_id = request.POST.get("domain_id")
    if not domain_id:
        messages.error(request, "Domain ID is required")
        return redirect("organization_manage_domains", id=request.user.userprofile.team.id)

    domain = get_object_or_404(Domain, id=domain_id)

    # Check if the user has permission to manage this domain
    has_permission = False
    if request.user.is_superuser:
        has_permission = True
    elif domain.organization and (
        domain.organization.admin == request.user or domain.organization.managers.filter(id=request.user.id).exists()
    ):
        has_permission = True
    elif domain.managers.filter(id=request.user.id).exists():
        has_permission = True

    if not has_permission:
        messages.error(request, "You don't have permission to check this domain")
        return redirect("organization_manage_domains", id=request.user.userprofile.team.id)

    try:
        # Check for security.txt
        has_security_txt = check_security_txt(domain.url)

        # Update domain with status
        domain.has_security_txt = has_security_txt
        domain.security_txt_checked_at = timezone.now()
        domain.save(update_fields=["has_security_txt", "security_txt_checked_at"])

        if has_security_txt:
            messages.success(request, f"Security.txt found for {domain.name}")
        else:
            messages.info(request, f"No security.txt found for {domain.name}")

    except Exception as e:
        messages.error(request, f"Error checking security.txt: {str(e)}")

    # Redirect back to the manage domains page
    if domain.organization:
        return redirect("organization_manage_domains", id=domain.organization.id)
    else:
        return redirect("organization_manage_domains", id=request.user.userprofile.team.id)


# Job Board Views


class OrganizationDashboardManageJobsView(View):
    """View for managing organization job postings"""

    @validate_organization_user
    def get(self, request, id, *args, **kwargs):
        from website.models import Job

        # For authenticated users, show organizations they have access to
        if request.user.is_authenticated:
            organizations = (
                Organization.objects.values("name", "id")
                .filter(Q(managers__in=[request.user]) | Q(admin=request.user))
                .distinct()
            )
        else:
            organizations = []

        # Get the organization object
        organization_obj = Organization.objects.filter(id=id).first()
        if not organization_obj:
            messages.error(request, "Organization does not exist")
            return redirect("home")

        # Get all jobs for this organization
        jobs = Job.objects.filter(organization=organization_obj).order_by("-created_at")

        # Apply search and filters
        search_query = request.GET.get("q", "")
        status_filter = request.GET.get("status", "")
        job_type_filter = request.GET.get("type", "")
        visibility_filter = request.GET.get("visibility", "")

        if search_query:
            jobs = jobs.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query))

        if status_filter:
            jobs = jobs.filter(status=status_filter)

        if job_type_filter:
            jobs = jobs.filter(job_type=job_type_filter)

        if visibility_filter:
            if visibility_filter == "public":
                jobs = jobs.filter(is_public=True)
            elif visibility_filter == "private":
                jobs = jobs.filter(is_public=False)

        # Get statistics (from all jobs, not filtered)
        all_jobs = Job.objects.filter(organization=organization_obj)
        total_jobs = all_jobs.count()
        active_jobs = all_jobs.filter(status="active").count()
        draft_jobs = all_jobs.filter(status="draft").count()
        public_jobs = all_jobs.filter(is_public=True).count()
        total_views = all_jobs.aggregate(total=Sum("views_count"))["total"] or 0

        context = {
            "organization": id,
            "organizations": organizations,
            "organization_obj": organization_obj,
            "jobs": jobs,
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "draft_jobs": draft_jobs,
            "public_jobs": public_jobs,
            "total_views": total_views,
            "search_query": search_query,
            "status_filter": status_filter,
            "job_type_filter": job_type_filter,
            "visibility_filter": visibility_filter,
        }

        return render(request, "organization/dashboard/organization_manage_jobs.html", context)


@login_required
def create_job(request, id):
    """Create a new job posting for the organization"""
    from website.forms import JobForm

    # Get organization and verify access
    organization = get_object_or_404(Organization, id=id)

    # Check if user is admin or manager
    is_member = organization.admin == request.user or organization.managers.filter(id=request.user.id).exists()

    if not is_member:
        messages.error(request, "You do not have permission to create jobs for this organization.")
        return redirect("home")

    if request.method == "POST":
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.organization = organization
            job.posted_by = request.user
            job.save()
            messages.success(request, f"Job '{job.title}' has been created successfully!")
            return redirect("organization_manage_jobs", id=id)
    else:
        form = JobForm()

    # Get organizations for sidebar
    if request.user.is_authenticated:
        organizations = (
            Organization.objects.values("name", "id")
            .filter(Q(managers__in=[request.user]) | Q(admin=request.user))
            .distinct()
        )
    else:
        organizations = []

    context = {
        "form": form,
        "organization": id,
        "organization_obj": organization,
        "organizations": organizations,
    }

    return render(request, "organization/dashboard/create_job.html", context)


@login_required
def edit_job(request, id, job_id):
    """Edit an existing job posting"""
    from website.forms import JobForm
    from website.models import Job

    # Get organization and job
    organization = get_object_or_404(Organization, id=id)
    job = get_object_or_404(Job, id=job_id, organization=organization)

    # Check permissions
    is_member = organization.admin == request.user or organization.managers.filter(id=request.user.id).exists()

    if not is_member:
        messages.error(request, "You do not have permission to edit this job.")
        return redirect("home")

    if request.method == "POST":
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, f"Job '{job.title}' has been updated successfully!")
            return redirect("organization_manage_jobs", id=id)
    else:
        form = JobForm(instance=job)

    # Get organizations for sidebar
    if request.user.is_authenticated:
        organizations = (
            Organization.objects.values("name", "id")
            .filter(Q(managers__in=[request.user]) | Q(admin=request.user))
            .distinct()
        )
    else:
        organizations = []

    context = {
        "form": form,
        "job": job,
        "organization": id,
        "organization_obj": organization,
        "organizations": organizations,
        "is_edit": True,
    }

    return render(request, "organization/dashboard/create_job.html", context)


@login_required
@require_http_methods(["POST"])
def delete_job(request, id, job_id):
    """Delete a job posting"""
    from website.models import Job

    organization = get_object_or_404(Organization, id=id)
    job = get_object_or_404(Job, id=job_id, organization=organization)

    # Check permissions
    is_member = organization.admin == request.user or organization.managers.filter(id=request.user.id).exists()

    if not is_member:
        messages.error(request, "You do not have permission to delete this job.")
        return redirect("home")

    job_title = job.title
    job.delete()
    messages.success(request, f"Job '{job_title}' has been deleted successfully!")

    return redirect("organization_manage_jobs", id=id)


@login_required
@require_http_methods(["POST"])
def toggle_job_status(request, id, job_id):
    """Toggle job status between active and paused"""
    from website.models import Job

    organization = get_object_or_404(Organization, id=id)
    job = get_object_or_404(Job, id=job_id, organization=organization)

    # Check permissions
    is_member = organization.admin == request.user or organization.managers.filter(id=request.user.id).exists()

    if not is_member:
        return JsonResponse({"success": False, "message": "Permission denied"})

    # Toggle between active and paused
    if job.status == "active":
        job.status = "paused"
    elif job.status == "paused":
        job.status = "active"

    job.save(update_fields=["status"])

    return JsonResponse({"success": True, "status": job.status})


def public_job_list(request):
    """Public view showing all active public jobs"""
    from django.utils import timezone

    from website.models import Job

    # Get all public and active jobs that haven't expired
    jobs = (
        Job.objects.filter(is_public=True, status="active")
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
        .select_related("organization")
        .order_by("-created_at")
    )

    # Search functionality
    search_query = request.GET.get("q", "")
    if search_query:
        jobs = jobs.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(location__icontains=search_query)
            | Q(organization__name__icontains=search_query)
        )

    # Filter by job type
    job_type = request.GET.get("type", "")
    if job_type:
        jobs = jobs.filter(job_type=job_type)

    # Filter by location
    location = request.GET.get("location", "")
    if location:
        jobs = jobs.filter(location__icontains=location)

    context = {
        "jobs": jobs,
        "search_query": search_query,
        "job_type_filter": job_type,
        "location_filter": location,
    }

    return render(request, "jobs/public_job_list.html", context)


def job_detail(request, pk):
    """Public view for a single job posting; org members can see all their jobs"""
    from django.http import Http404

    from website.models import Job

    job = get_object_or_404(Job, pk=pk)

    # Check if user is org member (admin or manager)
    is_org_member = False
    if request.user.is_authenticated:
        is_org_member = (
            job.organization.admin == request.user or job.organization.managers.filter(id=request.user.id).exists()
        )

    # Public users can only see active, public, non-expired jobs
    if not is_org_member:
        from django.utils import timezone

        is_expired = job.expires_at and job.expires_at < timezone.now()
        if not job.is_public or job.status != "active" or is_expired:
            raise Http404("Job not found")

    # Increment view count
    job.increment_views()

    context = {
        "job": job,
    }

    return render(request, "jobs/job_detail.html", context)
