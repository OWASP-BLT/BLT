from django.urls import include, path
from company.views import (
    CompanyDashboardAnalyticsView,
    CompanyDashboardManageBugsView,
    CompanyDashboardManageDomainsView,
    AddDomainView
)


urlpatterns = [

    path("dashboard/analytics/",CompanyDashboardAnalyticsView.as_view(),name="company_analytics"),
    path("dashboard/bugs/",CompanyDashboardManageBugsView.as_view(),name="company_manage_bugs"),
    path("dashboard/domains/",CompanyDashboardManageDomainsView.as_view(),name="company_manage_domains"),
    path("dashboard/add_domain/",AddDomainView.as_view(),name="add_domain"),
]