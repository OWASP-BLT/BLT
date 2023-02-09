from django.contrib import admin

from .models import Comment


class MyCommentsAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "issue", "text", "created_date")


admin.site.register(Comment, MyCommentsAdmin)
