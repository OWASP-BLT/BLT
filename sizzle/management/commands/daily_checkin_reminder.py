from django.core.management.base import BaseCommand

# Import from website app since these models haven't been migrated yet
from website.models import Notification, UserProfile


class Command(BaseCommand):
    help = "Sends daily check-in reminders to users in organizations with check-ins enabled"

    def handle(self, *args, **options):
        userprofiles_with_checkins = UserProfile.objects.filter(team__check_ins_enabled=True)
        notifications = [
            Notification(
                user=userprofile.user,
                message=f"This is a reminder to add your daily check-in for {userprofile.team.name}",
                notification_type="reminder",
                link="/add-sizzle-checkin/",
            )
            for userprofile in userprofiles_with_checkins
        ]
        Notification.objects.bulk_create(notifications)
        self.stdout.write(
            self.style.SUCCESS(f"Sent check-in reminder notifications to {len(userprofiles_with_checkins)} users.")
        )