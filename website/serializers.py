from django.db.models import Sum
from rest_framework import serializers

from website.models import (
    ActivityLog,
    Bounty,
    Contributor,
    Domain,
    Hunt,
    HuntPrize,
    Issue,
    IssueScreenshot,
    Job,
    Organization,
    Points,
    Project,
    Repo,
    SearchHistory,
    Tag,
    TimeLog,
    Trademark,
    TrademarkOwner,
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


class BugHuntPrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HuntPrize
        fields = "__all__"


class BugHuntSerializer(serializers.ModelSerializer):
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


class JobSerializer(serializers.ModelSerializer):
    """
    Serializer for Job model
    """

    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_logo = serializers.ImageField(source="organization.logo", read_only=True)
    posted_by_username = serializers.CharField(source="posted_by.username", read_only=True)

    class Meta:
        model = Job
        fields = (
            "id",
            "organization",
            "organization_name",
            "organization_logo",
            "title",
            "description",
            "requirements",
            "location",
            "job_type",
            "salary_range",
            "is_public",
            "status",
            "expires_at",
            "application_email",
            "application_url",
            "application_instructions",
            "posted_by",
            "posted_by_username",
            "created_at",
            "updated_at",
            "views_count",
        )
        read_only_fields = ("id", "posted_by", "created_at", "updated_at", "views_count")


class JobPublicSerializer(serializers.ModelSerializer):
    """
    Public serializer for Job model (limited fields for public API)
    """

    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_logo = serializers.ImageField(source="organization.logo", read_only=True)

    class Meta:
        model = Job
        fields = (
            "id",
            "organization_name",
            "organization_logo",
            "title",
            "description",
            "requirements",
            "location",
            "job_type",
            "salary_range",
            "expires_at",
            "application_email",
            "application_url",
            "application_instructions",
            "created_at",
            "views_count",
        )


class TrademarkOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrademarkOwner
        fields = [
            "name",
            "address1",
            "address2",
            "city",
            "state",
            "country",
            "postcode",
            "owner_label",
            "legal_entity_type_label",
        ]


class TrademarkSerializer(serializers.ModelSerializer):
    owners = TrademarkOwnerSerializer(many=True, read_only=True)

    class Meta:
        model = Trademark
        fields = [
            "keyword",
            "registration_number",
            "serial_number",
            "status_label",
            "filing_date",
            "registration_date",
            "expiration_date",
            "description",
            "owners",
        ]


class SearchHistorySerializer(serializers.ModelSerializer):
    """Serializer for SearchHistory model"""

    class Meta:
        model = SearchHistory
        fields = ["id", "query", "search_type", "timestamp", "result_count"]
        read_only_fields = ["id", "timestamp"]

class BountySerializer(serializers.ModelSerializer):
    issue_id = serializers.PrimaryKeyRelatedField(
        source="issue",
        queryset=Issue.objects.all(),
        write_only=True,
    )
    issue = serializers.StringRelatedField(read_only=True)
    sponsor_username = serializers.CharField(
        source="github_sponsor_username",
        read_only=True,
    )
    sponsor_id = serializers.IntegerField(source="sponsor.id", read_only=True)

    class Meta:
        model = Bounty
        fields = [
            "id",
            "issue",
            "issue_id",
            "sponsor_id",
            "sponsor_username",
            "amount",
            "github_issue_url",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "created_at",
            "updated_at",
            "sponsor_id",
            "sponsor_username",
        ]
        extra_kwargs = {
            "issue": {"required": False, "allow_null": True},
        }

    def validate_amount(self, value):
        """
        Allow creating a bounty with only github_issue_url + amount + github_username.
        'issue' is optional; we can link it later if needed.
        """
        if not value.get("github_issue_url"):
            raise serializers.ValidationError(
                {"github_issue_url": "This field is required."}
            )
        if value <= 0:
            raise serializers.ValidationError("Bounty amount must be positive.")
        if value > 100000:  # arbitrary reasonable max, tweak as needed
            raise serializers.ValidationError("Bounty amount is unreasonably large.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        sponsor = request.user
        validated_data["sponsor"] = sponsor

        if "github_sponsor_username" not in validated_data:
            # Fallback: use a profile field or username; tweak as needed
            validated_data["github_sponsor_username"] = getattr(
                sponsor, "github_username", sponsor.username
            )

        bounty = super().create(validated_data)
        return bounty