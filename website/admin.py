from django.contrib import admin

from website.models import Issue, Points, Hunt

class IssueAdmin(admin.ModelAdmin):
    list_display = ('user','url','description','screenshot','created','modified')

class HuntAdmin(admin.ModelAdmin):
    list_display = ('user','url','prize','logo','plan','created','modified')

admin.site.register(Issue, IssueAdmin)
admin.site.register(Points)
admin.site.register(Hunt, HuntAdmin)