from django.db.models import Count

from website.management.base import LoggedBaseCommand
from website.models import UserProfile


class Command(LoggedBaseCommand):
    help = "Update user based on number of bugs"

    def handle(self, *args, **options):
        # Annotate issue count directly on UserProfile to avoid N+1 queries
        profiles = UserProfile.objects.annotate(total_issues=Count("user__issue"))

        for user_prof in profiles:
            total_issues = user_prof.total_issues
            if total_issues <= 10:
                user_prof.title = 1
            elif total_issues <= 50:
                user_prof.title = 2
            elif total_issues <= 200:
                user_prof.title = 3
            else:
                user_prof.title = 4

        UserProfile.objects.bulk_update(profiles, ["title"])

        return str("All users updated.")
