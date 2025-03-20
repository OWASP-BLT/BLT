import logging
from time import sleep

import requests
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from website.models import OsshCommunity, Tag

# ANSI escape codes for colors
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_RESET = "\033[0m"

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetches tech and open source communities from Reddit"

    def __init__(self):
        super().__init__()
        self.headers = {"User-Agent": "OsshCommunity/1.0"}
        self.processed_subreddits = set()
        self.MAX_COMMUNITIES = 100  # Control how many subreddits to fetch
        # Base topics to seed the search
        self.base_topics = [
            "programming",
            "coding",
            "developers",
            "computerscience",
            "technology",
            "opensource",
            "software",
        ]
        # Keywords to validate if a subreddit is relevant
        self.tech_keywords = {
            "programming",
            "code",
            "coding",
            "developer",
            "software",
            "web",
            "api",
            "database",
            "devops",
            "cloud",
            "opensource",
            "github",
            "computer",
            "tech",
            "engineering",
            "framework",
            "language",
            "script",
            "algorithm",
            "backend",
            "frontend",
            "fullstack",
            "infrastructure",
            "security",
            "docker",
            "kubernetes",
            "linux",
            "python",
            "javascript",
            "java",
            "rust",
            "golang",
            "cpp",
            "csharp",
        }

    def is_tech_related(self, subreddit_data):
        """Check if subreddit is tech-related based on description and title"""
        text = (
            (subreddit_data.get("description", "") or "").lower()
            + (subreddit_data.get("title", "") or "").lower()
            + (subreddit_data.get("display_name", "") or "").lower()
        )
        return any(keyword in text for keyword in self.tech_keywords)

    def search_subreddits(self, query):
        """Search for subreddits using Reddit's search API"""
        url = f"https://www.reddit.com/subreddits/search.json?q={query}&limit=100"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()["data"]["children"]
        except Exception as e:
            logger.error(f"{COLOR_RED}Error searching subreddits for query '{query}': {str(e)}{COLOR_RESET}")
            return []

    def get_related_subreddits(self, subreddit_name):
        """Get related subreddits from sidebar and wiki"""
        url = f"https://www.reddit.com/r/{subreddit_name}/wiki/related.json"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()["data"]["content_md"].lower()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                logger.warning(
                    f"{COLOR_YELLOW}Wiki not found for r/{subreddit_name}. Skipping related subreddits.{COLOR_RESET}"
                )
            elif response.status_code == 403:
                logger.warning(
                    f"{COLOR_YELLOW}Access denied to wiki for r/{subreddit_name}. Skipping related subreddits.{COLOR_RESET}"
                )
            else:
                logger.error(
                    f"{COLOR_RED}Failed to fetch related subreddits for r/{subreddit_name}: {str(e)}{COLOR_RESET}"
                )
            return ""
        except Exception as e:
            logger.error(
                f"{COLOR_RED}Unexpected error fetching related subreddits for r/{subreddit_name}: {str(e)}{COLOR_RESET}"
            )
            return ""

    def save_subreddit(self, data):
        """Save subreddit data to database"""
        try:
            community, created = OsshCommunity.objects.update_or_create(
                external_id=f"reddit-{data['id']}",
                defaults={
                    "name": data["display_name"],
                    "description": data.get("description", "")[:500],
                    "website": f"https://reddit.com/r/{data['display_name']}",
                    "source": "Reddit",
                    "category": "community",
                    "contributors_count": data["subscribers"],
                    "metadata": {
                        "subscriber_count": data["subscribers"],
                        "active_user_count": data.get("active_user_count", 0),
                        "created_utc": data["created_utc"],
                    },
                },
            )

            # Add tags based on subreddit name and common topics
            tags = set([slugify(data["display_name"])])
            for keyword in self.tech_keywords:
                if keyword in data.get("description", "").lower():
                    tags.add(keyword)

            for tag_name in tags:
                try:
                    # Try to get or create the tag
                    tag, _ = Tag.objects.get_or_create(slug=slugify(tag_name), defaults={"name": tag_name})
                    community.tags.add(tag)
                except Exception as e:
                    # If the slug already exists, fetch the existing tag
                    logger.warning(f"{COLOR_YELLOW}Tag '{tag_name}' already exists. Using existing tag.{COLOR_RESET}")
                    tag = Tag.objects.get(slug=slugify(tag_name))
                    community.tags.add(tag)

            return created
        except Exception as e:
            logger.error(f"{COLOR_RED}Failed to save r/{data['display_name']}: {str(e)}{COLOR_RESET}")
            return None

    def handle(self, *args, **options):
        logger.info(f"{COLOR_BLUE}Starting to fetch tech and open source communities from Reddit.{COLOR_RESET}")
        communities_fetched = 0

        for topic in self.base_topics:
            try:
                subreddits = self.search_subreddits(topic)
                for subreddit in subreddits:
                    if communities_fetched >= self.MAX_COMMUNITIES:
                        logger.info(
                            f"{COLOR_BLUE}Reached maximum communities limit ({self.MAX_COMMUNITIES}). Stopping.{COLOR_RESET}"
                        )
                        return

                    data = subreddit["data"]

                    if data["display_name"] in self.processed_subreddits or not self.is_tech_related(data):
                        continue

                    self.processed_subreddits.add(data["display_name"])
                    created = self.save_subreddit(data)

                    if created:
                        communities_fetched += 1
                        logger.info(f"{COLOR_GREEN}Added r/{data['display_name']}{COLOR_RESET}")

                        # For future use if we register the app on reddit api
                        # related_content = self.get_related_subreddits(data['display_name'])
                        # if related_content:
                        #     for keyword in self.tech_keywords:
                        #         if keyword in related_content:
                        #             new_subreddits = self.search_subreddits(keyword)
                        #             for new_sub in new_subreddits:
                        #                 if (new_sub['data']['display_name'] not in
                        #                     self.processed_subreddits):
                        #                     self.save_subreddit(new_sub['data'])

                    sleep(1)

            except Exception as e:
                logger.error(f"{COLOR_RED}Failed processing topic '{topic}': {str(e)}{COLOR_RESET}")

        logger.info(f"{COLOR_BLUE}Finished fetching communities. Total fetched: {communities_fetched}{COLOR_RESET}")
