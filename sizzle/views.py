import logging
from collections import defaultdict
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from sizzle.utils import format_timedelta, get_github_issue_title
from sizzle.utils.model_loader import get_daily_status_report_model, get_organization_model, get_timelog_model

logger = logging.getLogger(__name__)


def sizzle_docs(request):
    return render(request, "sizzle_docs.html")


def sizzle(request):
    # Get models dynamically
    TimeLog = get_timelog_model()
    
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
        "sizzle.html",
        {"sizzle_data": sizzle_data, "leaderboard": leaderboard},
    )


def checkIN(request):
    from datetime import date

    # Get models dynamically
    DailyStatusReport = get_daily_status_report_model()

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
        "checkin.html",
        {
            "data": data,
            "default_start_date": default_start_date.isoformat(),
            "default_end_date": default_end_date.isoformat(),
        },
    )


def truncate_text(text, length=15):
    return text if len(text) <= length else text[:length] + "..."


@login_required
def add_sizzle_checkIN(request):
    # Get models dynamically
    DailyStatusReport = get_daily_status_report_model()
    
    # Fetch yesterday's report
    yesterday = now().date() - timedelta(days=1)
    yesterday_report = DailyStatusReport.objects.filter(user=request.user, date=yesterday).first()

    # Fetch all check-ins for the user, ordered by date
    all_checkins = DailyStatusReport.objects.filter(user=request.user).order_by("-date")

    return render(
        request,
        "add_sizzle_checkin.html",
        {"yesterday_report": yesterday_report, "all_checkins": all_checkins},
    )


@login_required
def checkIN_detail(request, report_id):
    DailyStatusReport = get_daily_status_report_model()
    report = get_object_or_404(DailyStatusReport, pk=report_id)
    
    # Restrict to own reports or authorized users
    if report.user != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You don't have permission to view this report.")
    
    context = {
        "username": report.user.username,
        "date": report.date.strftime("%d %B %Y"),
        "previous_work": report.previous_work,
        "next_plan": report.next_plan,
        "blockers": report.blockers,
    }
    return render(request, "checkin_detail.html", context)


def TimeLogListAPIView(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

    # Get models dynamically
    TimeLog = get_timelog_model()

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


@login_required
def TimeLogListView(request):
    # Get models dynamically
    TimeLog = get_timelog_model()
    Organization = get_organization_model()
    
    time_logs = TimeLog.objects.filter(user=request.user).order_by("-start_time")
    active_time_log = time_logs.filter(end_time__isnull=True).first()

    # print the all details of the active time log
    token, created = Token.objects.get_or_create(user=request.user)
    organizations_list = []
    if Organization:
        organizations_list_queryset = Organization.objects.all().values("url", "name")
        organizations_list = list(organizations_list_queryset)
    organization_url = None
    if active_time_log and active_time_log.organization:
        organization_url = active_time_log.organization.url
    return render(
        request,
        "time_logs.html",
        {
            "time_logs": time_logs,
            "active_time_log": active_time_log,
            "token": token.key,
            "organizations_list": organizations_list,
            "organization_url": organization_url,
        },
    )


@login_required
def sizzle_daily_log(request):
    # Get models dynamically
    DailyStatusReport = get_daily_status_report_model()
    
    try:
        if request.method == "GET":
            reports = DailyStatusReport.objects.filter(user=request.user).order_by("-date")
            return render(request, "sizzle_daily_status.html", {"reports": reports})

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

    except (ValidationError, IntegrityError) as e:
        logger.exception("Error creating daily status report")
        messages.error(request, "An error occurred while submitting your report. Please try again.")
        return redirect("sizzle")

    return HttpResponseBadRequest("Invalid request method.")


@login_required
def user_sizzle_report(request, username):
    # Get models dynamically
    TimeLog = get_timelog_model()
    
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
        end_time = first_log.end_time.strftime("%I:%M %p") if first_log.end_time else "In Progress"
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
        "user_sizzle_report.html",
        {"response_data": response_data, "user": user},
    )
