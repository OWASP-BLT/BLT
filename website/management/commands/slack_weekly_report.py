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

        # Fetch all Slack integrations
        slack_integrations = SlackIntegration.objects.select_related("integration__organization").all()

        for integration in slack_integrations:
            org = integration.integration.organization
            if not org:
                continue

            # Use weekly report channel if configured, otherwise default
            channel_id = integration.weekly_report_channel_id or integration.default_channel_id
            if not channel_id:
                logger.warning(f"No channel configured for {org.name}, skipping")
                continue

            try:
                report = self._generate_report(org)
                self._send_to_slack(channel_id, integration.bot_access_token, report)
                logger.info(f"Sent weekly report to {org.name}")
            except Exception as e:
                logger.error(f"Error sending report for {org.name}: {e}")

    def _generate_report(self, org):
        """Generate weekly report for organization."""
        one_week_ago = timezone.now() - timedelta(days=7)

        # Get projects and repos
        projects = Project.objects.filter(organization=org).annotate(repo_count=Count("repos"))
        repos = Repo.objects.filter(organization=org)

        # Aggregate stats
        stats = repos.aggregate(
            total=Count("id"),
            stars=Sum("stars"),
            forks=Sum("forks"),
            issues=Sum("open_issues"),
        )

        # Build report
        lines = [
            "📊 *Weekly Organization Report*",
            f"Organization: *{org.name}*",
            f"Date: {timezone.now().strftime('%B %d, %Y')}",
            "",
            "📈 *Statistics*",
            f"• Projects: {projects.count()}",
            f"• Repositories: {stats['total'] or 0}",
            f"• Stars: {stats['stars'] or 0:,}",
            f"• Forks: {stats['forks'] or 0:,}",
            f"• Open Issues: {stats['issues'] or 0:,}",
        ]

        # Recent repos
        recent = repos.filter(last_updated__gte=one_week_ago, is_archived=False).order_by("-last_updated")[:5]

        if recent.exists():
            lines.extend(["", "🔥 *Recently Updated*"])
            for repo in recent:
                date = repo.last_updated.strftime("%Y-%m-%d") if repo.last_updated else "N/A"
                lines.append(f"• {repo.name} ({date})")

        # Top projects
        if projects.exists():
            lines.extend(["", "📦 *Top Projects*"])
            for proj in projects[:5]:
                lines.append(f"• {proj.name} ({proj.repo_count} repos)")

        return "\n".join(lines)

    def _send_to_slack(self, channel_id, token, message):
        """Send message to Slack."""
        try:
            app = App(token=token)
            app.client.chat_postMessage(channel=channel_id, text=message)
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            raise
