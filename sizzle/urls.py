from django.urls import path

from sizzle.views import (
    TimeLogListAPIView,
    TimeLogListView,
    add_sizzle_checkIN,
    checkIN,
    checkIN_detail,
    sizzle,
    sizzle_daily_log,
    sizzle_docs,
    user_sizzle_report,
)

urlpatterns = [
    path("", sizzle, name="sizzle"),
    path("check-in/", checkIN, name="checkIN"),
    path("add-sizzle-checkin/", add_sizzle_checkIN, name="add_sizzle_checkin"),
    path("check-in/<int:report_id>/", checkIN_detail, name="checkIN_detail"),
    path("docs/", sizzle_docs, name="sizzle_docs"),
    path("api/timelogsreport/", TimeLogListAPIView, name="timelogsreport"),
    path("time-logs/", TimeLogListView, name="time_logs"),
    path("sizzle-daily-log/", sizzle_daily_log, name="sizzle_daily_log"),
    path(
        "user-sizzle-report/<str:username>/",
        user_sizzle_report,
        name="user_sizzle_report",
    ),
]
