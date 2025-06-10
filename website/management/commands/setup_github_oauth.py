from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sets up GitHub OAuth configuration in the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain", default=getattr(settings, "SITE_DOMAIN", "localhost:8000"), help="Domain for the site"
        )
        parser.add_argument("--name", default=getattr(settings, "SITE_NAME", "localhost"), help="Name for the site")

    def handle(self, *args, **options):
        # Check if SITE_ID is configured
        site_id = getattr(settings, "SITE_ID", None)
        if not site_id:
            self.stdout.write(self.style.ERROR("Missing required setting: SITE_ID"))
            return

        # First ensure we have a site configured
        site, created = Site.objects.get_or_create(
            id=site_id, defaults={"domain": options["domain"], "name": options["name"]}
        )
        if not created:
            site.domain = options["domain"]
            site.name = options["name"]
            site.save()

        self.stdout.write(self.style.SUCCESS(f"Site configured: {site.domain}"))

        # Set up GitHub OAuth
        github_key = getattr(settings, "SOCIAL_AUTH_GITHUB_KEY", None)
        github_secret = getattr(settings, "SOCIAL_AUTH_GITHUB_SECRET", None)

        if not github_key or not github_secret:
            self.stdout.write(
                self.style.ERROR("Missing required settings: SOCIAL_AUTH_GITHUB_KEY and/or SOCIAL_AUTH_GITHUB_SECRET")
            )
            return

        try:
            github_app = SocialApp.objects.get(provider="github")
            github_app.client_id = github_key
            github_app.secret = github_secret
            github_app.save()
            if site not in github_app.sites.all():
                github_app.sites.add(site)
            self.stdout.write(self.style.SUCCESS("Updated GitHub OAuth configuration"))
        except SocialApp.DoesNotExist:
            github_app = SocialApp.objects.create(
                provider="github", name="GitHub", client_id=github_key, secret=github_secret
            )
            github_app.sites.add(site)
            self.stdout.write(self.style.SUCCESS("Created GitHub OAuth configuration"))
