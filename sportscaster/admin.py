from django.contrib import admin

from .models import AICommentaryTemplate, GitHubEvent, Leaderboard, MonitoredEntity, UserChannel


@admin.register(MonitoredEntity)
class MonitoredEntityAdmin(admin.ModelAdmin):
    list_display = ["name", "scope", "is_active", "created_at"]
    list_filter = ["scope", "is_active"]
    search_fields = ["name", "github_url"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(GitHubEvent)
class GitHubEventAdmin(admin.ModelAdmin):
    list_display = ["event_type", "monitored_entity", "timestamp", "processed", "commentary_generated"]
    list_filter = ["event_type", "processed", "commentary_generated", "timestamp"]
    search_fields = ["monitored_entity__name"]
    readonly_fields = ["timestamp"]
    date_hierarchy = "timestamp"


@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ["monitored_entity", "metric_type", "current_value", "rank", "updated_at"]
    list_filter = ["metric_type"]
    search_fields = ["monitored_entity__name"]
    readonly_fields = ["updated_at"]


@admin.register(UserChannel)
class UserChannelAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "is_public", "created_at"]
    list_filter = ["is_public", "created_at"]
    search_fields = ["name", "user__username"]
    readonly_fields = ["created_at", "updated_at"]
    filter_horizontal = ["monitored_entities"]


@admin.register(AICommentaryTemplate)
class AICommentaryTemplateAdmin(admin.ModelAdmin):
    list_display = ["event_type", "is_active", "created_at"]
    list_filter = ["event_type", "is_active"]
    search_fields = ["event_type", "template"]
