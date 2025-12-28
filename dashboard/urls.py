from django.urls import path
from .views import security_dashboard

urlpatterns = [
    path("dashboard/security/", security_dashboard, name="security-dashboard"),
]

