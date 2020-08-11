from django.contrib import admin
from django.contrib.auth.models import User
from django.template.defaultfilters import truncatechars
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from website.models import Issue, Points, Hunt, Domain, UserProfile, Subscription, CompanyAdmin, Company


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


class IssueAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'url', 'domain', 'description', 'closed_by', 'closed_date', 'screenshot', 'created', 'modified')


class HuntAdmin(admin.ModelAdmin):
    list_display = ('domain', 'url', 'prize', 'logo', 'starts_on','end_on', 'plan', 'created', 'modified')


class DomainAdminPanel(ImportExportModelAdmin):
    resource_class = DomainResource
    list_display = (
        'name', 'company', 'url', 'logo', 'clicks', 'color', 'email', 'email_event', 'twitter', 'facebook', 'created', 'modified')

class CompanyUserAdmin(ImportExportModelAdmin):
    resource_class = CompanyAdminResource
    list_display = (
        'role', 'user', 'company', 'domain', 'is_active')

class SubscriptionAdmin(ImportExportModelAdmin):
    resource_class = SubscriptionResource
    list_display = (
        'name', 'charge_per_month', 'hunt_per_domain', 'number_of_domains', 'feature')


class CompanyAdmins(ImportExportModelAdmin):
    resource_class = CompanyResource
    list_display = (
        'admin', 'name', 'url', 'email', 'twitter', 'facebook', 'created', 'modified', 'subscription')


class PointsAdmin(admin.ModelAdmin):
    list_display = ('user', 'short_description', 'domain', 'score', 'created', 'modified')

    def short_description(self, obj):
        return truncatechars(obj.issue, 100)


admin.site.unregister(User)


class UserAdmin(ImportExportModelAdmin):
    resource_class = UserResource
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined', 'is_staff')


admin.site.register(UserProfile)
admin.site.register(User, UserAdmin)

admin.site.register(Domain, DomainAdminPanel)

admin.site.register(Issue, IssueAdmin)
admin.site.register(Points, PointsAdmin)
admin.site.register(Hunt, HuntAdmin)

admin.site.register(CompanyAdmin, CompanyUserAdmin)
admin.site.register(Company, CompanyAdmins)

admin.site.register(Subscription, SubscriptionAdmin)