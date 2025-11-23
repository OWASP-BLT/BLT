import logging
from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from slack_bolt import App

from website.management.base import LoggedBaseCommand
from website.models import Project, Repo, SlackIntegration

logger = logging.getLogger(__name__)


class Command(LoggedBaseCommand):
    help = "Sends weekly project report to organizations with Slack integration"

    def handle(self, *args, **kwargs):
        logger.info("Starting weekly Slack report generation")

        # Fetch all Slack integrations with related integration data
        slack_integrations = SlackIntegration.objects.select_related("integration__organization").all()

        for integration in slack_integrations:
            current_org = integration.integration.organization
            if integration.default_channel_id and current_org:
                logger.info(f"Processing weekly report for organization: {current_org.name}")
                try:
                    report_message = self.generate_weekly_report(current_org)
                    self.send_message(
                        integration.default_channel_id,
                        integration.bot_access_token,
                        report_message,
                    )
                    logger.info(f"Successfully sent weekly report to {current_org.name}")
                except Exception as e:
                    logger.error(f"Error generating/sending report for {current_org.name}: {e}")

    def generate_weekly_report(self, organization):
        """Generate a comprehensive weekly report for the organization's projects."""
        one_week_ago = timezone.now() - timedelta(days=7)

        # Get all projects for this organization with repo count annotation
        projects = Project.objects.filter(organization=organization).annotate(repo_count=Count("repos"))
        project_count = projects.count()

        # Get all repos for this organization
        repos = Repo.objects.filter(organization=organization)
        total_repos = repos.count()

        # Count repos by different criteria
        active_repos = repos.filter(is_archived=False).count()
        archived_repos = repos.filter(is_archived=True).count()

        # Get repos updated in the last week
        recently_updated_repos = repos.filter(last_updated__gte=one_week_ago, is_archived=False).order_by(
            "-last_updated"
        )[:10]

        # Aggregate statistics
        aggregates = repos.aggregate(
            total_stars=Sum("stars"),
            total_forks=Sum("forks"),
            total_open_issues=Sum("open_issues"),
            total_contributors=Sum("contributor_count"),
        )
        total_stars = aggregates["total_stars"] or 0
        total_forks = aggregates["total_forks"] or 0
        total_open_issues = aggregates["total_open_issues"] or 0
        total_contributors = aggregates["total_contributors"] or 0

        # Build the report message
        report_lines = [
            "📊 *Weekly Organization Report*",
            f"Organization: *{organization.name}*",
            f"Report Date: {timezone.now().strftime('%B %d, %Y')}",
            "",
            "=" * 50,
            "",
            "📈 *Overview Statistics*",
            f"• Total Projects: {project_count}",
            f"• Total Repositories: {total_repos}",
            f"  - Active: {active_repos}",
            f"  - Archived: {archived_repos}",
            "",
            "⭐ *Aggregate Metrics*",
            f"• Total Stars: {total_stars:,}",
            f"• Total Forks: {total_forks:,}",
            f"• Open Issues: {total_open_issues:,}",
            f"• Contributors: {total_contributors:,}",
        ]

        # Add recently updated repositories section
        if recently_updated_repos.exists():
            report_lines.extend(
                [
                    "",
                    "🔥 *Recently Updated Repositories (Last 7 Days)*",
                ]
            )
            for repo in recently_updated_repos:
                last_updated = repo.last_updated.strftime("%Y-%m-%d") if repo.last_updated else "N/A"
                report_lines.append(
                    f"• *{repo.name}*\n"
                    f"  └─ Last Updated: {last_updated} | ⭐ {repo.stars} | 🍴 {repo.forks} | 🐛 {repo.open_issues} issues"
                )

        # Add project breakdown if available
        if project_count > 0:
            report_lines.extend(
                [
                    "",
                    "📦 *Projects Overview*",
                ]
            )
            for project in projects[:10]:  # Limit to 10 projects
                # Use annotated repo_count to avoid N+1 queries
                project_repos = project.repo_count
                report_lines.append(f"• *{project.name}*")
                if project.description:
                    # Truncate description if too long
                    desc = project.description[:100] + "..." if len(project.description) > 100 else project.description
                    report_lines.append(f"  └─ {desc}")
                report_lines.append(f"  └─ Repositories: {project_repos} | Status: {project.status}")

        # Add footer
        report_lines.extend(
            [
                "",
                "=" * 50,
                f"🔗 Organization Page: {organization.url}" if organization.url else "",
                "",
                "_This is an automated weekly report. Have a great week!_ 🚀",
            ]
        )

        return "\n".join(report_lines)

    def send_message(self, channel_id, bot_token, message):
        """Send a message to the Slack channel."""
        try:
            app = App(token=bot_token)
            app.client.conversations_join(channel=channel_id)
            response = app.client.chat_postMessage(channel=channel_id, text=message)
            logger.info(f"Message sent successfully: {response['ts']}")
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise
