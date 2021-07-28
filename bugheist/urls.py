from django.conf import settings
from django.urls import path
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

import comments.views
import website.views
from website.views import (
    UserProfileDetailView,
    IssueCreate,
    UploadCreate,
    InboundParseWebhookView,
    LeaderboardView,
    IssueView,
    AllIssuesView,
    SpecificIssuesView,
    HuntCreate,
    DomainDetailView,
    StatsDetailView,
    InviteCreate,
    CreateInviteFriend,
    ScoreboardView,
    CustomObtainAuthToken,
    CreateHunt,
    DraftHunts,
    UpcomingHunts,
    CompanySettings,
    OngoingHunts,
    PreviousHunts,
    DomainList,
    UserProfileDetailsView,
    JoinCompany,
    FacebookLogin,
    FacebookConnect,
    GithubConnect,
    GithubLogin,
    GoogleLogin,
    GoogleConnect,
    IssueViewSet,
    DomainViewSet,
    UserIssueViewSet,
    UserProfileViewSet
)
from bugheist import settings
from rest_framework import permissions, routers
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from dj_rest_auth.registration.views import (
    SocialAccountListView, SocialAccountDisconnectView
)

favicon_view = RedirectView.as_view(url="/static/favicon.ico", permanent=True)

router = routers.DefaultRouter()
router.register(r'issues', IssueViewSet, basename="issues")
router.register(r'userissues', UserIssueViewSet, basename="userissues")
router.register(r'profile', UserProfileViewSet, basename="profile")
router.register(r'domain', DomainViewSet, basename="domain")

from website.views import github_callback, google_callback, facebook_callback
from allauth.socialaccount.providers.github import views as github_views
from allauth.socialaccount.providers.google import views as google_views
from allauth.socialaccount.providers.facebook import views as facebook_views
from django.contrib import admin
from django.urls import include, path

admin.autodiscover()
schema_view = get_schema_view(
    openapi.Info(
        title="BugHeist API",
        default_version="v1",
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path(
        "captcha/", include("captcha.urls")
    ),
    url(
        r'^auth/registration/', include('dj_rest_auth.registration.urls')
    ),
    url(
        r'^auth/', include('dj_rest_auth.urls')
    ),
    url(
        'auth/facebook', FacebookLogin.as_view(), name='facebook_login'
    ),
    path(
        'auth/github/', GithubLogin.as_view(), name='github_login'
    ),
    path(
        'auth/google/', GoogleLogin.as_view(), name='google_login'
    ),
    path(
        'accounts/github/login/callback/', github_callback, name='github_callback'
    ),
    path(
        'accounts/google/login/callback/', google_callback, name='google_callback'
    ),
    path(
        'accounts/facebook/login/callback/', facebook_callback, name='facebook_callback'
    ),
    url(
        r'^auth/facebook/connect/$', FacebookConnect.as_view(), name='facebook_connect'
    ),
    url(
        r'^auth/github/connect/$', GithubConnect.as_view(), name='github_connect'
    ),
    url(
        r'^auth/google/connect/$', GoogleConnect.as_view(), name='google_connect'
    ),
    path(
        'auth/github/url/', github_views.oauth2_login
    ),
    path(
        'auth/google/url/', google_views.oauth2_login
    ),
    path(
        'auth/facebook/url/', facebook_views.oauth2_callback
    ),
    path(
        'socialaccounts/',
        SocialAccountListView.as_view(),
        name='social_account_list'
    ),
    path(
        'socialaccounts/<int:pk>/disconnect/',
        SocialAccountDisconnectView.as_view(),
        name='social_account_disconnect'
    ),
    url(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    url(
        r"^swagger/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    url(
        r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    ),
    url(r"^$", website.views.index, name="index"),
    url(
        r"^dashboard/company/$",
        website.views.company_dashboard,
        name="company_dashboar_home",
    ),
    url(
        r"^dashboard/user/profile/addbalance$",
        website.views.addbalance,
        name="addbalance",
    ),
    url(r"^dashboard/user/profile/withdraw$", website.views.withdraw, name="withdraw"),
    url(
        r"^dashboard/user/stripe/connected/(?P<username>[^/]+)/$",
        website.views.stripe_connected,
        name="stripe_connected",
    ),
    url(r"^dashboard/admin$", website.views.admin_dashboard, name="admin_dashboard"),
    url(
        r"^dashboard/admin/company$",
        website.views.admin_company_dashboard,
        name="admin_company_dashboard",
    ),
    url(
        r"^dashboard/admin/company/addorupdate$",
        website.views.add_or_update_company,
        name="add_or_update_company",
    ),
    url(
        r"^dashboard/company/domain/addorupdate$",
        website.views.add_or_update_domain,
        name="add_or_update_domain",
    ),
    path(
        "dashboard/company/domain/<int:pk>/",
        website.views.company_dashboard_domain_detail,
        name="company_dashboard_domain_detail",
    ),
    path(
        "dashboard/company/hunt/<int:pk>/",
        website.views.company_dashboard_hunt_detail,
        name="company_dashboard_hunt_detail",
    ),
    path("dashboard/user/hunt/<int:pk>/", website.views.view_hunt, name="view_hunt"),
    path(
        "dashboard/user/hunt/<int:pk>/submittion/",
        website.views.submit_bug,
        name="submit_bug",
    ),
    path(
        "dashboard/user/hunt/<int:pk>/results/",
        website.views.hunt_results,
        name="hunt_results",
    ),
    path(
        "dashboard/company/hunt/<int:pk>/edit",
        website.views.company_dashboard_hunt_edit,
        name="company_dashboard_hunt_edit",
    ),
    path(
        "dashboard/admin/company/<int:pk>/",
        website.views.admin_company_dashboard_detail,
        name="admin_company_dashboard_detail",
    ),
    url(r"^dashboard/company/hunt/create$", CreateHunt.as_view(), name="create_hunt"),
    url(r"^dashboard/company/hunt/drafts$", DraftHunts.as_view(), name="draft_hunts"),
    url(
        r"^dashboard/company/hunt/upcoming$",
        UpcomingHunts.as_view(),
        name="upcoming_hunts",
    ),
    url(
        r"^dashboard/company/hunt/previous$",
        PreviousHunts.as_view(),
        name="previous_hunts",
    ),
    path(
        "dashboard/company/hunt/previous/<int:pk>/",
        website.views.company_hunt_results,
        name="company_hunt_results",
    ),
    url(
        r"^dashboard/company/hunt/ongoing$",
        OngoingHunts.as_view(),
        name="ongoing_hunts",
    ),
    url(r"^dashboard/company/domains$", DomainList.as_view(), name="domain_list"),
    url(
        r"^dashboard/company/settings$",
        CompanySettings.as_view(),
        name="company-settings",
    ),
    url(r"^join$", JoinCompany.as_view(), name="join"),
    url(
        r"^dashboard/company/settings/role/update$",
        website.views.update_role,
        name="update-role",
    ),
    url(
        r"^dashboard/company/settings/role/add$",
        website.views.add_role,
        name="add-role",
    ),
    url(r"^dashboard/user/$", website.views.user_dashboard, name="user"),
    url(
        r"^dashboard/user/profile/(?P<slug>[^/]+)/$",
        UserProfileDetailsView.as_view(),
        name="user_profile",
    ),
    path(settings.ADMIN_URL + "/", admin.site.urls),
    url(
        r"^like_issue/(?P<issue_pk>\d+)/$", website.views.like_issue, name="like_issue"
    ),
    url(
        r"^save_issue/(?P<issue_pk>\d+)/$", website.views.save_issue, name="save_issue"
    ),
    url(
        r"^unsave_issue/(?P<issue_pk>\d+)/$",
        website.views.unsave_issue,
        name="unsave_issue",
    ),
    url(r"^issue/edit/$", website.views.IssueEdit),
    url(r"^issue/update/$", website.views.UpdateIssue),
    url(r"^issue/(?P<slug>\w+)/$", IssueView.as_view(), name="issue_view"),
    url(r"^follow/(?P<user>[^/]+)/", website.views.follow_user, name="follow_user"),
    url(r"^all_activity/$", AllIssuesView.as_view(), name="all_activity"),
    url(r"^label_activity/$", SpecificIssuesView.as_view(), name="all_activity"),
    url(r"^leaderboard/$", LeaderboardView.as_view(), name="leaderboard"),
    url(r"^scoreboard/$", ScoreboardView.as_view(), name="scoreboard"),
    url(r"^issue/$", IssueCreate.as_view(), name="issue"),
    url(
        r"^upload/(?P<time>[^/]+)/(?P<hash>[^/]+)/",
        UploadCreate.as_view(),
        name="upload",
    ),
    url(r"^profile/(?P<slug>[^/]+)/$", UserProfileDetailView.as_view(), name="profile"),
    url(r"^domain/(?P<slug>[^/]+)/$", DomainDetailView.as_view(), name="domain"),
    url(
        r"^.well-known/acme-challenge/(?P<token>[^/]+)/$",
        website.views.find_key,
        name="find_key",
    ),
    url(r"^accounts/profile/", website.views.profile),
    url(r"^delete_issue/(?P<id>\w+)/$", website.views.delete_issue),
    url(r"^accounts/", include("allauth.urls")),
    url(r"^start/$", TemplateView.as_view(template_name="hunt.html")),
    url(r"^hunt/$", login_required(HuntCreate.as_view()), name="hunt"),
    url(r"^invite/$", InviteCreate.as_view(template_name="invite.html")),
    url(
        r"^invite-friend/$",
        login_required(CreateInviteFriend.as_view()),
        name="invite_friend",
    ),
    url(r"^terms/$", TemplateView.as_view(template_name="terms.html")),
    url(r"^about/$", TemplateView.as_view(template_name="about.html")),
    url(r"^privacypolicy/$", TemplateView.as_view(template_name="privacy.html")),
    url(r"^stats/$", StatsDetailView.as_view()),
    url(r"^favicon\.ico$", favicon_view),
    url(
        r"^sendgrid_webhook/$",
        csrf_exempt(InboundParseWebhookView.as_view()),
        name="inbound_event_webhook_callback",
    ),
    url(r"^issue/comment/add/$", comments.views.add_comment, name="add_comment"),
    url(
        r"^issue/comment/delete/$", comments.views.delete_comment, name="delete_comment"
    ),
    url(r"^comment/autocomplete/$", comments.views.autocomplete, name="autocomplete"),
    url(
        r"^issue/(?P<pk>\d+)/comment/edit/$",
        comments.views.edit_comment,
        name="edit_comment",
    ),
    url(
        r"^issue/(?P<pk>\d+)/comment/reply/$",
        comments.views.reply_comment,
        name="reply_comment",
    ),
    url(r"^social/$", TemplateView.as_view(template_name="social.html")),
    url(r"^search/$", website.views.search),
    url(r"^report/$", TemplateView.as_view(template_name="report.html")),
    url(r"^i18n/", include("django.conf.urls.i18n")),
    url(r"^domain_check/$", website.views.domain_check),
    url(r"^api/v1/", include(router.urls)),
    url(r"^api/v1/userscore/$", website.views.get_score),
    url(r"^authenticate/", CustomObtainAuthToken.as_view()),
    url(r"^api/v1/createwallet/$", website.views.create_wallet),
    url(r"^api/v1/count/$", website.views.issue_count),
    url(
        r"^api/v1/createissues/$",
        csrf_exempt(IssueCreate.as_view()),
        name="issuecreate",
    ),
    url(r"^api/v1/delete_issue/(?P<id>\w+)/$", csrf_exempt(website.views.delete_issue)),
    url(r"^api/v1/issue/update/$", csrf_exempt(website.views.UpdateIssue)),
    url(r"^api/v1/scoreboard/$", website.views.get_scoreboard),
    url(r"^api/v1/terms/$", csrf_exempt(TemplateView.as_view(template_name="mobile_terms.html"))),
    url(r"^api/v1/about/$", csrf_exempt(TemplateView.as_view(template_name="mobile_about.html"))),
    url(r"^api/v1/privacypolicy/$", csrf_exempt(TemplateView.as_view(template_name="mobile_privacy.html"))),
    url(r"^error/", website.views.throw_error, name="post_error"),
    url(r"^tz_detect/", include("tz_detect.urls")),
    url(r"^tellme/", include("tellme.urls")),
    url(r"^ratings/", include("star_ratings.urls", namespace="ratings")),
    path("robots.txt", website.views.robots_txt),
    path("ads.txt", website.views.ads_txt),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
                      url(r"^__debug__/", include(debug_toolbar.urls)),
                  ] + urlpatterns
