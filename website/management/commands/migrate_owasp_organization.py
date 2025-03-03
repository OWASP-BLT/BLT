import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from website.models import Organization

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migrates data from owasp-foundation organization to owasp organization"

    def handle(self, *args, **options):
        try:
            # Check if owasp-foundation organization exists
            try:
                source_org = Organization.objects.get(slug="owasp-foundation")
            except Organization.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING("The owasp-foundation organization does not exist. No migration needed.")
                )
                return

            # Check if owasp organization exists
            try:
                target_org = Organization.objects.get(slug="owasp")
            except Organization.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR("The target owasp organization does not exist. Please create it first.")
                )
                return

            # Start transaction to ensure data consistency
            with transaction.atomic():
                self.stdout.write(self.style.NOTICE("Starting migration from owasp-foundation to owasp..."))

                # Log the current state of both organizations
                self.stdout.write(f"Source organization (owasp-foundation): ID={source_org.id}, Name={source_org.name}")
                self.stdout.write(f"Target organization (owasp): ID={target_org.id}, Name={target_org.name}")

                # Fields to migrate (excluding id, slug, and created fields)
                fields_to_migrate = [
                    "admin",
                    "name",
                    "description",
                    "logo",
                    "url",
                    "email",
                    "twitter",
                    "matrix_url",
                    "slack_url",
                    "discord_url",
                    "gitter_url",
                    "zulipchat_url",
                    "element_url",
                    "facebook",
                    "subscription",
                    "is_active",
                    "trademark_count",
                    "trademark_check_date",
                    "team_points",
                    "tagline",
                    "license",
                    "categories",
                    "contributor_guidance_url",
                    "tech_tags",
                    "topic_tags",
                    "source_code",
                    "ideas_link",
                    "repos_updated_at",
                    "type",
                    "address_line_1",
                    "address_line_2",
                    "city",
                    "state",
                    "country",
                    "postal_code",
                    "latitude",
                    "longitude",
                ]

                # Copy data from source to target for each field
                for field in fields_to_migrate:
                    source_value = getattr(source_org, field)
                    if source_value:  # Only update if source has a value
                        self.stdout.write(f"Migrating field '{field}': {source_value}")
                        setattr(target_org, field, source_value)

                # Update modified timestamp
                target_org.modified = timezone.now()
                target_org.save()

                # Handle many-to-many relationships
                # Managers
                for manager in source_org.managers.all():
                    self.stdout.write(f"Adding manager: {manager.username}")
                    target_org.managers.add(manager)

                # Tags
                for tag in source_org.tags.all():
                    self.stdout.write(f"Adding tag: {tag.name}")
                    target_org.tags.add(tag)

                # Integrations
                for integration in source_org.integrations.all():
                    self.stdout.write(f"Adding integration: {integration}")
                    target_org.integrations.add(integration)

                # Update domains to point to the target organization
                domains_count = 0
                for domain in source_org.domain_set.all():
                    domain.organization = target_org
                    domain.save()
                    domains_count += 1

                self.stdout.write(f"Updated {domains_count} domains to point to the owasp organization")

                # Update projects to point to the target organization
                projects_count = 0
                for project in source_org.projects.all():
                    project.organization = target_org
                    project.save()
                    projects_count += 1

                self.stdout.write(f"Updated {projects_count} projects to point to the owasp organization")

                # Update repos to point to the target organization
                repos_count = 0
                for repo in source_org.repos.all():
                    repo.organization = target_org
                    repo.save()
                    repos_count += 1

                self.stdout.write(f"Updated {repos_count} repos to point to the owasp organization")

                # Update time logs to point to the target organization
                time_logs_count = 0
                for time_log in source_org.time_logs.all():
                    time_log.organization = target_org
                    time_log.save()
                    time_logs_count += 1

                self.stdout.write(f"Updated {time_logs_count} time logs to point to the owasp organization")

                # Update user profiles that have this team
                user_profiles_count = 0
                for user_profile in source_org.user_profiles.all():
                    user_profile.team = target_org
                    user_profile.save()
                    user_profiles_count += 1

                msg = f"Updated {user_profiles_count} user profiles to point to the owasp organization"
                self.stdout.write(msg)

                # Update team challenges
                team_challenges_count = 0
                for challenge in source_org.team_challenges.all():
                    challenge.team_participants.remove(source_org)
                    challenge.team_participants.add(target_org)
                    team_challenges_count += 1

                self.stdout.write(f"Updated {team_challenges_count} team challenges to point to the owasp organization")

                # Delete the source organization
                source_org_id = source_org.id
                source_org.delete()

                self.stdout.write(
                    self.style.SUCCESS(f"Successfully deleted owasp-foundation organization (ID: {source_org_id})")
                )
                self.stdout.write(self.style.SUCCESS("Migration completed successfully!"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred during migration: {str(e)}"))
            # Log the full traceback for debugging
            logger.exception("Exception during OWASP organization migration")
