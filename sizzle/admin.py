from django.contrib import admin

from .models import DailyStatusReport, ReminderSettings, TimeLog


@admin.register(TimeLog)
class TimelogAdmin(admin.ModelAdmin):
    pass


@admin.register(DailyStatusReport)
class DailyStatusReportAdmin(admin.ModelAdmin):
    pass


@admin.register(ReminderSettings)
class ReminderSettingsAdmin(admin.ModelAdmin):
    pass
