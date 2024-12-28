import csv
import re
import time

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, models, transaction
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify

from website.models import Contributor, Organization, Project, Repo, Tag


class Command(BaseCommand):
    help = "Upload project and repository details from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            required=True,
            help="Path to the CSV file containing project data.",
        )
        parser.add_argument(
            "--delay-on-rate-limit",
            type=int,
            default=60,
            help="Seconds to wait if GitHub API rate limit is reached before retrying.",
        )
        parser.add_argument(
            "--max-rate-limit-retries",
            type=int,
            default=5,
            help="Maximum number of retries after hitting rate limits.",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        delay_on_rate_limit = options["delay_on_rate_limit"]
        max_rate_limit_retries = options["max_rate_limit_retries"]

        # Check if GITHUB_TOKEN is set
        github_token = getattr(settings, "GITHUB_TOKEN", None)
        if not github_token:
            self.stderr.write(
                self.style.ERROR("GITHUB_TOKEN is not configured in settings. Aborting.")
            )
            return

        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        # Check if OWASP organization exists
        try:
            org = Organization.objects.get(name__iexact="OWASP")
            self.stdout.write(self.style.SUCCESS(f"Found Organization: {org.name}"))
        except Organization.DoesNotExist:
            self.stderr.write(self.style.ERROR("Organization 'OWASP' does not exist. Aborting."))
            return

        # Prompt user for confirmation
        confirm = (
            input(f"Do you want to add projects to the organization '{org.name}'? (yes/no): ")
            .strip()
            .lower()
        )
        if confirm not in ["yes", "y"]:
            self.stdout.write(self.style.WARNING("Operation cancelled by the user."))
            return

        # Validate and read CSV file
        try:
            with open(csv_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                required_fields = ["Name", "Tag", "License(s)", "Repo", "Website URL", "Code URL"]
                for field in required_fields:
                    if field not in reader.fieldnames:
                        raise CommandError(f"Missing required field in CSV: {field}")
                rows = list(reader)
        except FileNotFoundError:
            raise CommandError(f"CSV file not found: {csv_file}")
        except PermissionError:
            raise CommandError(f"Permission denied when accessing the CSV file: {csv_file}")
        except csv.Error as e:
            raise CommandError(f"Error reading CSV file: {e}")

        if not rows:
            self.stdout.write(self.style.WARNING("CSV file is empty. No projects to add."))
            return

        self.stdout.write(
            self.style.NOTICE(f"Processing {len(rows)} projects from the CSV file...")
        )

        project_count = 0

        def clean_github_url(url):
            """Remove hash fragments and query parameters from GitHub URLs"""
            if not url:
                return url
            # Remove hash fragment
            url = url.split("#")[0]
            # Remove query parameters
            url = url.split("?")[0]
            # Remove trailing slashes
            url = url.rstrip("/")
            return url

        for row_index, row in enumerate(rows, start=1):
            # Extract fields from CSV
            name = row.get("Name", "").strip()
            tag_csv = row.get("Tag", "").strip()
            tag_names = [tag.strip() for tag in tag_csv.split(",") if tag.strip()]
            license_csv = row.get("License(s)", "").strip()
            repo_field = row.get("Repo", "").strip()
            website_url = row.get("Website URL", "").strip()
            code_urls_csv = row.get("Code URL", "").strip()
            code_urls = [
                clean_github_url(url.strip())
                for url in re.split(r"[,\n]+", code_urls_csv)
                if url.strip()
            ]
            # Filter out any empty strings after cleaning
            code_urls = [url for url in code_urls if url]
            # Remove duplicates that might occur after cleaning URLs
            code_urls = list(dict.fromkeys(code_urls))
            twitter = row.get("Twitter", "").strip()
            facebook = row.get("Facebook", "").strip()

            self.stdout.write(self.style.NOTICE(f"Processing row {row_index}: Repo={repo_field}"))

            # Derive GitHub repo URL
            if repo_field.startswith("https://github.com/"):
                repo_url = repo_field
            else:
                repo_url = f"https://github.com/OWASP/{repo_field}"

            # Validate GitHub repo existence
            if not self.validate_github_repo(
                repo_url, headers, delay_on_rate_limit, max_rate_limit_retries
            ):
                self.stderr.write(
                    self.style.WARNING(
                        f"Invalid or inaccessible Repo URL: {repo_url}. Skipping row {row_index}."
                    )
                )
                continue

            # Fetch complete GitHub repo data
            repo_info = self.fetch_github_repo_data(
                repo_url,
                headers,
                delay_on_rate_limit,
                max_rate_limit_retries,
                is_wiki=True,
                is_main=False,
            )
            if not repo_info:
                self.stderr.write(
                    self.style.WARNING(
                        f"Failed to fetch complete data for {repo_url}. Skipping row {row_index}."
                    )
                )
                continue

            # Determine Project name
            project_name = name if name else repo_info.get("name", "Unnamed Project")

            # Generate unique slug
            project_slug = slugify(project_name)
            project_slug = project_slug.replace(".", "-")
            if len(project_slug) > 50:
                project_slug = project_slug[:50]
            if not project_slug:
                project_slug = f"project-{int(time.time())}"

            if Project.objects.filter(slug=project_slug).exists():
                base_slug = project_slug
                counter = 1
                while Project.objects.filter(slug=project_slug).exists():
                    suffix = f"-{counter}"
                    # Make sure base_slug + suffix doesn't exceed 50 chars
                    if len(base_slug) + len(suffix) > 50:
                        base_slug = base_slug[: 50 - len(suffix)]
                    project_slug = f"{base_slug}{suffix}"
                    counter += 1

            # Validate and set Website URL
            if website_url:
                if not website_url.startswith("http://") and not website_url.startswith("https://"):
                    website_url = f"http://{website_url}"

            # Handle Tags
            tag_instances = []
            for tag_name in tag_names:
                tag_slug = slugify(tag_name)
                tag, created = Tag.objects.get_or_create(slug=tag_slug, defaults={"name": tag_name})
                tag_instances.append(tag)

            with transaction.atomic():
                # Check if project already exists by URL or slug
                if Project.objects.filter(
                    models.Q(url=website_url)
                    | models.Q(url=repo_info.get("html_url"))
                    | models.Q(slug=project_slug)
                ).exists():
                    self.stdout.write(
                        self.style.WARNING(
                            f"Project already exists with URL {website_url or repo_info.get('html_url')}. Skipping..."
                        )
                    )
                    continue

                try:
                    project = Project.objects.create(
                        slug=project_slug,
                        name=project_name,
                        description=repo_info.get("description", ""),
                        url=website_url if website_url else repo_info.get("html_url"),
                        twitter=twitter,
                        facebook=facebook,
                        logo="",  # Initialize empty, will be set by fetch_and_save_logo
                        organization=org,
                    )
                except IntegrityError:
                    self.stdout.write(
                        self.style.WARNING(
                            "Failed to create project due to duplicate data. Skipping..."
                        )
                    )
                    continue

                # Fetch and save the logo
                project_logo_url = repo_info.get("logo_url", "")
                if self.fetch_and_save_logo(project, project_logo_url, headers):
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Successfully fetched and saved logo for {project.name}"
                        )
                    )
                else:
                    self.stdout.write(self.style.WARNING(f"No logo found for {project.name}"))

                self.stdout.write(
                    self.style.SUCCESS(f"Updated project: {project.name} ({repo_url})")
                )

                # Handle wiki repo
                try:
                    repo = Repo.objects.get(repo_url=repo_url)
                    self.stdout.write(
                        self.style.WARNING(
                            f"Wiki repo {repo_url} already exists. Skipping creation..."
                        )
                    )
                except Repo.DoesNotExist:
                    try:
                        repo = Repo.objects.create(
                            project=project,
                            slug=project_slug,
                            name=repo_info.get("name", ""),
                            description=repo_info.get("description", ""),
                            repo_url=repo_url,
                            homepage_url=repo_info.get("homepage_url", ""),
                            is_wiki=True,
                            is_main=False,
                            stars=repo_info.get("stars", 0),
                            forks=repo_info.get("forks", 0),
                            last_updated=parse_datetime(repo_info.get("last_updated"))
                            if repo_info.get("last_updated")
                            else None,
                            watchers=repo_info.get("watchers", 0),
                            primary_language=repo_info.get("primary_language", ""),
                            license=repo_info.get("license", ""),
                            last_commit_date=parse_datetime(repo_info.get("last_commit_date"))
                            if repo_info.get("last_commit_date")
                            else None,
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
                            release_datetime=parse_datetime(repo_info.get("release_datetime"))
                            if repo_info.get("release_datetime")
                            else None,
                        )
                    except IntegrityError:
                        self.stdout.write(
                            self.style.WARNING(
                                "Failed to create wiki repo due to duplicate data. Skipping..."
                            )
                        )
                        continue

                # Handle additional repos
                for idx, code_url in enumerate(code_urls, start=1):
                    if not code_url.startswith("https://github.com/"):
                        self.stderr.write(
                            self.style.WARNING(f"Invalid Code URL: {code_url}. Skipping.")
                        )
                        continue

                    # Validate Code Repo URL
                    if not self.validate_github_repo(
                        code_url, headers, delay_on_rate_limit, max_rate_limit_retries
                    ):
                        self.stderr.write(
                            self.style.WARNING(
                                f"Invalid or inaccessible Code Repo URL: {code_url}. Skipping."
                            )
                        )
                        continue

                    # Fetch the fetch_github_repo_data for the code repo and for the first one set is_main=True
                    code_repo_info = self.fetch_github_repo_data(
                        code_url,
                        headers,
                        delay_on_rate_limit,
                        max_rate_limit_retries,
                        is_wiki=False,
                        is_main=idx == 1,
                    )

                    if not code_repo_info:
                        self.stderr.write(
                            self.style.WARNING(
                                f"Failed to fetch complete data for {code_url}. Skipping."
                            )
                        )
                        continue

                    try:
                        code_repo = Repo.objects.get(repo_url=code_url)
                        self.stdout.write(
                            self.style.WARNING(
                                f"Code repo {code_url} already exists. Skipping creation..."
                            )
                        )
                        continue
                    except Repo.DoesNotExist:
                        try:
                            base_slug = slugify(code_repo_info["name"])
                            base_slug = base_slug.replace(".", "-")
                            if len(base_slug) > 50:
                                base_slug = base_slug[:50]
                            if not base_slug:
                                base_slug = f"repo-{int(time.time())}"

                            unique_slug = base_slug
                            counter = 1
                            while Repo.objects.filter(slug=unique_slug).exists():
                                suffix = f"-{counter}"
                                if len(base_slug) + len(suffix) > 50:
                                    base_slug = base_slug[: 50 - len(suffix)]
                                unique_slug = f"{base_slug}{suffix}"
                                counter += 1

                            code_repo = Repo.objects.create(
                                project=project,
                                slug=unique_slug,
                                name=code_repo_info["name"],
                                description=code_repo_info["description"],
                                repo_url=code_url,
                                homepage_url=code_repo_info["homepage_url"],
                                is_wiki=False,
                                is_main=idx == 1,
                                stars=code_repo_info["stars"],
                                forks=code_repo_info["forks"],
                                last_updated=parse_datetime(code_repo_info.get("last_updated"))
                                if code_repo_info.get("last_updated")
                                else None,
                                watchers=code_repo_info["watchers"],
                                primary_language=code_repo_info["primary_language"],
                                license=code_repo_info["license"],
                                last_commit_date=parse_datetime(
                                    code_repo_info.get("last_commit_date")
                                )
                                if code_repo_info.get("last_commit_date")
                                else None,
                                created=code_repo_info["created"],
                                modified=code_repo_info["modified"],
                                network_count=code_repo_info["network_count"],
                                subscribers_count=code_repo_info["subscribers_count"],
                                size=code_repo_info["size"],
                                logo_url=code_repo_info["logo_url"],
                                open_issues=code_repo_info["open_issues"],
                                closed_issues=code_repo_info["closed_issues"],
                                open_pull_requests=code_repo_info["open_pull_requests"],
                                total_issues=code_repo_info["total_issues"],
                                contributor_count=code_repo_info["contributor_count"],
                                commit_count=code_repo_info["commit_count"],
                                release_name=code_repo_info.get("release_name", ""),
                                release_datetime=parse_datetime(
                                    code_repo_info.get("release_datetime")
                                )
                                if code_repo_info.get("release_datetime")
                                else None,
                            )
                        except IntegrityError:
                            self.stdout.write(
                                self.style.WARNING(
                                    "Failed to create code repo due to duplicate data. Skipping..."
                                )
                            )
                            continue

                    # Add same tags to code repo
                    if tag_instances:
                        code_repo.tags.add(*tag_instances)

                    if not code_repo:
                        self.stderr.write(
                            self.style.WARNING(
                                f"Failed to create/update Code Repo for {code_url}. Skipping."
                            )
                        )
                        continue

                    # Handle contributors only for newly created repos
                    if code_repo:
                        code_contributors_data = self.fetch_contributors_data(
                            code_url, headers, delay_on_rate_limit, max_rate_limit_retries
                        )
                        if code_contributors_data:
                            self.handle_contributors(code_repo, code_contributors_data)

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"   -> Added/Updated Repo: {code_repo.name} ({code_url})"
                        )
                    )

            project_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Import completed. Processed {project_count} projects.")
        )

    def validate_github_repo(self, repo_url, headers, delay, max_retries):
        """Check if a GitHub repository exists."""
        api_url = self.convert_to_api_url(repo_url)
        if not api_url:
            return False

        for attempt in range(max_retries):
            try:
                response = requests.get(api_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    return True
                elif response.status_code in [403, 429]:
                    self.stderr.write(
                        self.style.WARNING(f"Rate limit reached. Waiting for {delay} seconds...")
                    )
                    time.sleep(delay)
                    continue
                elif response.status_code == 404:
                    return False
                else:
                    self.stderr.write(
                        self.style.WARNING(
                            f"Unexpected status code {response.status_code} for URL: {repo_url}"
                        )
                    )
                    return False
            except requests.exceptions.RequestException as e:
                self.stderr.write(
                    self.style.WARNING(
                        f"Network error while validating {repo_url}: {e}. Retrying in {delay} seconds..."
                    )
                )
                time.sleep(delay)
                continue
        return False

    def convert_to_api_url(self, repo_url):
        """Convert a GitHub repository URL to its corresponding API URL."""
        # Remove hash fragments and query parameters
        repo_url = repo_url.split("#")[0].split("?")[0].rstrip("/")
        match = re.match(r"https?://github\.com/([^/]+)/([^/]+)/?$", repo_url)
        if match:
            owner, repo = match.groups()
            return f"https://api.github.com/repos/{owner}/{repo}"
        else:
            self.stderr.write(self.style.WARNING(f"Invalid GitHub URL format: {repo_url}"))
            return None

    def fetch_github_repo_data(
        self, repo_url, headers, delay, max_retries, is_wiki=False, is_main=False
    ):
        match = re.match(r"https://github.com/([^/]+/[^/]+)", repo_url)
        if not match:
            return None

        def api_get(url):
            for i in range(max_retries):
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code in (403, 429):  # Rate limit or forbidden
                        self.stderr.write(
                            self.style.WARNING(
                                f"Rate limit hit for {url}. Attempt {i+1}/{max_retries}"
                            )
                        )
                        time.sleep(delay)
                        continue
                    return response
                except requests.exceptions.RequestException as e:
                    self.stderr.write(
                        self.style.WARNING(
                            f"Request failed for {url}: {str(e)}. Attempt {i+1}/{max_retries}"
                        )
                    )
                    time.sleep(delay)
                    continue
            # After max retries, return None instead of raising exception
            self.stderr.write(
                self.style.WARNING(f"Failed to fetch {url} after {max_retries} attempts")
            )
            return None

        # Main repo data
        full_name = match.group(1)
        url = f"https://api.github.com/repos/{full_name}"
        response = api_get(url)

        if response is None or response.status_code != 200:
            return None

        try:
            repo_data = response.json()
        except ValueError:
            self.stderr.write(self.style.WARNING(f"Invalid JSON response from {url}"))
            return None

        full_name = repo_data.get("full_name")
        data = {
            "name": repo_data.get("name"),
            "description": repo_data.get("description", ""),
            "repo_url": repo_url,
            "homepage_url": repo_data.get("homepage", ""),
            "is_wiki": is_wiki,
            "is_main": is_main,
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "last_updated": repo_data.get("updated_at"),
            "watchers": repo_data.get("watchers_count", 0),
            "primary_language": repo_data.get("language", ""),
            "license": repo_data.get("license", {}).get("name")
            if repo_data.get("license")
            else None,
            "last_commit_date": repo_data.get("pushed_at"),
            "created": repo_data.get("created_at", ""),
            "modified": repo_data.get("updated_at", ""),
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
            data["release_datetime"] = release_info.get("published_at")

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
                        self.stderr.write(
                            self.style.WARNING(
                                f"Rate limit hit for {url}. Attempt {i+1}/{max_retries}"
                            )
                        )
                        time.sleep(delay)
                        continue
                    return response
                except requests.exceptions.RequestException as e:
                    self.stderr.write(
                        self.style.WARNING(
                            f"Request failed for {url}: {str(e)}. Attempt {i+1}/{max_retries}"
                        )
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
        except Exception as e:
            self.stderr.write(self.style.WARNING(f"Error fetching logo: {str(e)}"))
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
                contributor_obj.avatar_url = contributor.get(
                    "avatar_url", contributor_obj.avatar_url
                )
                contributor_obj.contributor_type = contributor.get(
                    "type", contributor_obj.contributor_type
                )
                contributor_obj.contributions = contributor.get(
                    "contributions", contributor_obj.contributions
                )
                contributor_obj.save()

            contributor_instances.append(contributor_obj)
            self.stdout.write(
                self.style.SUCCESS(f"   -> Added/Updated Contributor: {contributor_obj.name}")
            )
        # Assign all contributors to the repo
        repo_instance.contributor.add(*contributor_instances)

        self.stdout.write(
            self.style.SUCCESS(
                f"Added {len(contributor_instances)} contributors to {repo_instance.name}"
            )
        )
