from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

import comments.views
import website.views
from website.views import (UserProfileDetailView, IssueCreate, UploadCreate, EmailDetailView,
                           InboundParseWebhookView, LeaderboardView, IssueView, AllIssuesView,
                           HuntCreate, DomainDetailView, StatsDetailView, InviteCreate, CreateInviteFriend,
                           ScoreboardView)

favicon_view = RedirectView.as_view(url='/static/favicon.ico', permanent=True)

admin.autodiscover()

urlpatterns = [
                  url(r'^$', website.views.index, name='index'),
                  url(r'^' + settings.ADMIN_URL + '/', include(admin.site.urls)),
                  url(r'^like_issue/(?P<issue_pk>\d+)/$', website.views.like_issue,name="like_issue"),
                  url(r'^issue/edit/$', website.views.IssueEdit),
                  url(r'^issue/update/$', website.views.UpdateIssue),
                  url(r'^issue/(?P<slug>\w+)/$', IssueView.as_view(), name="issue_view"),
                  url(r'^follow_user/(?P<user>[^/]+)/', website.views.follow_user,name="follow_user"),
                  url(r'^all_activity/$', AllIssuesView.as_view(), name="all_activity"),
                  url(r'^leaderboard/$', LeaderboardView.as_view(), name="leaderboard"),
                  url(r'^scoreboard/$', ScoreboardView.as_view(), name="scoreboard"),
                  url(r'^issue/$', IssueCreate.as_view(), name="issue"),
                  url(r'^upload/(?P<time>[^/]+)/(?P<hash>[^/]+)/',
                      UploadCreate.as_view(), name="upload"),
                  url(r'^profile/(?P<slug>[^/]+)/$',
                      UserProfileDetailView.as_view(), name="profile"),
                  url(r'^domain/(?P<slug>[^/]+)/$',
                      DomainDetailView.as_view(), name="domain"),
                  url(r'^email/(?P<slug>[^/]+)/$', EmailDetailView.as_view(), name="email"),
                  url(r'^.well-known/acme-challenge/(?P<token>[^/]+)/$',
                      website.views.find_key, name="find_key"),
                  url(r'^accounts/profile/', website.views.profile),
                  url(r'^delete_issue/(?P<id>\w+)/$', website.views.delete_issue),
                  url(r'^accounts/', include('allauth.urls')),
                  url(r'^start/$', TemplateView.as_view(template_name="hunt.html")),
                  url(r'^hunt/$', login_required(HuntCreate.as_view()), name="hunt"),
                  url(r'^invite/$', InviteCreate.as_view(template_name="invite.html")),
                  url(r'^invite-friend/$', login_required(CreateInviteFriend.as_view()),
                      name='invite_friend'),
                  url(r'^terms/$', TemplateView.as_view(template_name="terms.html")),
                  url(r'^about/$', TemplateView.as_view(template_name="about.html")),
                  url(r'^stats/$', StatsDetailView.as_view()),
                  url(r'^favicon\.ico$', favicon_view),
                  url(r'^sendgrid_webhook/$', csrf_exempt(InboundParseWebhookView.as_view()),
                      name='inbound_event_webhook_callback'),
                  url(r'^issue/comment/add/$', comments.views.add_comment, name='add_comment'),
                  url(r'^issue/comment/delete/$',
                      comments.views.delete_comment, name='delete_comment'),
                  url(r'^comment/autocomplete/$',
                      comments.views.autocomplete, name='autocomplete'),
                  url(r'^issue/(?P<pk>\d+)/comment/edit/$',
                      comments.views.edit_comment, name='edit_comment'),
                  url(r'^issue/(?P<pk>\d+)/comment/reply/$',
                      comments.views.reply_comment, name='reply_comment'),
                  url(r'^social/$', TemplateView.as_view(template_name="social.html")),
                  url(r'^search/$', website.views.search),
                  url(r'^report/$', TemplateView.as_view(template_name="report.html")),
                  url(r'^i18n/', include('django.conf.urls.i18n')),
                  url(r'^domain_check/$', website.views.domain_check),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
                      url(r'^__debug__/', include(debug_toolbar.urls)),
                  ] + urlpatterns
