from django.conf.urls import include, url, patterns
from django.conf import settings
from django.contrib import admin
from django.views.generic import TemplateView
from website.views import UserProfileDetailView, IssueCreate, UploadCreate, IssueView, AllIssuesView, HuntCreate
from django.contrib.auth.decorators import login_required


from django.conf.urls.static import static

admin.autodiscover()

import website.views

urlpatterns = patterns('',
    url(r'^$', website.views.index, name='index'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^issue/(?P<slug>\w+)/$', IssueView.as_view(), name="issue_view"),
    url(r'^all_activity/$', AllIssuesView.as_view(), name="all_activity"),
    url(r'^issue/$', login_required(IssueCreate.as_view()), name="issue"),
    url(r'^upload/(?P<time>[^/]+)/(?P<hash>[^/]+)/', UploadCreate.as_view(), name="upload"),
    url(r'^profile/(?P<slug>[^/]+)/$', UserProfileDetailView.as_view(), name="profile"),
    url(r'^accounts/profile/', website.views.profile),
    url(r'^accounts/', include('allauth.urls')), 
    url(r'^activity/', include('actstream.urls')),
    url(r'^start/$', TemplateView.as_view(template_name="hunt.html")),
    url(r'^hunt/$', login_required(HuntCreate.as_view()), name="hunt"),
	url(r'^buttons/$', TemplateView.as_view(template_name="buttons.html")),

) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

