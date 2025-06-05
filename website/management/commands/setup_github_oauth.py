from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from django.conf import settings

class Command(BaseCommand):
    help = 'Sets up GitHub OAuth configuration in the database'

    def handle(self, *args, **options):
        # First ensure we have a site configured
        site, created = Site.objects.get_or_create(
            id=settings.SITE_ID,
            defaults={
                "domain": "localhost:8000",
                "name": "localhost"
            }
        )
        if not created:
            site.domain = "localhost:8000"
            site.name = "localhost"
            site.save()
            
        self.stdout.write(self.style.SUCCESS(f'Site configured: {site.domain}'))
        
        # Set up GitHub OAuth
        try:
            github_app = SocialApp.objects.get(provider="github")
            github_app.client_id = settings.SOCIAL_AUTH_GITHUB_KEY
            github_app.secret = settings.SOCIAL_AUTH_GITHUB_SECRET
            github_app.save()
            github_app.sites.add(site)
            self.stdout.write(self.style.SUCCESS('Updated GitHub OAuth configuration'))
        except SocialApp.DoesNotExist:
            github_app = SocialApp.objects.create(
                provider="github",
                name="GitHub",
                client_id=settings.SOCIAL_AUTH_GITHUB_KEY,
                secret=settings.SOCIAL_AUTH_GITHUB_SECRET
            )
            github_app.sites.add(site)
            self.stdout.write(self.style.SUCCESS('Created GitHub OAuth configuration'))
