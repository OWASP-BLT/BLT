import logging
import re
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import CommandError
from django.db.models import Prefetch
from django.template.loader import render_to_string
from django.utils import timezone

from website.management.base import LoggedBaseCommand
from website.models import Domain, Issue, Organization, UserProfile

logger = logging.getLogger(__name__)

# Configuration constants
BUG_DESCRIPTION_TRUNCATE_WORDS = getattr(settings, "DIGEST_TRUNCATE_WORDS", 30)


class Command(LoggedBaseCommand):
    help = "Send weekly bug report digest to organization/domain followers"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Number of days to look back for bug reports (default: 7)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run without actually sending emails (for testing)",
        )
        parser.add_argument(
            "--organization",
            type=str,
            help="Send digest for a specific organization slug only",
        )

    def handle(self, *_args, **options):
        days = options["days"]
        dry_run = options.get("dry_run", False)
        org_slug = options.get("organization")

        # Validate days parameter first
        if days <= 0:
            raise CommandError("Days parameter must be positive")

        start_date = timezone.now() - timedelta(days=days)

        if dry_run:
            logger.info("DRY RUN MODE - No emails will be sent")

        logger.info(f"Starting weekly bug digest for bugs reported since {start_date}")

        # Process organizations with optimized query
        org_filter = {"is_active": True}
        if org_slug:
            org_filter["slug"] = org_slug

        organizations = Organization.objects.filter(**org_filter).prefetch_related(
            Prefetch(
                "domain_set",
                queryset=Domain.objects.filter(is_active=True),
                to_attr="active_domains",
            )
        )

        if not organizations.exists():
            logger.warning("No active organizations found")
            return

        org_count = 0
        email_count = 0
        skipped_count = 0
        error_count = 0

        for org in organizations:
            try:
                result = self._process_organization(org, start_date, days, dry_run)
                org_count += 1
                email_count += result["sent"]
                skipped_count += result["skipped"]
                error_count += result["errors"]
            except Exception:
                logger.exception("Error processing organization %s", org.name)
                error_count += 1

        logger.info(
            f"Weekly bug digest completed. "
            f"Organizations: {org_count}, "
            f"Emails sent: {email_count}, "
            f"Skipped: {skipped_count}, "
            f"Errors: {error_count}"
        )

    def _process_organization(self, org, start_date, days, dry_run):
        """Process a single organization and return statistics"""
        sent = 0
        skipped = 0
        errors = 0

        # Get all active domains for this organization
        domains = getattr(org, "active_domains", [])

        if not domains:
            logger.debug(f"No active domains for organization: {org.name}")
            return {"sent": sent, "skipped": skipped, "errors": errors}

        # Get new bugs for these domains in the past week
        new_bugs_qs = (
            Issue.objects.filter(domain__in=domains, created__gte=start_date, is_hidden=False)
            .select_related("user", "domain")
            .order_by("-created")
        )

        if not new_bugs_qs.exists():
            logger.debug(f"No new bugs for organization: {org.name}")
            return {"sent": sent, "skipped": skipped, "errors": errors}

        # Materialize bugs once to avoid repeated iteration
        bug_list = list(new_bugs_qs)

        # Get followers (users who subscribed to any of the organization's domains)
        followers = (
            UserProfile.objects.filter(subscribed_domains__in=domains)
            .select_related("user")
            .prefetch_related("subscribed_domains")
            .distinct()
        )

        if not followers.exists():
            logger.debug(f"No followers for organization: {org.name}")
            return {"sent": sent, "skipped": skipped, "errors": errors}

        logger.info("Processing %s: %s bugs, %s followers", org.name, len(bug_list), followers.count())

        # Send email to each follower
        for follower in followers:
            # Validate user has email
            if not follower.user.email:
                logger.debug(f"User ID {follower.user.id} has no email address")
                skipped += 1
                continue

            # Check if user has unsubscribed from emails
            if follower.email_unsubscribed:
                logger.debug(f"User ID {follower.user.id} has unsubscribed, skipping")
                skipped += 1
                continue

            # Check if user is active
            if not follower.user.is_active:
                logger.debug(f"User ID {follower.user.id} is inactive, skipping")
                skipped += 1
                continue

            try:
                if dry_run:
                    logger.debug("[DRY RUN] Would send digest for %s (user_id=%s)", org.name, follower.user.id)
                else:
                    self.send_digest_email(follower.user, org, bug_list, days)
                    logger.debug("Sent weekly digest for %s (user_id=%s)", org.name, follower.user.id)
                sent += 1
            except Exception:
                logger.exception("Failed to send weekly digest for %s (user_id=%s)", org.name, follower.user.id)
                errors += 1

        return {"sent": sent, "skipped": skipped, "errors": errors}

    def send_digest_email(self, user, organization, bugs, days):
        """Send the weekly digest email to a user"""
        # Validate inputs
        if not user or not user.email:
            raise ValueError("User must have a valid email address")

        if not organization:
            raise ValueError("Organization is required")

        # Convert queryset to list to avoid multiple database hits
        bug_list = list(bugs)
        bug_count = len(bug_list)

        if bug_count == 0:
            logger.warning(f"No bugs to send for {organization.name}")
            return

        subject = f"{organization.name} - Weekly Bug Report Digest"

        # Validate and sanitize domain_name to prevent URL injection
        domain_name = getattr(settings, "DOMAIN_NAME", "blt.owasp.org")
        # Remove any protocol and whitespace
        domain_name = domain_name.strip().replace("http://", "").replace("https://", "")
        # Validate it's a reasonable domain (proper format with labels separated by dots)
        if not domain_name or not re.match(
            r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$", domain_name
        ):
            logger.error("Invalid DOMAIN_NAME in settings, using default")
            domain_name = "blt.owasp.org"  # Fallback to safe default

        # Prepare context for email template
        context = {
            "user": user,
            "organization": organization,
            "bugs": bug_list,
            "bug_count": bug_count,
            "days": days,
            "domain_name": domain_name,
            "project_name": getattr(settings, "PROJECT_NAME", "BLT"),
            "truncate_words": BUG_DESCRIPTION_TRUNCATE_WORDS,
        }

        try:
            # Render HTML email
            html_content = render_to_string("email/weekly_bug_digest.html", context)
        except Exception:
            logger.exception("Failed to render weekly_bug_digest template for organization %s", organization.name)
            raise

        # Create plain text version
        text_content = self._create_text_content(user, organization, bug_list, days, domain_name)

        # Create and send email
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=getattr(settings, "EMAIL_TO_STRING", settings.DEFAULT_FROM_EMAIL),
                to=[user.email],
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
        except Exception:
            logger.exception(
                "Failed to send weekly bug digest email to user_id=%s for organization %s",
                user.id,
                organization.name,
            )
            raise

    def _create_text_content(self, user, organization, bugs, days, domain_name):
        """Create plain text email content"""
        project_name = getattr(settings, "PROJECT_NAME", "BLT")

        text_content = f"""Hi {user.username},

Here's your weekly bug report digest for {organization.name}.

{len(bugs)} new bug(s) reported in the last {days} day{"s" if days != 1 else ""}:

"""
        for bug in bugs:
            # Safely handle description
            description = bug.description[:100] if bug.description else "No description"
            domain_name_str = bug.domain.name if bug.domain else "Unknown domain"
            text_content += f"- {description}... ({domain_name_str})\n"
            text_content += f"  View: https://{domain_name}/issue/{bug.id}\n\n"

        # Add organization link if slug exists
        if organization.slug:
            text_content += f"\nView all bugs: https://{domain_name}/organization/{organization.slug}\n"

        text_content += f"""
To unsubscribe from these emails, visit your profile settings.

Best regards,
The {project_name} Team
"""
        return text_content
