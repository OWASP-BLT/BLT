from django.conf.urls import include, url, patterns
from django.conf import settings
from django.contrib import admin
from django.views.generic import TemplateView
from website.views import (UserProfileDetailView, IssueCreate, UploadCreate, EmailDetailView, UpdateIssue,
                           InboundParseWebhookView, LeaderboardView, IssueView, IssueEditView, AllIssuesView,
                           HuntCreate, DomainDetailView, StatsDetailView, InviteCreate, CreateInviteFriend)
from django.contrib.auth.decorators import login_required
from django.views.generic.base import RedirectView
from django.conf.urls.static import static
from django.views.decorators.csrf import csrf_exempt

favicon_view = RedirectView.as_view(url='/static/favicon.ico', permanent=True)



admin.autodiscover()

import website.views

urlpatterns = patterns('',
    url(r'^$', website.views.index, name='index'),
    url(r'^' + settings.ADMIN_URL + '/', include(admin.site.urls)),
    url(r'^issue/(?P<slug>\w+)/$', IssueView.as_view(), name="issue_view"),
    url(r'^issue/(?P<slug>\w+)/edit/$', IssueEditView.as_view(), name="issue_edit"),
    url(r'^all_activity/$', AllIssuesView.as_view(), name="all_activity"),
    url(r'^leaderboard/$', LeaderboardView.as_view(), name="leaderboard"),
    url(r'^issue/$', IssueCreate.as_view(), name="issue"),
    url(r'^upload/(?P<time>[^/]+)/(?P<hash>[^/]+)/', UploadCreate.as_view(), name="upload"),
    url(r'^profile/(?P<slug>[^/]+)/$', UserProfileDetailView.as_view(), name="profile"),
    url(r'^domain/(?P<slug>[^/]+)/$', DomainDetailView.as_view(), name="domain"),
    url(r'^email/(?P<slug>[^/]+)/$', EmailDetailView.as_view(), name="email"),
    url(r'^.well-known/acme-challenge/(?P<token>[^/]+)/$', website.views.find_key, name="find_key"),
    url(r'^accounts/profile/', website.views.profile),
    url(r'^delete_issue/(?P<id>\w+)/$', website.views.delete_issue),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^activity/', include('actstream.urls')),
    url(r'^start/$', TemplateView.as_view(template_name="hunt.html")),
    url(r'^hunt/$', login_required(HuntCreate.as_view()), name="hunt"),
    url(r'^update/$', login_required(UpdateIssue.as_view()), name="update"),
    url(r'^invite/$', InviteCreate.as_view(template_name="invite.html")),
    url(r'^invite-friend/$', CreateInviteFriend.as_view(), name='invite_friend'),
    url(r'^terms/$', TemplateView.as_view(template_name="terms.html")),
    url(r'^stats/$', StatsDetailView.as_view()),
    url(r'^favicon\.ico$', favicon_view),
    url(r'^sendgrid_webhook/$', csrf_exempt(InboundParseWebhookView.as_view()), name='inbound_event_webhook_callback'),

) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

