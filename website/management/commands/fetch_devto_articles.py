import logging
import time
from datetime import datetime

import requests
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.utils.timezone import make_aware

from website.models import OsshArticle, Tag

# ANSI escape codes for colors
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_RESET = "\033[0m"

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetches articles from DEV.to API and stores them in the database."

    def handle(self, *args, **kwargs):
        base_url = "https://dev.to/api/articles"
        tags = ["programming", "javascript", "python", "webdev", "tutorial"]
        rate_limit_delay = 1

        for tag in tags:
            params = {
                "tag": tag,
            }

            try:
                # Add a delay to respect rate limits
                time.sleep(rate_limit_delay)
                response = requests.get(base_url, params=params)
                if response.status_code == 200:
                    articles = response.json()
                    for article in articles:
                        external_id = article.get("id")
                        title = article.get("title")
                        author = article.get("user", {}).get("name")
                        author_profile_image = article.get("user", {}).get("profile_image")
                        description = article.get("description")
                        publication_date = make_aware(
                            datetime.strptime(article.get("published_at"), "%Y-%m-%dT%H:%M:%SZ")
                        )
                        source = "DEV Community"
                        url = article.get("url")
                        cover_image = article.get("cover_image")
                        reading_time_minutes = article.get("reading_time_minutes")
                        ossh_article, created = OsshArticle.objects.update_or_create(
                            external_id=external_id,
                            defaults={
                                "title": title,
                                "author": author,
                                "author_profile_image": author_profile_image,
                                "description": description,
                                "publication_date": publication_date,
                                "source": source,
                                "url": url,
                                "cover_image": cover_image,
                                "reading_time_minutes": reading_time_minutes,
                            },
                        )

                        tags_list = article.get("tag_list", [])
                        for tag_name in tags_list:
                            try:
                                tag, _ = Tag.objects.get_or_create(slug=slugify(tag_name), defaults={"name": tag_name})
                                ossh_article.tags.add(tag)
                            except Exception as e:
                                logger.warning(
                                    f"{COLOR_YELLOW}Tag '{tag_name}' already exists. Using existing tag.{COLOR_RESET}"
                                )
                                tag = Tag.objects.get(slug=slugify(tag_name))
                                ossh_article.tags.add(tag)

                    logger.info(
                        f"{COLOR_GREEN}Successfully fetched and stored {len(articles)} articles for tag '{tag}'.{COLOR_RESET}"
                    )
                else:
                    logger.error(
                        f"{COLOR_RED}Failed to fetch articles for tag '{tag}'. Status code: {response.status_code}{COLOR_RESET}"
                    )

            except requests.exceptions.RequestException as e:
                logger.error(f"{COLOR_RED}Request failed for tag: {e}{COLOR_RESET}")
            except Exception as e:
                logger.error(f"{COLOR_RED}An unexpected error: {e}{COLOR_RESET}")

        self.stdout.write(self.style.SUCCESS("Finished fetching and storing articles from DEV.to."))
