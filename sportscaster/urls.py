from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"monitored-entities", views.MonitoredEntityViewSet, basename="monitored-entity")
router.register(r"channels", views.UserChannelViewSet, basename="channel")

app_name = "sportscaster"

urlpatterns = [
    # Web views
    path("", views.sportscaster_home, name="home"),
    path("live/", views.sportscaster_live, name="live"),
    path("live/<int:channel_id>/", views.sportscaster_live, name="live_channel"),
    path("channels/manage/", views.manage_channels, name="manage_channels"),
    # API endpoints
    path("api/", include(router.urls)),
    path("api/leaderboard/", views.api_leaderboard, name="api_leaderboard"),
    path("api/events/", views.api_recent_events, name="api_events"),
    path("api/refresh/", views.api_trigger_refresh, name="api_refresh"),
]
