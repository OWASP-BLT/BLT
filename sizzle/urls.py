from django.urls import path
from . import views

app_name = "sizzle"

urlpatterns = [
    path("", views.SizzleListView.as_view(), name="index"),
    path("docs/", views.SizzleListView.as_view(), name="docs"), 
    path("log/", views.SizzleListView.as_view(), name="sizzle_daily_log"),
    path("report/<str:username>/", views.user_sizzle_report_view, name="user_sizzle_report"),
    path("check-in/", views.checkin, name="checkin"),
    path("add-checkin/", views.add_sizzle_checkin, name="add_sizzle_checkin"),
    path("check-in/<int:report_id>/", views.checkin_detail, name="checkin_detail"),
]