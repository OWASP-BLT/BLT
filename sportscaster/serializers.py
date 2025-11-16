from rest_framework import serializers

from .models import GitHubEvent, Leaderboard, MonitoredEntity, UserChannel


class MonitoredEntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitoredEntity
        fields = ["id", "name", "scope", "github_url", "is_active", "created_at", "updated_at", "metadata"]
        read_only_fields = ["created_at", "updated_at"]


class GitHubEventSerializer(serializers.ModelSerializer):
    repository = serializers.CharField(source="monitored_entity.name", read_only=True)

    class Meta:
        model = GitHubEvent
        fields = [
            "id",
            "repository",
            "event_type",
            "event_data",
            "timestamp",
            "processed",
            "commentary_generated",
            "commentary_text",
        ]
        read_only_fields = ["id", "timestamp", "processed", "commentary_generated", "commentary_text"]


class LeaderboardSerializer(serializers.ModelSerializer):
    repository = serializers.CharField(source="monitored_entity.name", read_only=True)
    change = serializers.SerializerMethodField()

    class Meta:
        model = Leaderboard
        fields = ["id", "repository", "metric_type", "current_value", "previous_value", "rank", "change", "updated_at"]
        read_only_fields = ["id", "updated_at"]

    def get_change(self, obj):
        return obj.current_value - obj.previous_value


class UserChannelSerializer(serializers.ModelSerializer):
    monitored_entities_data = MonitoredEntitySerializer(source="monitored_entities", many=True, read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = UserChannel
        fields = [
            "id",
            "username",
            "name",
            "description",
            "monitored_entities",
            "monitored_entities_data",
            "is_public",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "username"]
