from django.contrib import admin

from website.models import Issue, Points, Hunt, Domain
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

class IssueAdmin(admin.ModelAdmin):
    list_display = ('user','url','domain','description','screenshot','created','modified')

class HuntAdmin(admin.ModelAdmin):
    list_display = ('user','url','prize','logo','plan','created','modified')

class DomainAdmin(admin.ModelAdmin):
    list_display = ('name','url','logo','clicks','color','email','twitter','facebook','created','modified')

class PointsAdmin(admin.ModelAdmin):
    list_display = ('user','issue','domain','score','created','modified')

admin.site.unregister(User)

UserAdmin.list_display = ('id','username','email', 'first_name', 'last_name', 'is_active', 'date_joined', 'is_staff')
    
admin.site.register(User, UserAdmin)

admin.site.register(Domain, DomainAdmin)

admin.site.register(Issue, IssueAdmin)
admin.site.register(Points, PointsAdmin)
admin.site.register(Hunt, HuntAdmin)