from django.contrib import admin

from .models import Comment


class MyCommentsAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "get_related_object", "text", "created_date")

    def get_related_object(self, obj):
        return obj.content_object

    get_related_object.short_description = "Related Object"


admin.site.register(Comment, MyCommentsAdmin)

