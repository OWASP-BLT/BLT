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
    accept_bug,
    company_view,
    delete_manager,
    delete_prize,
    edit_prize,
)

urlpatterns = [
    path("", RegisterCompanyView.as_view(), name="register_company"),
    path("dashboard/", company_view, name="company_view"),
    path(
        "<int:id>/dashboard/analytics/",
        CompanyDashboardAnalyticsView.as_view(),
        name="company_analytics",
    ),
    path(
        "<int:id>/dashboard/bugs/",
        CompanyDashboardManageBugsView.as_view(),
        name="company_manage_bugs",
    ),
    path(
        "<int:id>/dashboard/domains/",
        CompanyDashboardManageDomainsView.as_view(),
        name="company_manage_domains",
    ),
    path(
        "<int:id>/dashboard/roles/",
        CompanyDashboardManageRolesView.as_view(),
        name="company_manage_roles",
    ),
    path(
        "<int:id>/dashboard/bughunts/",
        CompanyDashboardManageBughuntView.as_view(),
        name="company_manage_bughunts",
    ),
    path("dashboard/end_bughunt/<int:pk>", EndBughuntView.as_view(), name="end_bughunt"),
    path("<int:id>/dashboard/add_bughunt/", AddHuntView.as_view(), name="add_bughunt"),
    path("<int:id>/dashboard/add_domain/", AddDomainView.as_view(), name="add_domain"),
    path(
        "<int:id>/dashboard/edit_domain/<int:domain_id>/",
        AddDomainView.as_view(),
        name="edit_domain",
    ),
    path("domain/<int:pk>/", login_required(DomainView.as_view()), name="view_domain"),
    path("delete_prize/<int:prize_id>/<int:company_id>", delete_prize, name="delete_prize"),
    path("edit_prize/<int:prize_id>/<int:company_id>", edit_prize, name="edit_prize"),
    path("accept_bug/<int:issue_id>/<str:reward_id>/", accept_bug, name="accept_bug"),
    path("accept_bug/<int:issue_id>/<str:no_reward>/", accept_bug, name="accept_bug_no_reward"),
    path("delete_manager/<int:manager_id>/<int:domain_id>/", delete_manager, name="delete_manager"),
]
