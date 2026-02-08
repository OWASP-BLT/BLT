"""
Management command to sync timers with GitHub issue status
Useful for cleaning up stale timers or syncing after downtime
"""
import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import TimeLog

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync timers with GitHub issue status'

    def add_arguments(self, parser):
        parser.add_argument(
            '--stop-closed',
            action='store_true',
            help='Stop timers for closed GitHub issues',
        )
        parser.add_argument(
            '--stop-stale',
            action='store_true',
            help='Stop timers that have been running for more than 24 hours',
        )
        parser.add_argument(
            '--github-token',
            type=str,
            help='GitHub personal access token for API calls',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        github_token = options.get('github_token') or getattr(settings, 'GITHUB_TOKEN', None)

        if not github_token and (options['stop_closed']):
            self.stdout.write(
                self.style.ERROR('GitHub token required for --stop-closed option')
            )
            return

        # Get all active timers
        active_timers = TimeLog.objects.filter(end_time__isnull=True)
        self.stdout.write(f'Found {active_timers.count()} active timers')

        if options['stop_stale']:
            self.stop_stale_timers(active_timers, dry_run)

        if options['stop_closed']:
            self.stop_closed_issue_timers(active_timers, github_token, dry_run)

        self.stdout.write(self.style.SUCCESS('Sync completed'))

    def stop_stale_timers(self, timers, dry_run):
        """Stop timers that have been running for more than 24 hours"""
        cutoff = timezone.now() - timedelta(hours=24)
        stale_timers = timers.filter(start_time__lt=cutoff)

        self.stdout.write(f'Found {stale_timers.count()} stale timers (>24 hours)')

        for timer in stale_timers:
            duration = timezone.now() - timer.start_time
            self.stdout.write(
                f'  Timer {timer.id} for {timer.user.username}: '
                f'{duration.total_seconds() / 3600:.1f} hours'
            )

            if not dry_run:
                timer.end_time = timezone.now()
                timer.save()
                self.stdout.write(self.style.SUCCESS(f'    Stopped timer {timer.id}'))

    def stop_closed_issue_timers(self, timers, github_token, dry_run):
        """Stop timers for closed GitHub issues"""
        timers_with_issues = timers.exclude(
            github_issue_number__isnull=True
        ).exclude(
            github_repo__isnull=True
        )

        self.stdout.write(
            f'Checking {timers_with_issues.count()} timers with GitHub issues'
        )

        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        for timer in timers_with_issues:
            try:
                # Check issue status on GitHub
                url = f'https://api.github.com/repos/{timer.github_repo}/issues/{timer.github_issue_number}'
                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    issue_data = response.json()
                    state = issue_data.get('state')

                    if state == 'closed':
                        self.stdout.write(
                            f'  Timer {timer.id}: Issue #{timer.github_issue_number} '
                            f'in {timer.github_repo} is closed'
                        )

                        if not dry_run:
                            timer.end_time = timezone.now()
                            timer.save()
                            self.stdout.write(
                                self.style.SUCCESS(f'    Stopped timer {timer.id}')
                            )
                elif response.status_code == 404:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  Timer {timer.id}: Issue not found (may be deleted)'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  Timer {timer.id}: GitHub API error {response.status_code}'
                        )
                    )

            except requests.RequestException as e:
                self.stdout.write(
                    self.style.ERROR(f'  Timer {timer.id}: Request failed - {str(e)}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  Timer {timer.id}: Error - {str(e)}')
                )
