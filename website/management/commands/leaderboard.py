from django.contrib.auth.models import User

from website.management.base import LoggedBaseCommand
from website.models import Issue, UserProfile


class Command(LoggedBaseCommand):
    help = "Update user based on number of bugs"

    def handle(self, *args, **options):
        all_user_prof = UserProfile.objects.all()
        all_user = User.objects.all()
        for user_ in all_user:
            user_prof = UserProfile.objects.get(user=user_)
            total_issues = Issue.objects.filter(user=user_).count()
            if total_issues <= 10:
                user_prof.title = 1
            elif total_issues <= 50:
                user_prof.title = 2
            elif total_issues <= 200:
                user_prof.title = 3
            else:
                user_prof.title = 4

            user_prof.save()

        return str("All users updated.")

