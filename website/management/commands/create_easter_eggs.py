from django.core.management.base import BaseCommand

from website.models import EasterEgg


class Command(BaseCommand):
    help = "Creates initial Easter eggs for the site"

    def handle(self, *args, **options):
        easter_eggs = [
            {
                "name": "Konami Code",
                "code": "konami-code",
                "description": "The classic Konami code! ↑ ↑ ↓ ↓ ← → ← → B A",
                "reward_type": "fun",
                "reward_amount": 0,
                "max_claims_per_user": 1,
            },
            {
                "name": "Secret Logo",
                "code": "secret-logo",
                "description": "Found by clicking the logo 7 times rapidly!",
                "reward_type": "fun",
                "reward_amount": 0,
                "max_claims_per_user": 1,
            },
            {
                "name": "Footer Tap Master",
                "code": "footer-tap",
                "description": "Tap the footer 5 times to reveal this secret!",
                "reward_type": "fun",
                "reward_amount": 0,
                "max_claims_per_user": 1,
            },
            {
                "name": "Secret BACON",
                "code": "secret-bacon",
                "description": "The ultimate secret! Type 'bacon' then find and click the glowing element. Rewards actual BACON tokens!",
                "reward_type": "bacon",
                "reward_amount": 10,
                "max_claims_per_user": 1,
            },
            {
                "name": "Lucky Tap",
                "code": "lucky-tap",
                "description": "Found by random double-tap (mobile only) - you got lucky!",
                "reward_type": "fun",
                "reward_amount": 0,
                "max_claims_per_user": 1,
            },
            {
                "name": "Four Corners Explorer",
                "code": "four-corners",
                "description": "Click all four corners of the screen to discover this!",
                "reward_type": "fun",
                "reward_amount": 0,
                "max_claims_per_user": 1,
            },
            {
                "name": "Speed Scroller",
                "code": "speed-scroller",
                "description": "Scroll to the bottom of the page 3 times in 5 seconds!",
                "reward_type": "fun",
                "reward_amount": 0,
                "max_claims_per_user": 1,
            },
        ]

        created_count = 0
        updated_count = 0

        for egg_data in easter_eggs:
            egg, created = EasterEgg.objects.update_or_create(
                code=egg_data["code"],
                defaults={
                    "name": egg_data["name"],
                    "description": egg_data["description"],
                    "reward_type": egg_data["reward_type"],
                    "reward_amount": egg_data["reward_amount"],
                    "max_claims_per_user": egg_data["max_claims_per_user"],
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Created Easter egg: {egg.name}")
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f"Updated Easter egg: {egg.name}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTotal: {created_count} created, {updated_count} updated"
            )
        )
