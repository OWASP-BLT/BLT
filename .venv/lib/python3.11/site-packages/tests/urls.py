from __future__ import unicode_literals

from django.urls import include, path

urlpatterns = [
    path('ratings/', include('star_ratings.urls', namespace='ratings')),
]
