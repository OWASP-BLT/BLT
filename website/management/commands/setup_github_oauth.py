from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Setup GitHub OAuth credentials for django-allauth in production or development environments"

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            type=str,
            help="Optional domain to use for the site (e.g., blt.owasp.org)",
        )
        parser.add_argument(
            "--check-only",
            action="store_true",
            help="Only check the current configuration without making changes",
        )

    def handle(self, *args, **options):
        domain = options.get("domain")
        check_only = options.get("check_only", False)

        # Get GitHub credentials from settings
        github_client_id = settings.SOCIALACCOUNT_PROVIDERS.get("github", {}).get("CLIENT_ID", "")
        github_client_secret = settings.SOCIALACCOUNT_PROVIDERS.get("github", {}).get("SECRET", "")

        if not github_client_id or not github_client_secret:
            self.stdout.write(self.style.ERROR("GitHub credentials not found in settings"))
            return

        self.stdout.write(f"GitHub Client ID: {github_client_id[:4]}... (length: {len(github_client_id)})")
        self.stdout.write(f"GitHub Client Secret: {github_client_secret[:4]}... (length: {len(github_client_secret)})")

        # Get the callback URL from settings
        callback_url = settings.CALLBACK_URL_FOR_GITHUB
        self.stdout.write(f"Callback URL from settings: {callback_url}")

        # Get current site
        site = Site.objects.get_current()
        self.stdout.write(f"Current site: {site.domain}")

        # If domain is provided, update the site
        if domain and not check_only:
            old_domain = site.domain
            site.domain = domain
            site.name = domain
            site.save()
            self.stdout.write(self.style.SUCCESS(f"Updated site domain from {old_domain} to {domain}"))

        # Check if the GitHub app exists in the database
        social_app, created = SocialApp.objects.get_or_create(
            provider="github",
            defaults={"name": "GitHub", "client_id": github_client_id, "secret": github_client_secret, "key": ""},
        )

        if check_only:
            self.stdout.write(self.style.SUCCESS(f"GitHub OAuth app exists: {not created}"))
            self.stdout.write(
                f"Client ID in database: {social_app.client_id[:4]}... (length: {len(social_app.client_id)})"
            )
            self.stdout.write(f"Secret in database: {social_app.secret[:4]}... (length: {len(social_app.secret)})")
            self.stdout.write(f"Associated sites: {', '.join([s.domain for s in social_app.sites.all()])}")
            self.stdout.write(self.style.SUCCESS(f"Site '{site.domain}' association: {site in social_app.sites.all()}"))
            return

        if not created:
            # Update existing app with new credentials
            if social_app.client_id != github_client_id or social_app.secret != github_client_secret:
                social_app.client_id = github_client_id
                social_app.secret = github_client_secret
                social_app.save()
                self.stdout.write(self.style.SUCCESS("Updated existing GitHub OAuth app with new credentials"))
            else:
                self.stdout.write(self.style.SUCCESS("Existing GitHub OAuth app credentials are up to date"))
        else:
            self.stdout.write(self.style.SUCCESS("Created new GitHub OAuth app"))

        # Add site to the app
        if site not in social_app.sites.all():
            social_app.sites.add(site)
            self.stdout.write(self.style.SUCCESS(f"Added site '{site.domain}' to GitHub OAuth app"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Site '{site.domain}' already associated with GitHub OAuth app"))

        # Final settings check
        if not callback_url or domain not in callback_url:
            self.stdout.write(
                self.style.WARNING(
                    f"WARNING: The callback URL in settings ({callback_url}) does not match the site domain ({site.domain}).\n"
                    f"Consider updating CALLBACK_URL_FOR_GITHUB in settings to include: https://{site.domain}/accounts/github/login/callback/"
                )
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("GitHub OAuth setup complete!"))
        self.stdout.write(
            self.style.SUCCESS("IMPORTANT: Make sure your GitHub OAuth app has the following callback URL registered:")
        )
        self.stdout.write(self.style.SUCCESS(f"https://{site.domain}/accounts/github/login/callback/"))
