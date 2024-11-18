from django.contrib import admin
from django.contrib.auth.models import User
from django.template.defaultfilters import truncatechars
from django.utils import timezone
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from website.models import (
    IP,
    Bid,
    Blocked,
    ChatBotLog,
    Company,
    CompanyAdmin,
    Contribution,
    Domain,
    Hunt,
    HuntPrize,
    InviteFriend,
    Issue,
    IssueScreenshot,
    Monitor,
    Payment,
    Points,
    Project,
    Subscription,
    Suggestion,
    SuggestionVotes,
    Tag,
    TimeLog,
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


class CompanyAdminResource(resources.ModelResource):
    class Meta:
        model = CompanyAdmin


class CompanyResource(resources.ModelResource):
    class Meta:
        model = Company


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
        "company",
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
    search_fields = ["name", "company__name", "url"]


class CompanyUserAdmin(ImportExportModelAdmin):
    resource_class = CompanyAdminResource
    list_display = ("role", "user", "company", "domain", "is_active")


class SubscriptionAdmin(ImportExportModelAdmin):
    resource_class = SubscriptionResource
    list_display = (
        "name",
        "charge_per_month",
        "hunt_per_domain",
        "number_of_domains",
        "feature",
    )


class CompanyAdmins(ImportExportModelAdmin):
    resource_class = CompanyResource
    list_display = (
        "admin",
        "name",
        "url",
        "email",
        "twitter",
        "facebook",
        "created",
        "modified",
        "subscription",
    )


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


class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("recommender", "recommended_user", "created_at")
    search_fields = ("recommender__username", "recommended_user__username")


class UserAdmin(ImportExportModelAdmin):
    resource_class = UserResource
    list_display = (
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
        "is_active",
        "date_joined",
        "is_staff",
    )


class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "user_avatar",
        "get_title_display",
        "role",
        "description",
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
        "recommendation_count",
        "x_username",
        "linkedin_url",
        "github_url",
        "website_url",
        "discounted_hourly_rate",
    )

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

    def recommendation_count(self, obj):
        return obj.recommendations.count()


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


class SuggestionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "description", "up_votes", "down_votes")


class SuggestionVotesAdmin(admin.ModelAdmin):
    list_display = ("user", "suggestion", "up_vote", "down_vote")


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
        "homepage_url",
        "created",
        "modified",
    )
    search_fields = ["name", "description", "slug"]


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


admin.site.register(Project, ProjectAdmin)
admin.site.register(Bid, BidAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(Domain, DomainAdminPanel)
admin.site.register(Issue, IssueAdmin)
admin.site.register(Points, PointsAdmin)
admin.site.register(Hunt, HuntAdmin)
admin.site.register(CompanyAdmin, CompanyUserAdmin)
admin.site.register(Company, CompanyAdmins)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Wallet, WalletAdmin)
admin.site.register(Winner, WinnerAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(IssueScreenshot, IssueScreenshotAdmin)
admin.site.register(HuntPrize)
admin.site.register(ChatBotLog, ChatBotLogAdmin)
admin.site.register(Blocked, BlockedAdmin)
admin.site.register(Suggestion, SuggestionAdmin)
admin.site.register(SuggestionVotes, SuggestionVotesAdmin)
admin.site.register(TimeLog, TimeLogAdmin)
admin.site.register(Contribution, ContributionAdmin)
admin.site.register(InviteFriend)
admin.site.register(IP, IPAdmin)
admin.site.register(Transaction)
admin.site.register(Monitor, MonitorAdmin)
admin.site.register(Tag, TagAdmin)
