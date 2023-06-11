from django.urls import include, path
from company.views import (
    CompanyDashboardAnalyticsView,
    CompanyDashboardManageBugsView,
    CompanyDashboardManageDomainsView,
    AddDomainView,
    DomainView,
    CompanyDashboardManageRolesView,
    company_view,
)


urlpatterns = [
    path("dashboard/",company_view,name="company_view"),
    path("dashboard/analytics/<str:company>/",CompanyDashboardAnalyticsView.as_view(),name="company_analytics"),
    path("dashboard/bugs/<str:company>/",CompanyDashboardManageBugsView.as_view(),name="company_manage_bugs"),
    path("dashboard/domains/<str:company>/",CompanyDashboardManageDomainsView.as_view(),name="company_manage_domains"),
    path("dashboard/roles/<str:company>/",CompanyDashboardManageRolesView.as_view(),name="company_manage_roles"),
    path("dashboard/add_domain/<str:company>",AddDomainView.as_view(),name="add_domain"),
    path("domain/<int:pk>/",DomainView.as_view(),name="view_domain"),
]