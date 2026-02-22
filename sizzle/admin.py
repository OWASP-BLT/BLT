from django.contrib import admin

from .models import DailyStatusReport


@admin.register(DailyStatusReport)
class DailyStatusReportAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "current_mood", "goal_accomplished")
    list_filter = ("date", "goal_accomplished")
