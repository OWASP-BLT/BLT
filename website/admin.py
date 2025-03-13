from urllib.parse import urlparse

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.template.defaultfilters import truncatechars
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from website.models import (
    IP,
    Activity,
    BannedApp,
    Bid,
    Blocked,
    ChatBotLog,
    Contribution,
    Contributor,
    ContributorStats,
    Course,
    DailyStats,
    Domain,
    Enrollment,
    ForumCategory,
    ForumComment,
    ForumPost,
    ForumVote,
    GitHubIssue,
    GitHubReview,
    Hunt,
    HuntPrize,
    Integration,
    InviteFriend,
    Issue,
    IssueScreenshot,
    JoinRequest,
    Lecture,
    LectureStatus,
    Message,
    Monitor,
    Organization,
    OrganizationAdmin,
    OsshCommunity,
    Payment,
    Points,
    Post,
    PRAnalysisReport,
    Project,
    Queue,
    Rating,
    Repo,
    Room,
    Section,
    SlackBotActivity,
    SlackIntegration,
    Subscription,
    Tag,
    TimeLog,
    Trademark,
    TrademarkOwner,
    Transaction,
    UserProfile,
    Wallet,
    Winner,
)


class UserResource(resources.ModelResource):
    class Meta:
        model = User


class DomainResource(resources.ModelResource):
    class Meta:
        model = Domain


class SubscriptionResource(resources.ModelResource):
    class Meta:
        model = Subscription


class OrganizationAdminResource(resources.ModelResource):
    class Meta:
        model = OrganizationAdmin


class OrganizationResource(resources.ModelResource):
    class Meta:
        model = Organization


class WalletResource(resources.ModelResource):
    class Meta:
        model = Wallet


class WinnerResource(resources.ModelResource):
    class Meta:
        model = Winner


class PaymentResource(resources.ModelResource):
    class Meta:
        model = Payment


class WinnerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "hunt",
        "winner",
        "runner",
        "second_runner",
        "prize_distributed",
    )


class BidAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "issue_url",
        "pr_link",
        "amount_bch",
        "bch_address",
        "status",
        "created",
        "modified",
    )


class WalletAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "current_balance", "created")


class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "team", "created_at", "is_accepted")


class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "wallet", "value", "active")


class ImageInline(admin.TabularInline):
    model = IssueScreenshot
    extra = 1


class IssueAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "url",
        "domain",
        "description",
        "closed_by",
        "closed_date",
        "screenshot",
        "created",
        "modified",
    )
    search_fields = ["url", "description", "domain__name", "user__username"]
    inlines = [ImageInline]
    list_filter = ["domain", "user"]


class HuntAdmin(admin.ModelAdmin):
    list_display = (
        "domain",
        "url",
        "prize",
        "logo",
        "starts_on",
        "end_on",
        "plan",
        "created",
        "modified",
    )


class DomainAdminPanel(ImportExportModelAdmin):
    resource_class = DomainResource
    list_display = (
        "name",
        "get_organization",
        "url",
        "logo",
        "clicks",
        "color",
        "email",
        "email_event",
        "twitter",
        "facebook",
        "created",
        "modified",
    )
    search_fields = ["name", "organization__name", "url"]

    def get_organization(self, obj):
        return obj.organization.name if obj.organization else "N/A"

    get_organization.short_description = "Organization"


class OrganizationUserAdmin(ImportExportModelAdmin):
    resource_class = OrganizationAdminResource
    list_display = ("role", "user", "get_organization", "domain", "is_active")

    def get_organization(self, obj):
        return obj.organization.name if obj.organization else "N/A"

    get_organization.short_description = "Organization"


class SubscriptionAdmin(ImportExportModelAdmin):
    resource_class = SubscriptionResource
    list_display = (
        "name",
        "charge_per_month",
        "hunt_per_domain",
        "number_of_domains",
        "feature",
    )


class OrganizationAdmins(ImportExportModelAdmin):
    resource_class = OrganizationResource
    list_display = (
        "id",
        "name",
        "url",
        "get_url_icon",
        "is_active",
        "created",
        "modified",
    )
    list_display_links = ("id",)
    list_editable = ("name", "url", "is_active")
    search_fields = ("name", "url")
    list_filter = ("is_active",)
    ordering = ("-created",)

    def get_url_icon(self, obj):
        if obj.url:
            # just return the domain part of the url
            domain_part = urlparse(obj.url).netloc
            return mark_safe(f'<a href="{domain_part}" target="_blank"><i class="fas fa-external-link-alt"></i></a>')
        return ""

    get_url_icon.short_description = " "
    get_url_icon.allow_tags = True


class PointsAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "short_description",
        "domain",
        "score",
        "created",
        "modified",
    )

    def short_description(self, obj):
        return truncatechars(obj.issue, 100)


admin.site.unregister(User)


# class UserAdmin(ImportExportModelAdmin):
#     resource_class = UserResource
#     list_display = (
#         "id",
#         "username",
#         "email",
#         "first_name",
#         "last_name",
#         "is_active",
#         "date_joined",
#         "is_staff",
#     )


class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "user_email",
        "user_avatar",
        "get_title_display",
        "role",
        "short_description",
        "winnings",
        "issues_hidden",
        "btc_address",
        "bch_address",
        "eth_address",
        "follow_count",
        "upvote_count",
        "downvote_count",
        "saved_count",
        "flagged_count",
        "subscribed_domains_count",
        "subscribed_users_count",
        "x_username",
        "linkedin_url",
        "github_url",
        "website_url",
        "discounted_hourly_rate",
        "email_status",
        "email_last_event",
        "email_last_event_time",
        "email_click_count",
        "email_open_count",
        "email_spam_report",
        "email_unsubscribed",
    )

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "Email"

    def short_description(self, obj):
        return truncatechars(obj.description, 10)

    short_description.short_description = "Description"

    def follow_count(self, obj):
        return obj.follows.count()

    def upvote_count(self, obj):
        return obj.issue_upvoted.count()

    def downvote_count(self, obj):
        return obj.issue_downvoted.count()

    def saved_count(self, obj):
        return obj.issue_saved.count()

    def flagged_count(self, obj):
        return obj.issue_flaged.count()

    def subscribed_domains_count(self, obj):
        return obj.subscribed_domains.count()

    def subscribed_users_count(self, obj):
        return obj.subscribed_users.count()


class IssueScreenshotAdmin(admin.ModelAdmin):
    model = IssueScreenshot
    list_display = ("id", "issue__user", "issue_description", "issue", "image")

    def issue__user(self, obj):
        return obj.issue.user

    def issue_description(self, obj):
        return obj.issue.description


def block_ip(modeladmin, request, queryset):
    for ip in queryset:
        Blocked.objects.create(address=ip.address, count=ip.count, created=timezone.now())

    modeladmin.message_user(request, "Selected IPs have been blocked successfully.")


block_ip.short_description = "Block selected IPs"


def unblock_ip(modeladmin, request, queryset):
    for ip in queryset:
        Blocked.objects.filter(ip=ip.address).delete()
    modeladmin.message_user(request, "Selected IPs have ben unblocked successfully")


unblock_ip.short_description = "Unblock selected IPs"


def block_user_agent(modeladmin, request, queryset):
    for ip in queryset:
        Blocked.objects.create(user_agent_string=ip.agent, count=ip.count, created=timezone.now())

    modeladmin.message_user(request, "Selected UserAgent have been blocked successfully.")


block_user_agent.short_description = "Block selected UserAgent"


def unblock_user_agent(modeladmin, request, queryset):
    for ip in queryset:
        Blocked.objects.filter(user_agent_string=ip.agent).delete()

    modeladmin.message_user(request, "Selected UserAgent have been unblocked successfully.")


unblock_user_agent.short_description = "Unblock selected UserAgent"


# Custom filter for IP address ranges
class IPAddressRangeFilter(SimpleListFilter):
    title = "IP Address Range"
    parameter_name = "ip_range"

    def lookups(self, request, model_admin):
        return (
            ("internal", "Internal (127.0.0.1)"),
            ("local", "Local (192.168.x.x)"),
            ("vpn", "VPN (10.x.x.x)"),
            ("ipv6", "IPv6"),
        )

    def queryset(self, request, queryset):
        if self.value() == "internal":
            return queryset.filter(address__startswith="127.0.0.1")
        if self.value() == "local":
            return queryset.filter(address__startswith="192.168.")
        if self.value() == "vpn":
            return queryset.filter(address__startswith="10.")
        if self.value() == "ipv6":
            return queryset.filter(address__contains=":")
        return queryset


class IPAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "address",
        "user",
        "issuenumber",
        "count",
        "created",
        "agent",
        "path",
        "method",
        "referer",
    )

    search_fields = ["address", "user", "agent", "path", "method", "referer"]
    list_filter = ["method", "created", IPAddressRangeFilter]
    date_hierarchy = "created"

    actions = [block_ip, unblock_ip, block_user_agent, unblock_user_agent]


class MonitorAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "url",
        "keyword",
        "created",
        "modified",
        "last_checked_time",
        "status",
        "user",
    )


class ChatBotLogAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "answer", "created")


class ForumPostAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "description", "up_votes", "down_votes", "status", "created")
    list_filter = ("status", "category")
    search_fields = ("title", "description", "user__username")


class ForumVoteAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "up_vote", "down_vote", "created")
    list_filter = ("up_vote", "down_vote")
    search_fields = ("user__username", "post__title")


class ForumCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "created")
    search_fields = ("name", "description")


class ForumCommentAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "content", "created", "last_modified")
    list_filter = ("created", "last_modified")
    search_fields = ("content", "user__username", "post__title")


class BlockedAdmin(admin.ModelAdmin):
    list_display = (
        "address",
        "reason_for_block",
        "ip_network",
        "user_agent_string",
        "count",
        "created",
        "modified",
    )


class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "slug",
        "description",
        "created",
        "modified",
    )
    search_fields = ["name", "description", "slug"]


class RepoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "description",
        "created",
        "modified",
    )
    search_fields = ["name", "description"]


class ContributorAdmin(admin.ModelAdmin):
    list_display = ("name", "github_id", "created")
    search_fields = ["name", "github_id"]


class ContributorStatsAdmin(admin.ModelAdmin):
    list_display = ("contributor", "repo", "date", "granularity")
    search_fields = ["contributor", "repo"]


class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created")
    prepopulated_fields = {"slug": ("name",)}


class TimeLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "start_time",
        "end_time",
        "duration",
        "github_issue_url",
        "created",
    )


class ContributionAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "description", "status", "created", "txid")
    list_filter = ["status", "user"]
    search_fields = ["title", "description", "user__username"]
    date_hierarchy = "created"


class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "created_at", "image")
    prepopulated_fields = {"slug": ("title",)}


class GitHubIssueAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_profile",
        "contributor",
        "type",
        "title",
        "state",
        "is_merged",
        "created_at",
        "merged_at",
        "updated_at",
        "url",
        "p2p_amount_usd",
        "p2p_amount_bch",
        "sent_by_user",
        "p2p_payment_created_at",
        "bch_tx_id",
    )
    list_filter = [
        "type",
        "state",
        "is_merged",
        "user_profile",
        "contributor",
        "sent_by_user",
        "repo",
    ]
    search_fields = [
        "title",
        "url",
        "user_profile__user__username",
        "contributor__name",
        "bch_tx_id",
    ]
    date_hierarchy = "created_at"


class GitHubReviewAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reviewer",
        "state",
        "submitted_at",
        "pull_request",
        "url",
    )
    list_filter = [
        "state",
        "reviewer",
    ]
    search_fields = [
        "reviewer__user__username",
        "url",
    ]
    date_hierarchy = "submitted_at"


class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "thread", "username", "content", "timestamp")
    list_filter = ("room", "timestamp")
    search_fields = ("username", "content")
    date_hierarchy = "timestamp"


class ThreadAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created", "modified")
    search_fields = ("name",)


class SlackBotActivityAdmin(admin.ModelAdmin):
    list_display = (
        "workspace_name",
        "activity_type",
        "user_id",
        "success",
        "created",
    )
    list_filter = ("activity_type", "success", "workspace_name")
    search_fields = ("workspace_name", "user_id", "error_message")
    readonly_fields = ("created",)
    ordering = ("-created",)


class RoomAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "type", "admin", "created_at")
    list_filter = ("type", "created_at")
    search_fields = ("name", "description", "admin__username")
    date_hierarchy = "created_at"


class DailyStatsAdmin(admin.ModelAdmin):
    list_display = ("name", "value", "created", "modified")
    search_fields = ["name", "value"]
    list_filter = ["created", "modified"]
    readonly_fields = ["created", "modified"]
    ordering = ["-modified"]


class QueueAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "short_message",
        "image",
        "created",
        "modified",
        "launched",
        "launched_at",
        "txid",
        "url_link",
    )
    list_filter = ("launched", "created", "modified")
    search_fields = ("message", "txid")
    readonly_fields = ("created", "modified")
    actions = ["mark_as_launched"]

    def short_message(self, obj):
        return truncatechars(obj.message, 50)

    short_message.short_description = "Message"

    def url_link(self, obj):
        if obj.url:
            return format_html('<a href="{}" target="_blank">View</a>', obj.url)
        return "-"

    url_link.short_description = "URL"

    def mark_as_launched(self, request, queryset):
        now = timezone.now()
        count = 0
        for queue_item in queryset:
            if not queue_item.launched:
                queue_item.launched = True
                queue_item.launched_at = now
                queue_item.save()
                count += 1
        self.message_user(request, f"{count} queue items marked as launched.")

    mark_as_launched.short_description = "Mark selected items as launched"


admin.site.register(Project, ProjectAdmin)
admin.site.register(Repo, RepoAdmin)
admin.site.register(Contributor, ContributorAdmin)
admin.site.register(ContributorStats, ContributorStatsAdmin)
admin.site.register(Bid, BidAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(Domain, DomainAdminPanel)
admin.site.register(Issue, IssueAdmin)
admin.site.register(Points, PointsAdmin)
admin.site.register(Hunt, HuntAdmin)
admin.site.register(OrganizationAdmin, OrganizationUserAdmin)
admin.site.register(Organization, OrganizationAdmins)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Wallet, WalletAdmin)
admin.site.register(Winner, WinnerAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(IssueScreenshot, IssueScreenshotAdmin)
admin.site.register(HuntPrize)
admin.site.register(ChatBotLog, ChatBotLogAdmin)
admin.site.register(Blocked, BlockedAdmin)
admin.site.register(ForumPost, ForumPostAdmin)
admin.site.register(ForumVote, ForumVoteAdmin)
admin.site.register(ForumCategory, ForumCategoryAdmin)
admin.site.register(ForumComment, ForumCommentAdmin)
admin.site.register(TimeLog, TimeLogAdmin)
admin.site.register(Contribution, ContributionAdmin)
admin.site.register(InviteFriend)
admin.site.register(IP, IPAdmin)
admin.site.register(Transaction)
admin.site.register(Monitor, MonitorAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Integration)
admin.site.register(SlackIntegration)
admin.site.register(Activity)
admin.site.register(PRAnalysisReport)
admin.site.register(Post, PostAdmin)
admin.site.register(Trademark)
admin.site.register(TrademarkOwner)
admin.site.register(OsshCommunity)
admin.site.register(Lecture)
admin.site.register(LectureStatus)
admin.site.register(Course)
admin.site.register(Section)
admin.site.register(Enrollment)
admin.site.register(Rating)
admin.site.register(GitHubIssue, GitHubIssueAdmin)
admin.site.register(GitHubReview, GitHubReviewAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(SlackBotActivity, SlackBotActivityAdmin)
admin.site.register(Room, RoomAdmin)
admin.site.register(DailyStats, DailyStatsAdmin)
admin.site.register(Queue, QueueAdmin)
admin.site.register(JoinRequest, JoinRequestAdmin)


@admin.register(BannedApp)
class BannedAppAdmin(admin.ModelAdmin):
    list_display = ("app_name", "country_name", "country_code", "app_type", "ban_date", "is_active")
    list_filter = ("app_type", "is_active", "ban_date")
    search_fields = ("country_name", "country_code", "app_name", "ban_reason")
    date_hierarchy = "ban_date"
    ordering = ("country_name", "app_name")

    fieldsets = (
        ("App Information", {"fields": ("app_name", "app_type")}),
        ("Country Information", {"fields": ("country_name", "country_code")}),
        ("Ban Details", {"fields": ("ban_reason", "ban_date", "source_url", "is_active")}),
    )
