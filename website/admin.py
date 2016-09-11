from django.contrib import admin

from website.models import Issue, Points, Hunt
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

class IssueAdmin(admin.ModelAdmin):
    list_display = ('user','url','description','screenshot','created','modified')

class HuntAdmin(admin.ModelAdmin):
    list_display = ('user','url','prize','logo','plan','created','modified')


admin.site.unregister(User)

UserAdmin.list_display = ('id','username','email', 'first_name', 'last_name', 'is_active', 'date_joined', 'is_staff')
    
admin.site.register(User, UserAdmin)

admin.site.register(Issue, IssueAdmin)
admin.site.register(Points)
admin.site.register(Hunt, HuntAdmin)