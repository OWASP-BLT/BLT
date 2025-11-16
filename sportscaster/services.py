import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from openai import OpenAI

from .models import AICommentaryTemplate, GitHubEvent, Leaderboard, MonitoredEntity

logger = logging.getLogger(__name__)


class GitHubService:
    """Service for interacting with GitHub API"""

    def __init__(self):
        self.github_token = getattr(settings, "GITHUB_TOKEN", os.environ.get("GITHUB_TOKEN", ""))
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def get_repository_events(self, owner: str, repo: str) -> List[Dict]:
        """Fetch recent events for a repository"""
        cache_key = f"github_events_{owner}_{repo}"
        cached_events = cache.get(cache_key)

        if cached_events:
            return cached_events

        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/events"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            events = response.json()

            cache.set(cache_key, events, 60)  # Cache for 1 minute
            return events
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching GitHub events for {owner}/{repo}: {e}")
            return []

    def get_repository_stats(self, owner: str, repo: str) -> Dict:
        """Fetch repository statistics"""
        cache_key = f"github_stats_{owner}_{repo}"
        cached_stats = cache.get(cache_key)

        if cached_stats:
            return cached_stats

        try:
            url = f"{self.base_url}/repos/{owner}/{repo}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            stats = {
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "watchers": data.get("watchers_count", 0),
                "open_issues": data.get("open_issues_count", 0),
            }

            cache.set(cache_key, stats, 300)  # Cache for 5 minutes
            return stats
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching GitHub stats for {owner}/{repo}: {e}")
            return {}

    def get_organization_repositories(self, org: str) -> List[Dict]:
        """Fetch repositories for an organization"""
        cache_key = f"github_org_repos_{org}"
        cached_repos = cache.get(cache_key)

        if cached_repos:
            return cached_repos

        try:
            url = f"{self.base_url}/orgs/{org}/repos"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            repos = response.json()

            cache.set(cache_key, repos, 600)  # Cache for 10 minutes
            return repos
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching organization repositories for {org}: {e}")
            return []

    def parse_github_url(self, url: str) -> Optional[Dict]:
        """Parse GitHub URL to extract owner and repo"""
        try:
            # Remove trailing slashes and .git
            url = url.rstrip("/").replace(".git", "")

            # Validate that the URL is from github.com domain
            if not url.startswith(("https://github.com/", "http://github.com/", "github.com/")):
                return None

            # Extract the path after github.com/
            if "://" in url:
                # URL with protocol
                parts = url.split("://")[-1].split("/")
                if len(parts) >= 3 and parts[0] == "github.com":
                    return {"owner": parts[1], "repo": parts[2]}
            else:
                # URL without protocol
                parts = url.split("/")
                if len(parts) >= 3 and parts[0] == "github.com":
                    return {"owner": parts[1], "repo": parts[2]}

            return None
        except Exception as e:
            logger.error(f"Error parsing GitHub URL {url}: {e}")
            return None


class AICommentaryService:
    """Service for generating AI-powered sports commentary"""

    def __init__(self):
        self.openai_api_key = getattr(settings, "OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
        if self.openai_api_key and self.openai_api_key != "openai_api_key":
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None

    def generate_commentary(self, event: GitHubEvent) -> str:
        """Generate sports-style commentary for a GitHub event"""
        if not self.client:
            return self._generate_fallback_commentary(event)

        try:
            # Get template for this event type
            template = self._get_commentary_template(event.event_type)

            # Prepare event context
            context = self._prepare_event_context(event)

            # Generate commentary using OpenAI
            prompt = self._build_prompt(event, context, template)

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Using gpt-4o-mini as o3-mini-high is not yet available
                messages=[
                    {
                        "role": "system",
                        "content": "You are an enthusiastic sports commentator covering GitHub activity like it's a competitive sport. Be energetic, dramatic, and engaging!",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=150,
                temperature=0.8,
            )

            commentary = response.choices[0].message.content.strip()
            return commentary

        except Exception as e:
            logger.error(f"Error generating AI commentary: {e}")
            return self._generate_fallback_commentary(event)

    def _get_commentary_template(self, event_type: str) -> str:
        """Get commentary template for event type"""
        try:
            template_obj = AICommentaryTemplate.objects.filter(event_type=event_type, is_active=True).first()
            if template_obj:
                return template_obj.template
        except Exception:
            pass

        # Default templates
        templates = {
            "star": "Oh wow! {repo} just gained {count} stars! The crowd goes wild!",
            "fork": "And {repo} has been forked {count} times! Developers are taking notice!",
            "pull_request": "Breaking news! A new pull request on {repo} from {user}!",
            "commit": "{user} just committed to {repo}! The action is heating up!",
            "release": "RELEASE ALERT! {repo} version {version} just dropped!",
        }
        return templates.get(event_type, "Amazing activity on {repo}!")

    def _prepare_event_context(self, event: GitHubEvent) -> Dict:
        """Prepare context from event data"""
        data = event.event_data
        entity = event.monitored_entity

        context = {
            "repo": entity.name,
            "event_type": event.event_type,
            "timestamp": event.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Add event-specific data
        if "count" in data:
            context["count"] = data["count"]
        if "user" in data:
            context["user"] = data["user"]
        if "version" in data:
            context["version"] = data["version"]

        return context

    def _build_prompt(self, event: GitHubEvent, context: Dict, template: str) -> str:
        """Build AI prompt for commentary generation"""
        prompt = f"""
Generate an exciting sports-style commentary for this GitHub event:

Event Type: {event.event_type}
Repository: {context['repo']}
Context: {template.format(**context)}

Make it sound like you're commentating a thrilling sports match. Be energetic and engaging!
Keep it under 100 words.
"""
        return prompt

    def _generate_fallback_commentary(self, event: GitHubEvent) -> str:
        """Generate simple fallback commentary without AI"""
        template = self._get_commentary_template(event.event_type)
        context = self._prepare_event_context(event)

        try:
            return template.format(**context)
        except Exception:
            return f"Exciting {event.event_type} activity on {event.monitored_entity.name}!"


class EventProcessingService:
    """Service for processing GitHub events and updating leaderboards"""

    def __init__(self):
        self.github_service = GitHubService()
        self.ai_service = AICommentaryService()

    def process_monitored_entities(self):
        """Process all active monitored entities"""
        entities = MonitoredEntity.objects.filter(is_active=True)

        for entity in entities:
            try:
                self.process_entity(entity)
            except Exception as e:
                logger.error(f"Error processing entity {entity.name}: {e}")

    def process_entity(self, entity: MonitoredEntity):
        """Process a single monitored entity"""
        parsed = self.github_service.parse_github_url(entity.github_url)

        if not parsed:
            logger.warning(f"Could not parse GitHub URL for {entity.name}")
            return

        owner = parsed["owner"]
        repo = parsed["repo"]

        # Fetch and process events
        events = self.github_service.get_repository_events(owner, repo)
        self._process_events(entity, events)

        # Update leaderboard
        stats = self.github_service.get_repository_stats(owner, repo)
        self._update_leaderboard(entity, stats)

    def _process_events(self, entity: MonitoredEntity, events: List[Dict]):
        """Process events and create GitHubEvent records"""
        for event_data in events[:10]:  # Process last 10 events
            event_type = self._map_event_type(event_data.get("type", ""))

            if not event_type:
                continue

            # Check if event already exists
            event_id = event_data.get("id")
            if event_id and GitHubEvent.objects.filter(event_data__id=event_id).exists():
                continue

            # Create new event
            github_event = GitHubEvent.objects.create(
                monitored_entity=entity, event_type=event_type, event_data=event_data, processed=False
            )

            # Generate commentary asynchronously (in production, use Celery)
            try:
                commentary = self.ai_service.generate_commentary(github_event)
                github_event.commentary_text = commentary
                github_event.commentary_generated = True
                github_event.save()
            except Exception as e:
                logger.error(f"Error generating commentary for event {github_event.id}: {e}")

    def _map_event_type(self, github_event_type: str) -> str:
        """Map GitHub event type to our event types"""
        mapping = {
            "WatchEvent": "star",
            "ForkEvent": "fork",
            "PullRequestEvent": "pull_request",
            "PushEvent": "commit",
            "ReleaseEvent": "release",
            "IssuesEvent": "issue",
        }
        return mapping.get(github_event_type, "")

    def _update_leaderboard(self, entity: MonitoredEntity, stats: Dict):
        """Update leaderboard with current stats"""
        for metric_type, value in stats.items():
            leaderboard, created = Leaderboard.objects.get_or_create(
                monitored_entity=entity, metric_type=metric_type, defaults={"current_value": value}
            )

            if not created:
                leaderboard.previous_value = leaderboard.current_value
                leaderboard.current_value = value
                leaderboard.save()

        # Update rankings
        self._update_rankings()

    def _update_rankings(self):
        """Update rankings for all leaderboard entries"""
        metric_types = Leaderboard.objects.values_list("metric_type", flat=True).distinct()

        for metric_type in metric_types:
            entries = Leaderboard.objects.filter(metric_type=metric_type).order_by("-current_value")

            for rank, entry in enumerate(entries, start=1):
                entry.rank = rank
                entry.save(update_fields=["rank"])
