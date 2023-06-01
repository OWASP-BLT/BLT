from django.urls import include, path
from company.views import CompanyDashboard


urlpatterns = [

    path("dashboard/",CompanyDashboard.as_view(),name="company_dashboard")

]