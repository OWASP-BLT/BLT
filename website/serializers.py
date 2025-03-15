from django.db.models import Sum
from rest_framework import serializers

from website.models import (
    ActivityLog,
    Contributor,
    Domain,
    Hunt,
    HuntPrize,
    Issue,
    IssueScreenshot,
    Organization,
    Points,
    Project,
    Repo,
    Tag,
    TimeLog,
    User,
    UserProfile,
)


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user model
    """

    class Meta:
        model = User
        fields = ("id", "username")


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user model
    """

    def get_total_score(self, instance):
        score = Points.objects.filter(user=instance.user).aggregate(total_score=Sum("score")).get("total_score")
        if score is None:
            return 0
        return score

    def get_activities(self, instance):
        issues = Points.objects.filter(user=instance.user, score__gt=0).values("issue__id")
        return [issue["issue__id"] for issue in issues]

    user = UserSerializer(read_only=True)
    total_score = serializers.SerializerMethodField(method_name="get_total_score")
    activities = serializers.SerializerMethodField(method_name="get_activities")

    class Meta:
        model = UserProfile
        fields = (
            "id",
            "title",
            "follows",
            "user",
            "user_avatar",
            "description",
            "winnings",
            "follows",
            "issue_upvoted",
            "issue_saved",
            "issue_flaged",
            "total_score",
            "activities",
        )


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"


class IssueScreenshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = IssueScreenshot
        fields = "__all__"


class IssueSerializer(serializers.ModelSerializer):
    """
    Serializer for Issue Model
    """

    user = UserSerializer(read_only=True)
    screenshots = IssueScreenshotSerializer(many=True, required=False)

    class Meta:
        model = Issue
        fields = "__all__"


class DomainSerializer(serializers.ModelSerializer):
    """
    Serializer for Domain Model
    """

    class Meta:
        model = Domain
        fields = "__all__"


class Bug BountyPrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HuntPrize
        fields = "__all__"


class Bug BountySerializer(serializers.ModelSerializer):
    class Meta:
        model = Hunt
        fields = "__all__"


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"


class ProjectSerializer(serializers.ModelSerializer):
    freshness = serializers.SerializerMethodField()
    stars = serializers.IntegerField()
    forks = serializers.IntegerField()
    external_links = serializers.JSONField()
    project_visit_count = serializers.IntegerField()

    class Meta:
        model = Project
        fields = "__all__"
        read_only_fields = ("slug", "contributors")

    def get_freshness(self, obj):
        return obj.fetch_freshness()


class ContributorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contributor
        fields = "__all__"


class TimeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeLog
        fields = [
            "id",
            "user",
            "organization",
            "start_time",
            "end_time",
            "duration",
            "github_issue_url",
            "created",
        ]
        read_only_fields = [
            "id",
            "user",
            "end_time",
            "duration",
            "created",
        ]  # These fields will be managed automatically


class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = ["id", "user", "window_title", "url", "recorded_at", "created"]
        read_only_fields = [
            "id",
            "user",
            "recorded_at",
            "created",
        ]  # Auto-filled fields


class RepoSerializer(serializers.ModelSerializer):
    """
    Serializer for Repo model
    """

    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        return obj.repo_url

    class Meta:
        model = Repo
        fields = ("id", "name", "url", "organization")

