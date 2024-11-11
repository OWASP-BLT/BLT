import json
import uuid
from urllib.parse import urlparse

import requests
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.db.models import Count, OuterRef, Q, Subquery, Sum
from django.db.models.functions import ExtractMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404
from django.utils import timezone
from django.views.generic import View

from website.models import Company, Domain, Hunt, Issue, IssueScreenshot
from website.utils import is_valid_https_url, rebuild_safe_url
from .helper import validate_company_user, check_company_or_manager



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
