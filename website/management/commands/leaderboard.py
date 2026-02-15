from django.db.models import Count

from website.management.base import LoggedBaseCommand
from website.models import UserProfile


class Command(LoggedBaseCommand):
    help = "Update user based on number of bugs"

    def handle(self, *args, **options):
        profiles = UserProfile.objects.annotate(total_issues=Count("user__issue"))

        for profile in profiles:
            total_issues = profile.total_issues
            if total_issues <= 10:
                profile.title = 1
            elif total_issues <= 50:
                profile.title = 2
            elif total_issues <= 200:
                profile.title = 3
            else:
                profile.title = 4

            profile.save(update_fields=["title"])

        return "All users updated."
