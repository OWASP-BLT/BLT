from django.db import IntegrityError, transaction
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
    SecurityIncident,
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

    total_stars = serializers.IntegerField(read_only=True)
    total_forks = serializers.IntegerField(read_only=True)

    external_links = serializers.JSONField(required=False)
    project_visit_count = serializers.IntegerField(required=False)

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
    """
    Serializer for creating and retrieving Bounty objects.

    This serializer supports:
    - Creating a bounty with or without linking an Issue immediately.
    - Automatically attaching the sponsor (request.user).
    - Returning sponsor metadata and issue metadata.
    - Validating bounty amount for sensible ranges.
    """

    issue_id = serializers.PrimaryKeyRelatedField(
        source="issue",
        queryset=Issue.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
        help_text="Optional issue ID to link this bounty to.",
    )
    issue = serializers.StringRelatedField(read_only=True)
    sponsor_username = serializers.CharField(
        source="github_sponsor_username",
        read_only=True,
    )
    sponsor_id = serializers.IntegerField(source="sponsor.id", read_only=True)

    github_username = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="GitHub username of the sponsor (used for display/attribution).",
    )

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
            "github_username",
        ]
        read_only_fields = [
            "id",
            "status",
            "created_at",
            "updated_at",
            "sponsor_id",
            "sponsor_username",
        ]

    def validate_amount(self, value):
        """
        Validate the bounty amount.
        Ensures:
        - The amount is positive.
        - The amount is not excessively large.
        """
        if value <= 0:
            raise serializers.ValidationError("Bounty amount must be positive.")
        if value > 100000:
            raise serializers.ValidationError("Bounty amount is unreasonably large.")
        return value

    def create(self, validated_data):
        """
        Create a new Bounty instance.

        - Automatically sets the sponsor to the authenticated user.
        - Uses github_username (from Slack / BLT-Action) for attribution when given.
        - Falls back to request.user's GitHub username / username.
        - If github_issue_url is present, attach (or create) an Issue so
        Bounty.issue is never NULL, using Issue.github_url as the key.
        """
        request = self.context["request"]
        sponsor = request.user
        validated_data["sponsor"] = sponsor

        # Pull out github_username if present (Slack / BLT-Action)
        github_username = validated_data.pop("github_username", "").strip()

        if github_username:
            # Explicit GitHub sponsor from caller → trust this for attribution
            validated_data["github_sponsor_username"] = github_username
        elif "github_sponsor_username" not in validated_data:
            # Fallback: use the API user's GitHub username / username
            validated_data["github_sponsor_username"] = getattr(
                sponsor,
                "github_username",
                sponsor.username,
            )

        github_issue_url = validated_data.get("github_issue_url")

        # Check for duplicate bounty
        if (
            github_issue_url
            and Bounty.objects.filter(
                sponsor=sponsor, github_issue_url=github_issue_url.rstrip("/"), status=Bounty.STATUS_PENDING
            ).exists()
        ):
            raise serializers.ValidationError("You already have a pending bounty for this issue.")
        if github_issue_url:
            # Use Issue.github_url as the canonical link to the GitHub issue.
            # IMPORTANT: do NOT pass any 'captcha' or 'user' kwargs here.
            normalized_url = github_issue_url.rstrip("/")
            validated_data["github_issue_url"] = normalized_url
            github_issue_url = normalized_url
            # Friendly pre-check (good error messages, fewer DB errors)
            if Bounty.objects.filter(
                sponsor=sponsor,
                github_issue_url=normalized_url,
                status=Bounty.STATUS_PENDING,
            ).exists():
                raise serializers.ValidationError("You already have a pending bounty for this issue.")
            issue_obj, _ = Issue.objects.get_or_create(
                github_url=github_issue_url,
                defaults={
                    "url": github_issue_url,
                    "description": f"GitHub issue: {github_issue_url}",
                    "is_hidden": True,
                },
            )
            validated_data["issue"] = issue_obj

        # DB-enforced uniqueness to handle concurrent requests safely
        try:
            with transaction.atomic():
                return super().create(validated_data)
        except IntegrityError as exc:
            # If another request slipped in and created the pending bounty first,
            # the unique constraint will fire; convert that into a clean API error.
            if "uniq_pending_bounty_per_sponsor_issue" in str(exc):
                raise serializers.ValidationError("You already have a pending bounty for this issue.")
            raise


class SecurityIncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityIncident
        fields = [
            "id",
            "title",
            "description",
            "severity",
            "status",
            "affected_systems",
            "created_at",
            "resolved_at",
        ]
        read_only_fields = ["id", "created_at", "resolved_at"]
