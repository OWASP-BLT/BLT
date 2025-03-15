import logging
import time
from datetime import datetime
from datetime import timezone as dt_timezone

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from website.models import Repo, Tag

# ANSI escape codes for colors
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_RESET = "\033[0m"

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetches and updates open source repository data from GitHub"

    def handle(self, *args, **options):
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"token {settings.GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        )

        self.MIN_STARS = 10
        self.MIN_FORKS = 5
        self.MAX_REPOS = 500  # Could go upwards of 100k in production
        self.MIN_CONTRIBUTORS, self.MIN_COMMITS = 5, 20
        self.MAX_DAYS_SINCE_UPDATE = 60

        logger.info(f"{COLOR_BLUE}Starting the fetch_repositories process.{COLOR_RESET}")
        self.fetch_repositories()
        logger.info(f"{COLOR_BLUE}Finished the fetch_repositories process.{COLOR_RESET}")

    def has_code_files(self, repo_full_name):
        """Check if the repo contains at least one source code file."""
        try:
            repo_details = self.session.get(f"https://api.github.com/repos/{repo_full_name}").json()
            default_branch = repo_details.get("default_branch", "main")

            response = self.session.get(
                f"https://api.github.com/repos/{repo_full_name}/git/trees/{default_branch}?recursive=1"
            )
            if response.status_code != 200:
                logger.warning(
                    f"{COLOR_YELLOW}Failed to fetch file tree for {repo_full_name}: {response.status_code}{COLOR_RESET}"
                )
                return False

            files = [file["path"] for file in response.json().get("tree", [])]
            code_extensions = {".py", ".js", ".java", ".cpp", ".c", ".ts", ".rb", ".go", ".rs", ".swift"}
            return any(file.endswith(tuple(code_extensions)) for file in files)

        except Exception as e:
            logger.error(f"{COLOR_RED}Error checking code files for {repo_full_name}: {str(e)}{COLOR_RESET}")
            return False

    def get_commit_count(self, repo_full_name):
        """Fetches the total commit count efficiently."""
        url = f"https://api.github.com/repos/{repo_full_name}/commits?per_page=1"
        try:
            response = self.session.get(url)
            if response.status_code == 200 and response.links.get("last"):
                last_page_url = response.links["last"]["url"]
                last_page_number = int(last_page_url.split("page=")[-1])
                return last_page_number
            elif response.status_code == 200:
                return len(response.json())
            else:
                return 0
        except Exception as e:
            logger.error(f"{COLOR_RED}Error fetching commit count for {repo_full_name}: {str(e)}{COLOR_RESET}")
            return 0

    def get_contributors_count(self, repo_full_name):
        """Fetches the number of contributors."""
        url = f"https://api.github.com/repos/{repo_full_name}/contributors?per_page=1&anon=true"
        try:
            response = self.session.get(url)
            if response.status_code == 200 and response.links.get("last"):
                last_page_url = response.links["last"]["url"]
                last_page_number = int(last_page_url.split("page=")[-1])
                return last_page_number
            elif response.status_code == 200:
                return len(response.json())
            else:
                return 0
        except Exception as e:
            logger.error(f"{COLOR_RED}Error fetching contributors for {repo_full_name}: {str(e)}{COLOR_RESET}")
            return 0

    def get_top_languages(self, repo_full_name):
        try:
            url = f"https://api.github.com/repos/{repo_full_name}/languages"
            response = requests.get(url)
            response.raise_for_status()
            languages = response.json()
            # Sort the languages by the number of bytes and get the top 7
            top_languages = sorted(languages, key=languages.get, reverse=True)[:7]
            return top_languages
        except Exception as e:
            logger.error(f"Error fetching languages for {repo_full_name}: {str(e)}")
            return []

    def is_good_repository(self, repo_data):
        """Checks for repository quality."""
        failure_messages = []

        if not self.has_code_files(repo_data["full_name"]):
            failure_messages.append(f"{COLOR_RED}No code files found{COLOR_RESET}")

        num_contributors = self.get_contributors_count(repo_data["full_name"])
        if num_contributors < self.MIN_CONTRIBUTORS:
            failure_messages.append(f"{COLOR_RED}Contributors < {self.MIN_CONTRIBUTORS}{COLOR_RESET}")

        num_commits = self.get_commit_count(repo_data["full_name"])
        if num_commits < self.MIN_COMMITS:
            failure_messages.append(f"{COLOR_RED}Commits < {self.MIN_COMMITS}{COLOR_RESET}")

        last_push_date = datetime.strptime(repo_data["pushed_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt_timezone.utc)
        days_since_last_push = (datetime.now(dt_timezone.utc) - last_push_date).days
        if days_since_last_push > self.MAX_DAYS_SINCE_UPDATE:
            failure_messages.append(f"{COLOR_RED}Last push > {self.MAX_DAYS_SINCE_UPDATE} days ago{COLOR_RESET}")

        if repo_data["stargazers_count"] < self.MIN_STARS:
            failure_messages.append(f"{COLOR_RED}Stars < {self.MIN_STARS}{COLOR_RESET}")
        if repo_data["forks_count"] < self.MIN_FORKS:
            failure_messages.append(f"{COLOR_RED}Forks < {self.MIN_FORKS}{COLOR_RESET}")
        if repo_data["archived"]:
            failure_messages.append(f"{COLOR_RED}Repository is archived{COLOR_RESET}")
        if repo_data.get("license") is None:
            failure_messages.append(f"{COLOR_RED}No license found{COLOR_RESET}")
        if repo_data.get("size", 0) <= 100:
            failure_messages.append(f"{COLOR_RED}Size <= 100 KB{COLOR_RESET}")

        if failure_messages:
            logger.warning(
                f"{COLOR_YELLOW}Repository {repo_data['full_name']} failed checks: {', '.join(failure_messages)}{COLOR_RESET}"
            )
            return False

        logger.info(f"{COLOR_GREEN}Repository {repo_data['full_name']} meets all criteria.{COLOR_RESET}")
        return True

    def fetch_repositories(self):
        query = " ".join(
            [
                "is:public",
                f"stars:>={self.MIN_STARS}",
                f"forks:>={self.MIN_FORKS}",
                "archived:false",
                "has:license",
                "size:>100",
                "-topic:awesome",
                "-topic:list",
                "-topic:resource",
                "-topic:resources",
                "-topic:questions",
                "-topic:cheatsheet",
                "-topic:roadmap",
                "-topic:guide",
                "-topic:collection",
                "-topic:interview",
                "-topic:coding-interview",
                "-topic:notes",
                "-topic:tutorials",
            ]
        )
        page, repos_processed, repos_saved = 1, 0, 0

        while repos_processed < self.MAX_REPOS:
            try:
                logger.info(f"{COLOR_BLUE}Fetching repositories from GitHub API (Page {page}).{COLOR_RESET}")
                response = self.session.get(
                    "https://api.github.com/search/repositories",
                    params={"q": query, "sort": "stars", "order": "desc", "page": page, "per_page": 100},
                )

                if response.status_code == 403:
                    logger.warning(
                        f"{COLOR_YELLOW}Reached GitHub API rate limit. Sleeping for 60 seconds.{COLOR_RESET}"
                    )
                    time.sleep(60)
                    continue
                elif response.status_code != 200:
                    logger.error(f"{COLOR_RED}Error fetching repositories: {response.status_code}{COLOR_RESET}")
                    break

                repos = response.json().get("items", [])
                if not repos:
                    logger.info(f"{COLOR_BLUE}No more repositories found. Exiting loop.{COLOR_RESET}")
                    break

                self.process_repositories(repos)
                repos_processed += len(repos)
                logger.info(f"{COLOR_BLUE}Processed {repos_processed} repositories so far.{COLOR_RESET}")
                page += 1
                time.sleep(1)
            except Exception as e:
                logger.error(f"{COLOR_RED}Error fetching repositories: {str(e)}{COLOR_RESET}")
                time.sleep(5)

    def process_repositories(self, repos):
        for repo_data in repos:
            try:
                if not self.is_good_repository(repo_data):
                    continue

                with transaction.atomic():
                    repo, created = Repo.objects.update_or_create(
                        repo_url=repo_data["html_url"],
                        defaults={
                            "name": repo_data["name"],
                            "description": repo_data["description"] or "",
                            "primary_language": repo_data["language"] or "",
                            "last_updated": timezone.make_aware(
                                datetime.strptime(repo_data["updated_at"], "%Y-%m-%dT%H:%M:%SZ"), dt_timezone.utc
                            ),
                            "stars": repo_data["stargazers_count"],
                            "forks": repo_data["forks_count"],
                            "open_issues": repo_data["open_issues_count"],
                            "last_commit_date": timezone.make_aware(
                                datetime.strptime(repo_data["pushed_at"], "%Y-%m-%dT%H:%M:%SZ"), dt_timezone.utc
                            ),
                            "license": repo_data.get("license", {}).get("spdx_id", ""),
                            "contributor_count": self.get_contributors_count(repo_data["full_name"]),
                            "commit_count": self.get_commit_count(repo_data["full_name"]),
                            "size": repo_data.get("size", 0),
                            "watchers": repo_data.get("watchers_count", 0),
                            "subscribers_count": repo_data.get("subscribers_count", 0),
                            "network_count": repo_data.get("network_count", 0),
                            "closed_issues": repo_data.get("closed_issues_count", 0),
                            "open_pull_requests": repo_data.get("open_pull_requests_count", 0),
                        },
                    )

                    if repo_data.get("topics"):
                        tags = []
                        for topic in repo_data["topics"]:
                            tag_slug = slugify(topic)
                            tag, _ = Tag.objects.get_or_create(slug=tag_slug, defaults={"name": topic})
                            tags.append(tag)

                        top_languages = self.get_top_languages(repo_data["full_name"])
                        for language in top_languages:
                            tag_slug = slugify(language)
                            tag, _ = Tag.objects.get_or_create(slug=tag_slug, defaults={"name": language})
                            tags.append(tag)

                        repo.tags.set(tags)

                    logger.info(
                        f"{COLOR_GREEN}{'Created' if created else 'Updated'} repository: {repo.name}{COLOR_RESET}"
                    )
            except Exception as e:
                logger.error(f"{COLOR_RED}Error processing repository {repo_data['full_name']}: {str(e)}{COLOR_RESET}")
                continue

