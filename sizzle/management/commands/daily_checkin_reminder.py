from sizzle.management.base import SizzleBaseCommand
from sizzle.utils.model_loader import get_userprofile_model, get_notification_model
from sizzle.conf import SIZZLE_DAILY_CHECKINS_ENABLED


class Command(SizzleBaseCommand):
    help = "Sends daily check-in reminders to users in organizations with check-ins enabled"

    def handle(self, *args, **options):
        # Check if daily check-ins are enabled
        if not SIZZLE_DAILY_CHECKINS_ENABLED:
            self.log_warning('Daily check-ins are disabled in settings')
            return

        # Get models dynamically
        UserProfile = get_userprofile_model()
        if UserProfile is None:
            self.log_error(
                'UserProfile model not configured or available. '
                'Check SIZZLE_USERPROFILE_MODEL setting.'
            )
            return

        Notification = get_notification_model()
        if Notification is None:
            self.log_error(
                'Notification model not configured or available. '
                'Check SIZZLE_NOTIFICATION_MODEL setting.'
            )
            return

        try:
            # Check if UserProfile has the required fields
            userprofiles_with_checkins = UserProfile.objects.filter(team__check_ins_enabled=True)
            
            notifications = []
            for userprofile in userprofiles_with_checkins:
                try:
                    notifications.append(
                        Notification(
                            user=userprofile.user,
                            message=f"This is a reminder to add your daily check-in for {userprofile.team.name}",
                            notification_type="reminder",
                            link="/add-sizzle-checkin/",
                        )
                    )
                except Exception as e:
                    self.log_error(f'Error creating notification for user {userprofile.user.username}: {e}')
                    continue

            if notifications:
                try:
                    Notification.objects.bulk_create(notifications)
                    self.log_info(f"Sent check-in reminder notifications to {len(notifications)} users.")
                except Exception as e:
                    self.log_error(f'Error bulk creating notifications: {e}')
            else:
                self.log_info("No users found with check-ins enabled or no notifications to create.")

        except Exception as e:
            self.log_error(f'Error in daily check-in reminder process: {e}')
            # Check if it's a field-related error and provide helpful guidance
            if 'team' in str(e) or 'check_ins_enabled' in str(e):
                self.log_error(
                    'It appears your UserProfile model does not have the expected fields. '
                    'Sizzle expects UserProfile to have a "team" field with "check_ins_enabled" attribute.'
                )
            raise