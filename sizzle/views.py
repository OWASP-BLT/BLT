from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now
from django.views.generic import ListView

from .models import DailyStatusReport


class SizzleListView(ListView):
    model = DailyStatusReport
    template_name = "sizzle/sizzle.html"
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["leaderboard"] = []
        context["sizzle_data"] = None
        context["user_reports"] = DailyStatusReport.objects.none()

        if self.request.user.is_authenticated:
            reports = DailyStatusReport.objects.filter(user=self.request.user).order_by("-date")
            context["sizzle_data"] = reports.first()
            context["user_reports"] = reports
        return context


def user_sizzle_report_view(request, username):
    user = get_object_or_404(User, username=username)
    reports = DailyStatusReport.objects.filter(user=user).order_by("-date")
    return render(request, "sizzle/sizzle_daily_status.html", {"username": username, "reports": reports})


@login_required
def checkin(request):
    return render(request, "sizzle/checkin.html")


@login_required
def add_sizzle_checkin(request):
    if request.method == "POST":
        previous_work = request.POST.get("previous_work")
        next_plan = request.POST.get("next_plan")
        blockers = request.POST.get("blockers")
        feeling = request.POST.get("feeling")
        goal_accomplished = request.POST.get("goal_accomplished") == "on"

        DailyStatusReport.objects.update_or_create(
            user=request.user,
            date=now().date(),
            defaults={
                "previous_work": previous_work,
                "next_plan": next_plan,
                "blockers": blockers,
                "current_mood": feeling if feeling else "Happy 😊",
                "goal_accomplished": goal_accomplished,
            },
        )
        return redirect("sizzle:index")

    user_reports = DailyStatusReport.objects.filter(user=request.user)
    yesterday = now().date() - timedelta(days=1)

    yesterday_report = user_reports.filter(date=yesterday).first()
    all_checkins = user_reports.order_by("-date")[:10]
    last_checkin = all_checkins[0] if all_checkins else None

    return render(
        request,
        "sizzle/add_sizzle_checkin.html",
        {
            "yesterday_report": yesterday_report,
            "last_checkin": last_checkin,
            "all_checkins": all_checkins,
        },
    )


@login_required
def checkin_detail(request, report_id):
    report = get_object_or_404(DailyStatusReport, id=report_id)
    if report.user != request.user:
        return HttpResponseForbidden()

    data = {
        "previous_work": report.previous_work,
        "next_plan": report.next_plan,
        "blockers": report.blockers,
    }
    return JsonResponse(data)
