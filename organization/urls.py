from django.contrib.auth.decorators import login_required
from django.urls import path

from organization.views import (
    AddDomainView,
    AddHuntView,
    DomainView,
    EndBughuntView,
    OrganizationDashboardAnalyticsView,
    OrganizationDashboardManageBughuntView,
    OrganizationDashboardManageBugsView,
    OrganizationDashboardManageDomainsView,
    OrganizationDashboardManageRolesView,
    RegisterOrganizationView,
    accept_bug,
    delete_manager,
    delete_prize,
    edit_prize,
    organization_view,
)

urlpatterns = [
    path("", RegisterOrganizationView.as_view(), name="register_organization"),
    path("dashboard/", organization_view, name="organization_view"),
    path(
        "<int:id>/dashboard/analytics/",
        OrganizationDashboardAnalyticsView.as_view(),
        name="organization_analytics",
    ),
    path(
        "<int:id>/dashboard/bugs/",
        OrganizationDashboardManageBugsView.as_view(),
        name="organization_manage_bugs",
    ),
    path(
        "<int:id>/dashboard/domains/",
        OrganizationDashboardManageDomainsView.as_view(),
        name="organization_manage_domains",
    ),
    path(
        "<int:id>/dashboard/roles/",
        OrganizationDashboardManageRolesView.as_view(),
        name="organization_manage_roles",
    ),
    path(
        "<int:id>/dashboard/bughunts/",
        OrganizationDashboardManageBughuntView.as_view(),
        name="organization_manage_bughunts",
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
    path("delete_prize/<int:prize_id>/<int:organization_id>", delete_prize, name="delete_prize"),
    path("edit_prize/<int:prize_id>/<int:organization_id>", edit_prize, name="edit_prize"),
    path("accept_bug/<int:issue_id>/<str:reward_id>/", accept_bug, name="accept_bug"),
    path("accept_bug/<int:issue_id>/<str:no_reward>/", accept_bug, name="accept_bug_no_reward"),
    path("delete_manager/<int:manager_id>/<int:domain_id>/", delete_manager, name="delete_manager"),
]
