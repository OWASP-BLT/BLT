from django.core.management.base import BaseCommand

from website.models import UserProfile


class Command(BaseCommand):
    help = 'Update contributor club memberships for all users'

    def handle(self, *args, **options):
        self.stdout.write('Starting club membership updates...')
        
        # Get all users with GitHub profiles
        users_with_github = UserProfile.objects.exclude(github_url="").exclude(github_url=None)
        user_count = users_with_github.count()
        
        self.stdout.write(f'Found {user_count} users with GitHub profiles')
        self.stdout.write('-' * 50)
        
        updated_count = 0
        for index, user_profile in enumerate(users_with_github, 1):
            self.stdout.write(f'[{index}/{user_count}] Updating clubs for: {user_profile.user.username}')
            
            try:
                user_profile.calculate_club_memberships()
                updated_count += 1
                
                # Show current club status
                clubs = []
                if user_profile.weekly_club_member:
                    clubs.append('Weekly')
                if user_profile.monthly_club_member:
                    clubs.append('Monthly') 
                if user_profile.hundred_club_member:
                    clubs.append('100 Club')
                elif user_profile.fifty_club_member:
                    clubs.append('50 Club')
                elif user_profile.ten_club_member:
                    clubs.append('10 Club')
                    
                club_status = ', '.join(clubs) if clubs else 'No clubs'
                self.stdout.write(f'  Clubs: {club_status} ({user_profile.merged_pr_count} merged PRs)')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error updating clubs for {user_profile.user.username}: {str(e)}')
                )
                
        self.stdout.write('-' * 50)
        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated club memberships for {updated_count}/{user_count} users!')
        )