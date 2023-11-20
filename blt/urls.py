from posixpath import basename
from django.conf import settings
from django.urls import path
from django.conf.urls import include

from django.urls import re_path

from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from dj_rest_auth.views import PasswordResetConfirmView

import comments.views
import website.views
from website.views import (
    UserProfileDetailView,
    IssueCreate,
    UploadCreate,
    InboundParseWebhookView,
    EachmonthLeaderboardView,
    GlobalLeaderboardView,
    SpecificMonthLeaderboardView,
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
    ListHunts,
    contributors_view,
    github_callback,
    google_callback,
    facebook_callback,
    sponsor_view
)
from website.api.views import (
    IssueViewSet,
    DomainViewSet,
    UserIssueViewSet,
    UserProfileViewSet,
    LikeIssueApiView,
    FlagIssueApiView,
    LeaderboardApiViewSet,
    StatsApiViewset,
    UrlCheckApiViewset,
    BugHuntApiViewset,
    BugHuntApiViewsetV2,
    InviteFriendApiViewset
)
from company.views import ShowBughuntView
from website.alternative_views import (
    like_issue2,
    flag_issue2,
    subscribe_to_domains,
    IssueView2
)

from blt import settings
from rest_framework import permissions, routers
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from dj_rest_auth.registration.views import (
    SocialAccountListView,
    SocialAccountDisconnectView,
)

favicon_view = RedirectView.as_view(url="/static/favicon.ico", permanent=True)

router = routers.DefaultRouter()
router.register(r"issues", IssueViewSet, basename="issues")
router.register(r"userissues", UserIssueViewSet, basename="userissues")
router.register(r"profile", UserProfileViewSet, basename="profile")
router.register(r"domain", DomainViewSet, basename="domain")

from allauth.socialaccount.providers.github import views as github_views
from allauth.socialaccount.providers.google import views as google_views
from allauth.socialaccount.providers.facebook import views as facebook_views
from django.contrib import admin
from django.urls import include, path

admin.autodiscover()
schema_view = get_schema_view(
    openapi.Info(
        title="API",
        default_version="v1",
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

handler404 = "website.views.handler404"
handler500 = "website.views.handler500"

urlpatterns = [
    path("captcha/", include("captcha.urls")),
    re_path(r"^auth/registration/", include("dj_rest_auth.registration.urls")),
    path('rest-auth/password/reset/confirm/<str:uidb64>/<str:token>', PasswordResetConfirmView.as_view(),
           name='password_reset_confirm'),
    re_path(r"^auth/", include("dj_rest_auth.urls")),
    re_path("auth/facebook", FacebookLogin.as_view(), name="facebook_login"),
    path('accounts/', include('allauth.urls')),
    path("auth/github/", GithubLogin.as_view(), name="github_login"),
    path("auth/google/", GoogleLogin.as_view(), name="google_login"),
    path("accounts/github/login/callback/", github_callback, name="github_callback"),
    path("accounts/google/login/callback/", google_callback, name="google_callback"),
    path(
        "accounts/facebook/login/callback/", facebook_callback, name="facebook_callback"
    ),
    re_path(
        r"^auth/facebook/connect/$", FacebookConnect.as_view(), name="facebook_connect"
    ),
    re_path(r"^auth/github/connect/$", GithubConnect.as_view(), name="github_connect"),
    re_path(r"^auth/google/connect/$", GoogleConnect.as_view(), name="google_connect"),
    path("auth/github/url/", github_views.oauth2_login),
    path("auth/google/url/", google_views.oauth2_login),
    path("auth/facebook/url/", facebook_views.oauth2_callback),
    path(
        "socialaccounts/", SocialAccountListView.as_view(), name="social_account_list"
    ),
    path(
        "socialaccounts/<int:pk>/disconnect/",
        SocialAccountDisconnectView.as_view(),
        name="social_account_disconnect",
    ),
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    re_path(
        r"^swagger/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    re_path(
        r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    ),
    re_path(r"^$", website.views.index, name="index"),
    re_path(
        r"^dashboard/company/$",
        website.views.company_dashboard,
        name="company_dashboar_home",
    ),
    re_path(
        r"^dashboard/user/profile/addbalance$",
        website.views.addbalance,
        name="addbalance",
    ),
    re_path(
        r"^dashboard/user/profile/withdraw$", website.views.withdraw, name="withdraw"
    ),
    re_path(
        r"^dashboard/user/stripe/connected/(?P<username>[^/]+)/$",
        website.views.stripe_connected,
        name="stripe_connected",
    ),
    re_path(
        r"^dashboard/admin$", website.views.admin_dashboard, name="admin_dashboard"
    ),
    re_path(
        r"^dashboard/admin/company$",
        website.views.admin_company_dashboard,
        name="admin_company_dashboard",
    ),
    re_path(
        r"^dashboard/admin/company/addorupdate$",
        website.views.add_or_update_company,
        name="add_or_update_company",
    ),
    re_path(
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
    re_path(
        r"^dashboard/company/hunt/create$", CreateHunt.as_view(), name="create_hunt"
    ),
    path(
        "hunt/<int:pk>", ShowBughuntView.as_view(), name="show_bughunt"
    ),
    re_path(
        r"^dashboard/company/hunt/drafts$", DraftHunts.as_view(), name="draft_hunts"
    ),
    re_path(
        r"^dashboard/company/hunt/upcoming$",
        UpcomingHunts.as_view(),
        name="upcoming_hunts",
    ),
    re_path(
        r"^dashboard/company/hunt/previous$",
        PreviousHunts.as_view(),
        name="previous_hunts",
    ),
    path(
        "dashboard/company/hunt/previous/<int:pk>/",
        website.views.company_hunt_results,
        name="company_hunt_results",
    ),
    re_path(
        r"^dashboard/company/hunt/ongoing$",
        OngoingHunts.as_view(),
        name="ongoing_hunts",
    ),
    re_path(r"^dashboard/company/domains$", DomainList.as_view(), name="domain_list"),
    re_path(
        r"^dashboard/company/settings$",
        CompanySettings.as_view(),
        name="company-settings",
    ),
    re_path(r"^join$", JoinCompany.as_view(), name="join"),
    re_path(
        r"^dashboard/company/settings/role/update$",
        website.views.update_role,
        name="update-role",
    ),
    re_path(
        r"^dashboard/company/settings/role/add$",
        website.views.add_role,
        name="add-role",
    ),
    re_path(r"^dashboard/user/$", website.views.user_dashboard, name="user"),
    re_path(
        r"^dashboard/user/profile/(?P<slug>[^/]+)/$",
        UserProfileDetailsView.as_view(),
        name="user_profile",
    ),
    path(settings.ADMIN_URL + "/", admin.site.urls),
    re_path(
        r"^like_issue/(?P<issue_pk>\d+)/$", website.views.like_issue, name="like_issue"
    ),
    re_path(
        r"^dislike_issue/(?P<issue_pk>\d+)/$", website.views.dislike_issue, name="dislike_issue"
    ),
    re_path(
        r"^flag_issue/(?P<issue_pk>\d+)/$", website.views.flag_issue, name="flag_issue"
    ),
    re_path(
        r"^like_issue2/(?P<issue_pk>\d+)/$", like_issue2, name="like_issue2"
    ),
    re_path(
        r"^flag_issue2/(?P<issue_pk>\d+)/$", flag_issue2, name="flag_issue2"
    ),
    path(
        "domain/<int:pk>/subscribe/", subscribe_to_domains, name="subscribe_to_domains"
    ),

    re_path(
        r"^save_issue/(?P<issue_pk>\d+)/$", website.views.save_issue, name="save_issue"
    ),
    re_path(
        r"^unsave_issue/(?P<issue_pk>\d+)/$",
        website.views.unsave_issue,
        name="unsave_issue",
    ), 
    re_path(r"^issue/edit/$", website.views.IssueEdit, name="edit_issue"),
    re_path(r"^issue/update/$", website.views.UpdateIssue, name="update_issue"),
    path("issue/<str:issue_pk>/comment/", website.views.comment_on_issue, name="comment_on_issue"),
    # UPDATE COMMENT
    path("issue/<str:issue_pk>/comment/update/<str:comment_pk>/", website.views.update_comment, name="update_comment"),
    # delete_comment 
    path("issue2/comment/delete/", website.views.delete_comment, name="delete_comment"),
    re_path(r"^issue/(?P<slug>\w+)/$", IssueView.as_view(), name="issue_view"),
    re_path(r"^issue2/(?P<slug>\w+)/$", IssueView2.as_view(), name="issue_view2"),
    re_path(r"^follow/(?P<user>[^/]+)/", website.views.follow_user, name="follow_user"),
    re_path(r"^all_activity/$", AllIssuesView.as_view(), name="all_activity"),
    re_path(r"^label_activity/$", SpecificIssuesView.as_view(), name="all_activity"),
    re_path(r"^leaderboard/$", GlobalLeaderboardView.as_view(), name="leaderboard_global"),
    re_path(r"^leaderboard/monthly/$", SpecificMonthLeaderboardView.as_view(), name="leaderboard_specific_month"),
    re_path(r"^leaderboard/each-month/$", EachmonthLeaderboardView.as_view(), name="leaderboard_eachmonth"),
    re_path(r"^api/v1/issue/like/(?P<id>\w+)/$", LikeIssueApiView.as_view(), name="like_issue"),
    re_path(r"^api/v1/issue/flag/(?P<id>\w+)/$", FlagIssueApiView.as_view(), name="flag_issue"),
    re_path(r"^api/v1/leaderboard/$",LeaderboardApiViewSet.as_view(),name="leaderboard"),
    re_path(r"^api/v1/invite_friend/",InviteFriendApiViewset.as_view(),name="invite_friend"),

    re_path(r"^scoreboard/$", ScoreboardView.as_view(), name="scoreboard"),
    re_path(r"^issue/$", IssueCreate.as_view(), name="issue"),

    re_path(
        r"^upload/(?P<time>[^/]+)/(?P<hash>[^/]+)/",
        UploadCreate.as_view(),
        name="upload",
    ),
    re_path(
        r"^profile/(?P<slug>[^/]+)/$", UserProfileDetailView.as_view(), name="profile"
    ),
    re_path(r"^domain/(?P<slug>[^/]+)/$", DomainDetailView.as_view(), name="domain"),
    re_path(
        r"^.well-known/acme-challenge/(?P<token>[^/]+)/$",
        website.views.find_key,
        name="find_key",
    ),
    re_path(r"^accounts/profile/", website.views.profile, name="account_profile"),
    re_path(r"^delete_issue/(?P<id>\w+)/$", website.views.delete_issue, name="delete_issue"),
    re_path(r"^accounts/", include("allauth.urls")),
    re_path(r"^start/$", TemplateView.as_view(template_name="hunt.html"),name="start_hunt"),
    re_path(r"^hunt/$", login_required(HuntCreate.as_view()), name="hunt"),
    re_path(r"^hunts/$", ListHunts.as_view(), name="hunts"),
    re_path(r"^invite/$", InviteCreate.as_view(template_name="invite.html")),
    re_path(
        r"^invite-friend/$",
        login_required(CreateInviteFriend.as_view()),
        name="invite_friend",
    ),
    re_path(r"^terms/$", TemplateView.as_view(template_name="terms.html"),name="terms"),
    re_path(r"^about/$", TemplateView.as_view(template_name="about.html")),
    re_path(r"^privacypolicy/$", TemplateView.as_view(template_name="privacy.html")),
    re_path(r"^stats/$", StatsDetailView.as_view(), name="stats"),
    re_path(r"^favicon\.ico$", favicon_view),
    re_path(
        r"^sendgrid_webhook/$",
        csrf_exempt(InboundParseWebhookView.as_view()),
        name="inbound_event_webhook_callback",
    ),
    re_path(r"^issue/comment/add/$", comments.views.add_comment, name="add_comment"),
    re_path(
        r"^issue/comment/delete/$", comments.views.delete_comment, name="delete_comment"
    ),
    re_path(
        r"^comment/autocomplete/$", comments.views.autocomplete, name="autocomplete"
    ),
    re_path(
        r"^issue/(?P<pk>\d+)/comment/edit/$",
        comments.views.edit_comment,
        name="edit_comment",
    ),
    re_path(
        r"^issue/(?P<pk>\d+)/comment/reply/$",
        comments.views.reply_comment,
        name="reply_comment",
    ),
    re_path(r"^social/$", TemplateView.as_view(template_name="social.html")),
    re_path(r"^search/$", website.views.search),
    re_path(r"^report/$", IssueCreate.as_view(),name="report"),
    re_path(r"^i18n/", include("django.conf.urls.i18n")),
    re_path(r"^api/v1/", include(router.urls)),
    re_path(r"^api/v1/stats/$", StatsApiViewset.as_view(), name="get_score"),
    re_path(r"^api/v1/urlcheck/$", UrlCheckApiViewset.as_view(), name="url_check"),
    re_path(
        r"^api/v1/hunt/$",BugHuntApiViewset.as_view(),name="hunt_details"
    ),
    re_path(
        r"^api/v2/hunts/$",BugHuntApiViewsetV2.as_view(),name="hunts_detail_v2"
    ),
    re_path(r"^api/v1/userscore/$", website.views.get_score, name="get_score"),
    re_path(r"^authenticate/", CustomObtainAuthToken.as_view()),
    re_path(r"^api/v1/createwallet/$", website.views.create_wallet, name="create_wallet"),
    re_path(r"^api/v1/count/$", website.views.issue_count, name="api_count"),
    re_path(r"^api/v1/contributors/$", website.views.contributors, name="api_contributor"),
    re_path(
        r"^api/v1/createissues/$",
        csrf_exempt(IssueCreate.as_view()),
        name="issuecreate",
    ),
    re_path(r"^api/v1/search/$", csrf_exempt(website.views.search_issues), name="search_issues"),
    re_path(
        r"^api/v1/delete_issue/(?P<id>\w+)/$", csrf_exempt(website.views.delete_issue), name="delete_api_issue"
    ),
    re_path(r"^api/v1/issue/update/$", csrf_exempt(website.views.UpdateIssue), name="update_api_issue"),
    re_path(r"^api/v1/scoreboard/$", website.views.get_scoreboard, name="api_scoreboard"),
    re_path(
        r"^api/v1/terms/$",
        csrf_exempt(TemplateView.as_view(template_name="mobile_terms.html")),
    ),
    re_path(
        r"^api/v1/about/$",
        csrf_exempt(TemplateView.as_view(template_name="mobile_about.html")),
    ),
    re_path(
        r"^api/v1/privacypolicy/$",
        csrf_exempt(TemplateView.as_view(template_name="mobile_privacy.html")),
    ),
    re_path(r"^error/", website.views.throw_error, name="post_error"),
    re_path(r"^tz_detect/", include("tz_detect.urls")),
    # re_path(r"^tellme/", include("tellme.urls")),
    re_path(r"^ratings/", include("star_ratings.urls", namespace="ratings")),
    path("robots.txt", website.views.robots_txt),
    path("ads.txt", website.views.ads_txt),
    re_path(r"^contributors/$",contributors_view,name="contributors"),
    path("company/",include("company.urls")),
    path("sponsor/",website.views.sponsor_view, name="sponsor")
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        re_path(r"^__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
