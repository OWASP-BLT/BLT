import json

from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods

from website.models import Company, Domain, HuntPrize, Issue, Winner

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
    
    