import os
import re
import time
from datetime import datetime

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify

from website.management.base import LoggedBaseCommand
from website.models import Contributor, Organization, Project, Repo


class Command(LoggedBaseCommand):
    help = "Automatically detects and imports new OWASP www-project repositories"

    def parse_date_safely(self, date_string):
        """Safely parse datetime string, return None if invalid"""
        if not date_string or not isinstance(date_string, str):
            return None
        try:
            parsed_date = parse_datetime(date_string)
            if parsed_date is None:
                # If Django's parse_datetime fails, try a simpler ISO format parse
                parsed_date = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
            return parsed_date
        except (ValueError, TypeError, AttributeError):
            self.stderr.write(self.style.WARNING(f"Failed to parse date: {date_string}"))
            return None

    def handle(self, *args, **options):
        # Check required environment variables
        github_token = getattr(settings, "GITHUB_TOKEN", None)
        slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL")

        if not github_token:
            self.stderr.write(self.style.ERROR("GITHUB_TOKEN is not configured in settings. Aborting."))
            return

        if not slack_webhook_url:
            self.stderr.write(
                self.style.WARNING("SLACK_WEBHOOK_URL not found in environment. Slack notifications will be disabled.")
            )

        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        # Add default options that exist in owasp_project_upload
        delay_on_rate_limit = 60
        max_rate_limit_retries = 5

        # Get or create OWASP organization
        org, created = Organization.objects.get_or_create(name__iexact="OWASP", defaults={"name": "OWASP"})

        # Fetch all www-project repos
        www_project_repos = self.fetch_all_repos(headers)
        if not www_project_repos:
            self.stdout.write("No repositories fetched or an error occurred.")
            return

        self.stdout.write(f"Found {len(www_project_repos)} www-project repositories")

        # Keep track of new projects for Slack notification
        new_projects = []

        # Process each repository
        for repo_data in www_project_repos:
            repo_url = repo_data["html_url"]

            # Skip if repo already exists by checking Repo table
            if Repo.objects.filter(repo_url=repo_url).exists():
                self.stdout.write(self.style.WARNING(f"Repository {repo_url} already exists. Skipping..."))
                continue

            self.stdout.write(f"Processing repository {repo_url}")
            with transaction.atomic():
                try:
                    # Create project with validation
                    base_url = repo_data.get("homepage", "")  # Default to empty string if None
                    project_name = repo_data["name"]
                    project_slug = slugify(project_name)[:50]

                    # Ensure unique slug
                    base_slug = project_slug
                    counter = 1
                    while Project.objects.filter(slug=project_slug).exists():
                        suffix = f"-{counter}"
                        project_slug = f"{base_slug[:50-len(suffix)]}{suffix}"
                        counter += 1

                    # Validate and set default values for required fields
                    project_data = {
                        "slug": project_slug,
                        "name": project_name,
                        "description": repo_data.get("description")
                        or "No description available",  # Set default description
                        "url": base_url or repo_data.get("html_url", ""),  # Fallback to repo URL if no homepage
                        "organization": org,
                    }

                    # Additional validation
                    if not project_data["name"]:
                        raise ValueError("Project name cannot be empty")

                    # Create project with validated data
                    project = Project.objects.create(**project_data)

                    # Fetch complete repo data
                    repo_info = self.fetch_github_repo_data(
                        repo_url,
                        headers,
                        delay_on_rate_limit,
                        max_rate_limit_retries,
                        is_wiki=True,
                        is_main=False,
                    )

                    if repo_info:
                        # Create main repo with safe date parsing
                        repo = Repo.objects.create(
                            project=project,
                            slug=project_slug,
                            name=repo_data["name"],
                            description=repo_data.get("description", ""),
                            repo_url=repo_url,
                            homepage_url=repo_data.get("homepage", ""),
                            is_wiki=True,
                            is_main=False,
                            stars=repo_info.get("stars", 0),
                            forks=repo_info.get("forks", 0),
                            last_updated=self.parse_date_safely(repo_info.get("last_updated")),
                            watchers=repo_info.get("watchers", 0),
                            primary_language=repo_info.get("primary_language", ""),
                            license=repo_info.get("license", ""),
                            last_commit_date=self.parse_date_safely(repo_info.get("last_commit_date")),
                            created=self.parse_date_safely(repo_info.get("created")),
                            modified=self.parse_date_safely(repo_info.get("modified")),
                            network_count=repo_info.get("network_count", 0),
                            subscribers_count=repo_info.get("subscribers_count", 0),
                            size=repo_info.get("size", 0),
                            logo_url=repo_info.get("logo_url", ""),
                            open_issues=repo_info.get("open_issues", 0),
                            closed_issues=repo_info.get("closed_issues", 0),
                            open_pull_requests=repo_info.get("open_pull_requests", 0),
                            total_issues=repo_info.get("total_issues", 0),
                            contributor_count=repo_info.get("contributor_count", 0),
                            commit_count=repo_info.get("commit_count", 0),
                            release_name=repo_info.get("release_name", ""),
                            release_datetime=self.parse_date_safely(repo_info.get("release_datetime")),
                            is_owasp_repo=True,
                        )

                        # Add to new projects list for Slack notification
                        new_projects.append(
                            {
                                "name": project_name,
                                "url": repo_url,
                                "description": repo_data.get("description", ""),
                                "stars": repo_info.get("stars", 0),
                                "language": repo_info.get("primary_language", "N/A"),
                            }
                        )

                        # Handle contributors
                        contributors_data = self.fetch_contributors_data(
                            repo_url,
                            headers,
                            delay_on_rate_limit,
                            max_rate_limit_retries,
                        )
                        if contributors_data:
                            self.handle_contributors(repo, contributors_data)

                        # Fetch and save logo
                        if repo_info.get("logo_url"):
                            self.fetch_and_save_logo(project, repo_info["logo_url"], headers)

                    self.stdout.write(self.style.SUCCESS(f"Successfully created project and repo: {project_name}"))

                except ValueError as ve:
                    self.stderr.write(self.style.ERROR(f"Validation error for {repo_url}: {str(ve)}"))
                    continue
                except IntegrityError as ie:
                    self.stderr.write(self.style.ERROR(f"Database integrity error for {repo_url}: {str(ie)}"))
                    continue
                except requests.RequestException as req_exc:
                    self.stderr.write(self.style.WARNING(f"Network error while processing {repo_url}: {str(req_exc)}"))
                    continue
                except CommandError as ce:
                    self.stderr.write(self.style.ERROR(f"Command execution error for {repo_url}: {str(ce)}"))
                    continue

        # Send Slack notification if new projects were found and Slack webhook is configured
        if new_projects and slack_webhook_url:
            self.send_slack_notification(new_projects, slack_webhook_url)

    def fetch_all_repos(self, headers, per_page=100):
        """Fetch www-project repositories from OWASP using GitHub Search API"""
        all_repos = []
        page = 1

        while True:
            # Using GitHub Search API to specifically find www-project repos in OWASP org
            search_query = "org:OWASP www-project in:name"
            url = f"https://api.github.com/search/repositories?q={search_query}&per_page={per_page}&page={page}"

            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code != 200:
                    self.stderr.write(self.style.ERROR(f"Error: API returned status {response.status_code}"))
                    break

                data = response.json()
                if not data.get("items"):
                    break

                all_repos.extend(data["items"])

                # Check if we've received all items
                if len(all_repos) >= data["total_count"]:
                    break

                page += 1

            except requests.exceptions.RequestException as e:
                self.stderr.write(self.style.ERROR(f"Error fetching repos: {str(e)}"))
                break

        return all_repos

    def fetch_github_repo_data(self, repo_url, headers, delay, max_retries, is_wiki=False, is_main=False):
        match = re.match(r"https://github.com/([^/]+/[^/]+)", repo_url)
        if not match:
            return None

        def api_get(url):
            for i in range(max_retries):
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code in (403, 429):  # Rate limit or forbidden
                        self.stderr.write(self.style.WARNING(f"Rate limit hit for {url}. Attempt {i+1}/{max_retries}"))
                        time.sleep(delay)
                        continue
                    return response
                except requests.exceptions.RequestException as e:
                    self.stderr.write(
                        self.style.WARNING(f"Request failed for {url}: {str(e)}. Attempt {i+1}/{max_retries}")
                    )
                    time.sleep(delay)
                    continue
            # After max retries, return None instead of raising exception
            self.stderr.write(self.style.WARNING(f"Failed to fetch {url} after {max_retries} attempts"))
            return None

        # Main repo data
        full_name = match.group(1)
        url = f"https://api.github.com/repos/{full_name}"
        response = api_get(url)

        if response is None or response.status_code != 200:
            return None

        try:
            repo_data = response.json()
        except ValueError as ve:
            self.stderr.write(self.style.WARNING(f"Invalid JSON response from {url}: {str(ve)}"))
            return None
        except requests.RequestException as req_exc:
            self.stderr.write(self.style.WARNING(f"Request failed for {url}: {str(req_exc)}"))
            return None

        full_name = repo_data.get("full_name")

        # Safely parse all date fields
        last_updated = self.parse_date_safely(repo_data.get("updated_at"))
        last_commit_date = self.parse_date_safely(repo_data.get("pushed_at"))
        created_date = self.parse_date_safely(repo_data.get("created_at"))
        modified_date = self.parse_date_safely(repo_data.get("updated_at"))

        data = {
            "name": repo_data.get("name"),
            "description": repo_data.get("description", ""),
            "repo_url": repo_url,
            "homepage_url": repo_data.get("homepage", ""),
            "is_wiki": is_wiki,
            "is_main": is_main,
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "last_updated": last_updated,
            "watchers": repo_data.get("watchers_count", 0),
            "primary_language": repo_data.get("language", ""),
            "license": (repo_data.get("license", {}).get("name") if repo_data.get("license") else None),
            "last_commit_date": last_commit_date,
            "created": created_date,
            "modified": modified_date,
            "network_count": repo_data.get("network_count", 0),
            "subscribers_count": repo_data.get("subscribers_count", 0),
            "size": repo_data.get("size", 0),
            "logo_url": repo_data.get("owner", {}).get("avatar_url", ""),
        }

        def get_issue_count(query):
            search_url = f"https://api.github.com/search/issues?q=repo:{full_name}+{query}"
            resp = api_get(search_url)
            if resp.status_code == 200:
                return resp.json().get("total_count", 0)
            return 0

        data["open_issues"] = get_issue_count("type:issue+state:open")
        data["closed_issues"] = get_issue_count("type:issue+state:closed")
        data["open_pull_requests"] = get_issue_count("type:pr+state:open")
        data["total_issues"] = data["open_issues"] + data["closed_issues"]

        releases_url = f"https://api.github.com/repos/{full_name}/releases/latest"
        release_resp = api_get(releases_url)
        if release_resp.status_code == 200:
            release_info = release_resp.json()
            data["release_name"] = release_info.get("name") or release_info.get("tag_name")
            data["release_datetime"] = self.parse_date_safely(release_info.get("published_at"))

        commit_count, contributor_data_list = self.compute_commit_count_and_contributors(
            full_name, headers, delay, max_retries
        )
        data["contributor_count"] = len(contributor_data_list)
        data["commit_count"] = commit_count

        return data

    def compute_commit_count_and_contributors(self, full_name, headers, delay, max_retries):
        def api_get(url):
            for i in range(max_retries):
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                except requests.exceptions.RequestException:
                    time.sleep(delay)
                    continue
                if response.status_code in (403, 429):
                    time.sleep(delay)
                    continue
                return response

        commit_count = 0
        all_contributors = []
        page = 1
        while True:
            contrib_url = f"https://api.github.com/repos/{full_name}/contributors?anon=true&per_page=100&page={page}"
            c_resp = api_get(contrib_url)
            if c_resp.status_code != 200:
                break
            contributors_data = c_resp.json()
            if not contributors_data:
                break
            commit_count += sum(c.get("contributions", 0) for c in contributors_data)
            all_contributors.extend(contributors_data)
            page += 1
        return commit_count, all_contributors

    def fetch_contributors_data(self, repo_url, headers, delay, max_retries):
        match = re.match(r"https://github.com/([^/]+)/([^/]+)/?", repo_url)
        if not match:
            return None

        def api_get(url):
            for i in range(max_retries):
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code in (403, 429):
                        self.stderr.write(self.style.WARNING(f"Rate limit hit for {url}. Attempt {i+1}/{max_retries}"))
                        time.sleep(delay)
                        continue
                    return response
                except requests.exceptions.RequestException as e:
                    self.stderr.write(
                        self.style.WARNING(f"Request failed for {url}: {str(e)}. Attempt {i+1}/{max_retries}")
                    )
                    time.sleep(delay)
                    continue
            return None

        owner, repo_name = match.groups()
        full_name = f"{owner}/{repo_name}"

        all_contributors = []
        page = 1
        while True:
            contrib_url = f"https://api.github.com/repos/{full_name}/contributors?anon=true&per_page=100&page={page}"
            response = api_get(contrib_url)

            if response is None or response.status_code != 200:
                break

            try:
                contributors_data = response.json()
                if not contributors_data:
                    break
                all_contributors.extend(contributors_data)
                page += 1
            except ValueError:
                self.stderr.write(self.style.WARNING(f"Invalid JSON response from {contrib_url}"))
                break

        return all_contributors if all_contributors else None

    def fetch_and_save_logo(self, project, project_logo_url, headers):
        """Fetch and save logo from GitHub repository"""
        try:
            if project_logo_url:
                response = requests.get(project_logo_url, headers=headers)
                if response.status_code == 200:
                    # Create a ContentFile from the response content
                    logo_content = ContentFile(response.content)
                    # Generate filename from project slug
                    filename = f"{project.slug}_logo.png"
                    # Save the file to project's logo field
                    project.logo.save(filename, logo_content, save=True)
                    return True

            return False
        except requests.RequestException as re:
            self.stderr.write(self.style.WARNING(f"Network error fetching logo: {str(re)}"))
            return False
        except IOError as ioe:
            self.stderr.write(self.style.WARNING(f"File system error saving logo: {str(ioe)}"))
            return False

    def handle_contributors(self, repo_instance, contributors_data):
        """Process and assign contributors to a repository"""
        if not contributors_data:
            return

        contributor_instances = []

        for contributor in contributors_data:
            github_id = contributor.get("id")
            if not github_id:
                continue

            # Try to get existing contributor or create new one
            contributor_obj, created = Contributor.objects.get_or_create(
                github_id=github_id,
                defaults={
                    "name": contributor.get("login", ""),
                    "github_url": contributor.get("html_url", ""),
                    "avatar_url": contributor.get("avatar_url", ""),
                    "contributor_type": contributor.get("type", "User"),
                    "contributions": contributor.get("contributions", 0),
                },
            )

            # Update contributor data even if it exists
            if not created:
                contributor_obj.name = contributor.get("login", contributor_obj.name)
                contributor_obj.github_url = contributor.get("html_url", contributor_obj.github_url)
                contributor_obj.avatar_url = contributor.get("avatar_url", contributor_obj.avatar_url)
                contributor_obj.contributor_type = contributor.get("type", contributor_obj.contributor_type)
                contributor_obj.contributions = contributor.get("contributions", contributor_obj.contributions)
                contributor_obj.save()

            contributor_instances.append(contributor_obj)
            self.stdout.write(self.style.SUCCESS(f"   -> Added/Updated Contributor: {contributor_obj.name}"))
        # Assign all contributors to the repo
        repo_instance.contributor.add(*contributor_instances)

        self.stdout.write(
            self.style.SUCCESS(f"Added {len(contributor_instances)} contributors to {repo_instance.name}")
        )

    def send_slack_notification(self, new_projects, webhook_url):
        """Send notification to Slack about newly imported projects"""

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🎉 New OWASP Projects Detected and Imported!",
                },
            }
        ]

        for project in new_projects:
            project_block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*<{project['url']}|{project['name']}>*\n"
                        f"_{project['description']}_\n"
                        f"Stars: {project['stars']} | Language: {project['language']}"
                    ),
                },
            }
            blocks.append(project_block)
            # Add divider after each project except the last one
            if project != new_projects[-1]:
                blocks.append({"type": "divider"})

        message = {
            "text": f"Found {len(new_projects)} new OWASP projects!",
            "blocks": blocks,
        }

        try:
            response = requests.post(webhook_url, json=message)
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS("Successfully sent Slack notification"))
            else:
                self.stderr.write(
                    self.style.WARNING(f"Failed to send Slack notification. Status code: {response.status_code}")
                )
        except requests.RequestException as re:
            self.stderr.write(self.style.ERROR(f"Network error sending Slack notification: {str(re)}"))
        except ValueError as ve:
            self.stderr.write(self.style.ERROR(f"Invalid message format for Slack: {str(ve)}"))
