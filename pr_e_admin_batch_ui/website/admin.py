from django.contrib import admin

from website.models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    actions = ["recalculate_freshness"]
    list_display = ("id", "name", "slug", "description", "created", "modified")
    search_fields = ["id", "name", "slug", "description"]

    def recalculate_freshness(self, request, queryset):
        count = 0
        for project in queryset:
            project.freshness = project.calculate_freshness()
            project.save(update_fields=["freshness"])
            project.log_freshness_summary()
            count += 1
        self.message_user(request, f"Recalculated freshness for {count} projects. See logs for summary.")

    recalculate_freshness.short_description = "Recalculate freshness (full)"


from website.models import Project

# ... (rest of admin.py content unchanged, up to line 1289)
