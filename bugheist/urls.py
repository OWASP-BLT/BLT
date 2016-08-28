from django.conf.urls import include, url

from django.contrib import admin
from website.views import UserProfileDetailView, IssueCreate
from django.contrib.auth.decorators import login_required
admin.autodiscover()

import website.views

urlpatterns = [
    url(r'^$', website.views.index, name='index'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^issue/', login_required(IssueCreate.as_view()), name="issue"),
    url(r'^profile/(?P<slug>[^/]+)/$', UserProfileDetailView.as_view(), name="profile"),
    url(r'^accounts/profile/', website.views.profile),
    url(r'^accounts/', include('allauth.urls')), 
    url(r'^activity/', include('actstream.urls')),
]
