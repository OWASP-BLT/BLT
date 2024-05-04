from django.urls import path

from .views import SetOffsetView

urlpatterns = [
    path("set/", SetOffsetView.as_view(), name="tz_detect__set"),
]
