from django.contrib.auth.decorators import login_required
from django.urls import path

from company.views import (
    AddDomainView,
    AddHuntView,
    CompanyDashboardAnalyticsView,
    CompanyDashboardManageBughuntView,
    CompanyDashboardManageBugsView,
    CompanyDashboardManageDomainsView,
    CompanyDashboardManageRolesView,
    DomainView,
    EndBughuntView,
    RegisterCompanyView,
    company_view,
)

urlpatterns = [
    path("", RegisterCompanyView.as_view(), name="register_company"),
    path("dashboard/", company_view, name="company_view"),
    path(
        "<str:company>/dashboard/analytics/",
        CompanyDashboardAnalyticsView.as_view(),
        name="company_analytics",
    ),
    path(
        "<str:company>/dashboard/bugs/",
        CompanyDashboardManageBugsView.as_view(),
        name="company_manage_bugs",
    ),
    path(
        "<str:company>/dashboard/domains/",
        CompanyDashboardManageDomainsView.as_view(),
        name="company_manage_domains",
    ),
    path(
        "<str:company>/dashboard/roles/",
        CompanyDashboardManageRolesView.as_view(),
        name="company_manage_roles",
    ),
    path(
        "<str:company>/dashboard/bughunts/",
        CompanyDashboardManageBughuntView.as_view(),
        name="company_manage_bughunts",
    ),
    path("dashboard/end_bughunt/<int:pk>", EndBughuntView.as_view(), name="end_bughunt"),
    path("<str:company>/dashboard/add_bughunt/", AddHuntView.as_view(), name="add_bughunt"),
    path("<str:company>/dashboard/add_domain/", AddDomainView.as_view(), name="add_domain"),
    path("domain/<int:pk>/", login_required(DomainView.as_view()), name="view_domain"),
]
