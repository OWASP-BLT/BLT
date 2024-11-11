import json
import uuid
from datetime import datetime

from django.contrib import messages
from django.core.files.storage import default_storage
from django.http import Http404
from django.db.models import Count, OuterRef, Q, Subquery, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View

from website.models import Company, Domain, Hunt, HuntPrize, Issue, IssueScreenshot, Winner
from .helper import validate_company_user, check_company_or_manager


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