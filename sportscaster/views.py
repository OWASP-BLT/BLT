from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import GitHubEvent, Leaderboard, MonitoredEntity, UserChannel
from .serializers import (
    GitHubEventSerializer,
    LeaderboardSerializer,
    MonitoredEntitySerializer,
    UserChannelSerializer,
)
from .services import EventProcessingService


def sportscaster_home(request):
    """Main sportscaster view"""
    channels = []
    if request.user.is_authenticated:
        channels = UserChannel.objects.filter(user=request.user)

    context = {
        "channels": channels,
        "public_channels": UserChannel.objects.filter(is_public=True)[:5],
    }
    return render(request, "sportscaster/home.html", context)


def sportscaster_live(request, channel_id=None):
    """Live sportscaster stream view"""
    channel = None
    if channel_id:
        channel = get_object_or_404(UserChannel, id=channel_id)

    context = {
        "channel": channel,
        "channel_id": channel_id or "all",
    }
    return render(request, "sportscaster/live.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def manage_channels(request):
    """Manage user channels"""
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description", "")
        is_public = request.POST.get("is_public") == "on"

        channel = UserChannel.objects.create(
            user=request.user, name=name, description=description, is_public=is_public
        )

        return JsonResponse({"success": True, "channel_id": channel.id})

    channels = UserChannel.objects.filter(user=request.user)
    return render(request, "sportscaster/manage_channels.html", {"channels": channels})


@api_view(["GET"])
def api_leaderboard(request):
    """API endpoint for leaderboard data"""
    metric_type = request.query_params.get("metric", "stars")
    limit = int(request.query_params.get("limit", 10))

    leaderboard = Leaderboard.objects.filter(metric_type=metric_type).select_related("monitored_entity").order_by(
        "rank"
    )[:limit]

    serializer = LeaderboardSerializer(leaderboard, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def api_recent_events(request):
    """API endpoint for recent events"""
    limit = int(request.query_params.get("limit", 20))
    channel_id = request.query_params.get("channel_id")

    if channel_id:
        try:
            channel = UserChannel.objects.get(id=channel_id)
            entity_ids = channel.monitored_entities.values_list("id", flat=True)
            events = GitHubEvent.objects.filter(monitored_entity_id__in=entity_ids).select_related("monitored_entity")[
                :limit
            ]
        except UserChannel.DoesNotExist:
            return Response({"error": "Channel not found"}, status=status.HTTP_404_NOT_FOUND)
    else:
        events = GitHubEvent.objects.select_related("monitored_entity").order_by("-timestamp")[:limit]

    serializer = GitHubEventSerializer(events, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@login_required
def api_trigger_refresh(request):
    """API endpoint to trigger event refresh"""
    try:
        service = EventProcessingService()
        service.process_monitored_entities()
        return Response({"success": True, "message": "Refresh triggered successfully"})
    except Exception as e:
        return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MonitoredEntityViewSet(viewsets.ModelViewSet):
    """ViewSet for MonitoredEntity model"""

    queryset = MonitoredEntity.objects.all()
    serializer_class = MonitoredEntitySerializer


class UserChannelViewSet(viewsets.ModelViewSet):
    """ViewSet for UserChannel model"""

    serializer_class = UserChannelSerializer

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return UserChannel.objects.filter(user=self.request.user)
        return UserChannel.objects.filter(is_public=True)
