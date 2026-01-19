from urllib.parse import urlparse

from website.management.base import LoggedBaseCommand
from website.models import Organization


class Command(LoggedBaseCommand):
    help = "Populate github_org field from source_code field for organizations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing github_org values",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        overwrite = options["overwrite"]

        self.stdout.write(self.style.SUCCESS("Starting GitHub organization population..."))

        # Get organizations with source_code but no github_org (or all if overwrite)
        if overwrite:
            orgs = Organization.objects.filter(source_code__isnull=False).exclude(source_code="")
            self.stdout.write(f"Processing {orgs.count()} organizations (overwrite mode)...")
        else:
            orgs = Organization.objects.filter(source_code__isnull=False, github_org__isnull=True).exclude(
                source_code=""
            ) | Organization.objects.filter(source_code__isnull=False, github_org="").exclude(source_code="")
            self.stdout.write(f"Processing {orgs.count()} organizations without github_org...")

        updated_count = 0
        skipped_count = 0
        error_count = 0

        for org in orgs:
            try:
                github_org = self.extract_github_org(org.source_code)

                if github_org:
                    if dry_run:
                        self.stdout.write(
                            f"[DRY RUN] Would set '{org.name}' github_org to: {github_org} (from {org.source_code})"
                        )
                        updated_count += 1
                    else:
                        org.github_org = github_org
                        org.save(update_fields=["github_org"])
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✓ Updated '{org.name}' github_org to: {github_org} (from {org.source_code})"
                            )
                        )
                        updated_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(f"⚠ Could not extract GitHub org from '{org.source_code}' for '{org.name}'")
                    )
                    skipped_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Error processing '{org.name}': {str(e)}"))
                error_count += 1

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Summary:"))
        if dry_run:
            self.stdout.write(f"  Organizations that would be updated: {updated_count}")
        else:
            self.stdout.write(f"  Organizations updated: {updated_count}")
        self.stdout.write(f"  Organizations skipped: {skipped_count}")
        self.stdout.write(f"  Errors: {error_count}")
        self.stdout.write("=" * 60)

        if dry_run:
            self.stdout.write(self.style.WARNING("\nThis was a dry run. No changes were made."))
            self.stdout.write("Run without --dry-run to apply changes.")

    def extract_github_org(self, url):
        """
        Extract GitHub organization name from various GitHub URL formats.

        Supports:
        - https://github.com/org
        - https://github.com/org/
        - https://github.com/org/repo
        - https://github.com/org/repo/...
        - http://github.com/org
        - www.github.com/org
        - github.com/org
        """
        if not url:
            return None

        try:
            # Handle URLs without scheme
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            parsed = urlparse(url)

            # Check if it's a GitHub URL (strict host match)
            # Using hostname instead of netloc to avoid issues with ports
            hostname = parsed.hostname
            if not hostname:
                return None
            
            hostname = hostname.lower()
            # Only allow github.com or *.github.com subdomains
            if hostname != "github.com" and not hostname.endswith(".github.com"):
                return None

            # Extract path parts
            path_parts = [p for p in parsed.path.split("/") if p]

            # GitHub org is the first part of the path
            if path_parts:
                return path_parts[0]

            return None

        except Exception:
            return None
