from django.utils import timezone

from website.management.base import LoggedBaseCommand
from website.models import Comment, Issue, User


class Command(LoggedBaseCommand):
    help = "Update user statistics"

    def handle(self, *args, **options):
        # Get all users
        users = User.objects.all()

        for user in users:
            # Count issues and comments
            issue_count = Issue.objects.filter(user=user).count()
            comment_count = Comment.objects.filter(user=user).count()

            # Update user stats
            user.total_issues = issue_count
            user.total_comments = comment_count
            user.last_updated = timezone.now()
            user.save()

            self.stdout.write(f"Updated stats for user: {user.username}")

        self.stdout.write("User statistics update completed")
