import time

from django.core.management.base import BaseCommand

from website.models import UserProfile
from website.github_verification import (
    award_github_linking_tokens,
    extract_github_username,
    verify_github_linkback,
)


class Command(BaseCommand):
    help = "Verify GitHub linkbacks for users who already have GitHub URLs and award tokens"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run without actually awarding tokens",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        
        # Find users with GitHub URLs who haven't received the reward yet
        profiles = UserProfile.objects.filter(
            github_url__isnull=False, github_linking_reward_given=False
        ).exclude(github_url="").select_related("user")
        
        self.stdout.write(f"Found {profiles.count()} profiles to check")
        
        verified_count = 0
        awarded_count = 0
        
        for profile in profiles:
            github_username = extract_github_username(profile.github_url)
            if not github_username:
                self.stdout.write(
                    self.style.WARNING(f"Invalid GitHub URL for {profile.user.username}: {profile.github_url}")
                )
                continue
            
            self.stdout.write(f"Checking {profile.user.username} ({github_username})...")
            
            verification_result = verify_github_linkback(github_username)
            
            if verification_result["verified"]:
                verified_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Verified linkback in {verification_result['found_in']}")
                )
                
                if not dry_run:
                    success = award_github_linking_tokens(profile.user)
                    if success:
                        awarded_count += 1
                        self.stdout.write(self.style.SUCCESS("  → Awarded 5 BACON tokens"))
                else:
                    self.stdout.write(self.style.WARNING("  → Would award 5 BACON tokens (dry-run)"))
            else:
                self.stdout.write(self.style.ERROR("✗ No BLT link found in GitHub profile"))
            
            # Rate limiting to avoid hitting GitHub API limits
            time.sleep(1)
        
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(f"Verified: {verified_count}/{profiles.count()}")
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"Awarded tokens to: {awarded_count} users"))
        else:
            self.stdout.write(self.style.WARNING("DRY RUN - No tokens were actually awarded"))
