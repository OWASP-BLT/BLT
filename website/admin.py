from django.contrib import admin

from website.models import Issue, Points, Hunt, Domain
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.template.defaultfilters import truncatechars

from import_export import resources
from import_export.admin import ImportExportModelAdmin

class UserResource(resources.ModelResource):

    class Meta:
        model = User

class DomainResource(resources.ModelResource):

    class Meta:
        model = Domain

class IssueAdmin(admin.ModelAdmin):
    list_display = ('user','url','domain','description','screenshot','created','modified')

class HuntAdmin(admin.ModelAdmin):
    list_display = ('user','url','prize','logo','plan','created','modified')

class DomainAdmin(ImportExportModelAdmin):
    resource_class = DomainResource
    list_display = ('name','url','logo','clicks','color','email','email_event','twitter','facebook','created','modified')

class PointsAdmin(admin.ModelAdmin):
    list_display = ('user','short_description','domain','score','created','modified')
    def short_description(self, obj):
        return truncatechars(obj.issue, 100)

admin.site.unregister(User)

class UserAdmin(ImportExportModelAdmin):
	resource_class = UserResource
	list_display = ('id','username','email', 'first_name', 'last_name', 'is_active', 'date_joined', 'is_staff')
    
admin.site.register(User, UserAdmin)

admin.site.register(Domain, DomainAdmin)

admin.site.register(Issue, IssueAdmin)
admin.site.register(Points, PointsAdmin)
admin.site.register(Hunt, HuntAdmin)