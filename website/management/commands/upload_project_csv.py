import csv
import re
import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.template.defaultfilters import slugify
from django.utils.dateparse import parse_datetime

from website.models import AdditionalRepo, Contributor, Project, Tag


class RateLimitException(Exception):
    pass


class Command(BaseCommand):
    help = "Upload project details from a CSV file and fetch additional data from GitHub."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            required=True,
            help="Path to the CSV file containing project data",
        )
        parser.add_argument(
            "--delay-on-rate-limit",
            type=int,
            default=60,
            help="Number of seconds to wait if rate limit is reached before retrying",
        )
        parser.add_argument(
            "--max-rate-limit-retries",
            type=int,
            default=5,
            help="Number of times to retry after hitting rate limits",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        delay_on_rate_limit = options["delay_on_rate_limit"]
        max_rate_limit_retries = options["max_rate_limit_retries"]

        # Check if GITHUB_TOKEN is set
        if not getattr(settings, "GITHUB_TOKEN", None):
            self.stderr.write(
                self.style.ERROR("GITHUB_TOKEN is not configured in settings. Aborting.")
            )
            return

        headers = {
            "Authorization": f"token {settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        }

        self.stdout.write(self.style.NOTICE(f"Starting import from {csv_file}..."))

        try:
            with open(csv_file, newline="", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except FileNotFoundError as e:
            self.stderr.write(self.style.ERROR(f"CSV file not found: {e}"))
            return
        except PermissionError as e:
            self.stderr.write(self.style.ERROR(f"Permission error reading CSV file: {e}"))
            return
        except OSError as e:
            self.stderr.write(self.style.ERROR(f"OS error reading CSV file: {e}"))
            return

        header_index = None
        for i, line in enumerate(lines):
            if line.startswith("Name,Level,Activity"):
                header_index = i
                break

        if header_index is None:
            self.stderr.write(self.style.ERROR("No valid header line found in the CSV."))
            return

        lines = lines[header_index:]

        try:
            reader = csv.DictReader(lines)
        except csv.Error as e:
            self.stderr.write(self.style.ERROR(f"Error parsing CSV lines: {e}"))
            return

        project_count = 0

        for row_index, row in enumerate(reader, start=1):
            # Extract fields from CSV
            repo_url = row.get("Repo", "").strip()
            website_url = row.get("Website URL", "").strip()
            project_level = row.get("Level", "").strip()
            activity_status = row.get("Activity", "").strip()
            code_urls = row.get("Code URL", "").strip()
            external_links_csv = row.get("External Links", "").strip()
            project_type_csv = row.get("Type", "").strip()
            license = row.get("License(s)", "").strip()

            self.stdout.write(
                self.style.NOTICE(f"Processing row {row_index}: Repo name: {repo_url}")
            )

            if repo_url and not repo_url.startswith("https://github.com/"):
                repo_url = f"https://github.com/OWASP/{repo_url}"

            # Validate main repo URL
            if not repo_url or not repo_url.startswith("https://github.com/"):
                self.stderr.write(
                    self.style.WARNING(
                        f"Skipping row {row_index} due to invalid Repo URL: {repo_url}"
                    )
                )
                continue

            project_types = [pt.strip() for pt in project_type_csv.split(",") if pt.strip()]
            external_links_list = [
                l.strip() for l in re.split(r"[\n,]+", external_links_csv) if l.strip()
            ]

            try:
                main_repo_data = self.fetch_github_repo_data(
                    repo_url, headers, delay_on_rate_limit, max_rate_limit_retries
                )
            except RateLimitException:
                self.stderr.write(
                    self.style.ERROR(
                        f"Rate limit exceeded even after retries for {repo_url}, aborting..."
                    )
                )
                return
            except requests.exceptions.RequestException as e:
                self.stderr.write(
                    self.style.WARNING(
                        f"Network error while fetching data for {repo_url}: {e}. Skipping."
                    )
                )
                continue
            except ValueError as e:
                # Handles possible JSON decode errors or other value errors
                self.stderr.write(
                    self.style.WARNING(f"Value error fetching data for {repo_url}: {e}. Skipping.")
                )
                continue

            if not main_repo_data:
                self.stderr.write(
                    self.style.WARNING(
                        f"Could not retrieve main repo data for {repo_url}. Skipping."
                    )
                )
                continue

            with transaction.atomic():
                slug = (
                    main_repo_data["name"].lower() if main_repo_data.get("name") else "unnamed-repo"
                )
                slug = slug.replace(".", "-")
                if len(slug) > 50:
                    slug = slugify(slug[:50])

                if not slug:
                    slug = f"project-{int(time.time())}"

                project, created = Project.objects.get_or_create(
                    slug=slug,
                    defaults={
                        "name": main_repo_data.get("name", "Unnamed Project"),
                        "github_url": repo_url,
                        "description": main_repo_data.get("description")
                        or main_repo_data.get("name", ""),
                        "logo_url": main_repo_data.get("owner_avatar_url", ""),
                    },
                )

                project.activity_status = activity_status or project.activity_status
                project.project_lavel = project_level or project.project_lavel
                project.project_type = project_types if project_types else project.project_type

                if website_url:
                    project.wiki_url = website_url
                else:
                    if main_repo_data.get("html_url"):
                        project.wiki_url = main_repo_data["html_url"]

                current_external_links = set(project.external_links or [])
                for link in external_links_list:
                    current_external_links.add(link)
                project.external_links = list(current_external_links)

                project.homepage_url = main_repo_data.get("homepage")
                project.stars = main_repo_data.get("stargazers_count", 0)
                project.forks = main_repo_data.get("forks_count", 0)
                project.watchers = main_repo_data.get("subscribers_count", 0)
                project.network_count = main_repo_data.get("network_count", 0)
                project.subscribers_count = main_repo_data.get("subscribers_count", 0)
                project.primary_language = main_repo_data.get("language")
                if main_repo_data.get("license") is None:
                    project.license = license
                else:
                    project.license = main_repo_data.get("license")
                project.created_at = parse_datetime(main_repo_data.get("created_at"))
                project.updated_at = parse_datetime(main_repo_data.get("updated_at"))
                project.size = main_repo_data.get("size", 0)
                project.last_commit_date = parse_datetime(main_repo_data.get("pushed_at"))
                project.open_issues = main_repo_data.get("open_issues", 0)
                project.closed_issues = main_repo_data.get("closed_issues", 0)
                project.total_issues = main_repo_data.get("total_issues", 0)
                project.open_pull_requests = main_repo_data.get("open_pull_requests", 0)
                project.commit_count = main_repo_data.get("commit_count", 0)
                project.contributor_count = main_repo_data.get("contributor_count", 0)
                project.release_name = main_repo_data.get("release_name")
                release_datetime = main_repo_data.get("release_datetime")
                project.release_datetime = (
                    parse_datetime(release_datetime) if release_datetime else None
                )

                project.save()

                if project_types:
                    for tname in project_types:
                        tag_slug = slugify(tname)
                        tag, _ = Tag.objects.get_or_create(slug=tag_slug, defaults={"name": tname})
                        project.tags.add(tag)

                self.stdout.write(
                    self.style.SUCCESS(f"Updated main project: {project.name} ({repo_url})")
                )

                # Fetch and update contributors for the main project
                main_contributors = None
                try:
                    main_contributors = self.fetch_contributors_data(
                        repo_url, headers, delay_on_rate_limit, max_rate_limit_retries
                    )
                except requests.exceptions.RequestException as e:
                    self.stderr.write(
                        self.style.WARNING(
                            f"Network error fetching contributors for {repo_url}: {e}"
                        )
                    )
                except RateLimitException:
                    self.stderr.write(
                        self.style.WARNING(
                            f"Rate limit hit while fetching contributors for {repo_url}"
                        )
                    )
                except ValueError as e:
                    self.stderr.write(
                        self.style.WARNING(f"Value error fetching contributors for {repo_url}: {e}")
                    )

                if main_contributors is not None:
                    self.update_contributors_for_entity(project, main_contributors)

                # Handle Additional Repos from "Code URL"
                if code_urls:
                    additional_urls = [
                        cu.strip() for cu in re.split(r"[,\n]+", code_urls) if cu.strip()
                    ]

                    for add_url in additional_urls:
                        if not add_url.startswith("https://github.com/"):
                            self.stderr.write(
                                self.style.WARNING(
                                    f"Invalid Additional Repo URL: {add_url}, skipping."
                                )
                            )
                            continue

                        try:
                            add_repo_data = self.fetch_github_repo_data(
                                add_url, headers, delay_on_rate_limit, max_rate_limit_retries
                            )
                        except RateLimitException:
                            self.stderr.write(
                                self.style.ERROR(
                                    f"Rate limit exceeded when fetching additional repo {add_url}. Skipping this repo."
                                )
                            )
                            continue
                        except requests.exceptions.RequestException as e:
                            self.stderr.write(
                                self.style.WARNING(
                                    f"Network error while fetching data for {add_url}: {e}. Skipping."
                                )
                            )
                            continue
                        except ValueError as e:
                            self.stderr.write(
                                self.style.WARNING(
                                    f"Value error fetching data for {add_url}: {e}. Skipping."
                                )
                            )
                            continue

                        if not add_repo_data:
                            self.stderr.write(
                                self.style.WARNING(
                                    f"Additional repo not found or inaccessible: {add_url}"
                                )
                            )
                            continue

                        add_slug = (
                            add_repo_data["name"].lower()
                            if add_repo_data.get("name")
                            else "unnamed-add-repo"
                        )
                        add_slug = add_slug.replace(".", "-")
                        if len(add_slug) > 50:
                            add_slug = slugify(add_slug[:50])

                        if not add_slug:
                            add_slug = f"additional-repo-{int(time.time())}"

                        additional_repo, add_created = AdditionalRepo.objects.get_or_create(
                            project=project,
                            slug=add_slug,
                            defaults={
                                "name": add_repo_data.get("name", "Unnamed Repo"),
                                "github_url": add_url,
                                "description": add_repo_data.get("description")
                                or add_repo_data.get("name", ""),
                                "logo_url": add_repo_data.get("owner_avatar_url", ""),
                            },
                        )

                        additional_repo.homepage_url = add_repo_data.get("homepage")
                        additional_repo.stars = add_repo_data.get("stargazers_count", 0)
                        additional_repo.forks = add_repo_data.get("forks_count", 0)
                        additional_repo.watchers = add_repo_data.get("subscribers_count", 0)
                        additional_repo.network_count = add_repo_data.get("network_count", 0)
                        additional_repo.subscribers_count = add_repo_data.get(
                            "subscribers_count", 0
                        )
                        additional_repo.primary_language = add_repo_data.get("language")
                        additional_repo.license = add_repo_data.get("license")
                        additional_repo.created_at = parse_datetime(add_repo_data.get("created_at"))
                        additional_repo.updated_at = parse_datetime(add_repo_data.get("updated_at"))
                        additional_repo.size = add_repo_data.get("size", 0)
                        additional_repo.last_commit_date = parse_datetime(
                            add_repo_data.get("pushed_at")
                        )
                        additional_repo.open_issues = add_repo_data.get("open_issues", 0)
                        additional_repo.closed_issues = add_repo_data.get("closed_issues", 0)
                        additional_repo.total_issues = add_repo_data.get("total_issues", 0)
                        additional_repo.open_pull_requests = add_repo_data.get(
                            "open_pull_requests", 0
                        )
                        additional_repo.commit_count = add_repo_data.get("commit_count", 0)
                        additional_repo.contributor_count = add_repo_data.get("contributor_count", 0)
                        additional_repo.release_name = add_repo_data.get("release_name")
                        release_datetime = add_repo_data.get("release_datetime")
                        additional_repo.release_datetime = (
                            parse_datetime(release_datetime) if release_datetime else None
                        )


                        additional_repo.save()

                        add_contributors = None
                        try:
                            add_contributors = self.fetch_contributors_data(
                                add_url, headers, delay_on_rate_limit, max_rate_limit_retries
                            )
                        except requests.exceptions.RequestException as e:
                            self.stderr.write(
                                self.style.WARNING(
                                    f"Network error fetching contributors for {add_url}: {e}"
                                )
                            )
                        except RateLimitException:
                            self.stderr.write(
                                self.style.WARNING(
                                    f"Rate limit hit while fetching contributors for {add_url}"
                                )
                            )
                        except ValueError as e:
                            self.stderr.write(
                                self.style.WARNING(
                                    f"Value error fetching contributors for {add_url}: {e}"
                                )
                            )

                        if add_contributors is not None:
                            self.update_contributors_for_entity(additional_repo, add_contributors)

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"   -> Added/Updated AdditionalRepo: {additional_repo.name} ({add_url})"
                            )
                        )

            project_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Import completed. Processed {project_count} projects.")
        )

    def fetch_github_repo_data(self, repo_url, headers, delay, max_retries):
        """
        Fetch all necessary GitHub repo details including:
        - Basic info (stars, forks, language, etc.)
        - Issues and PR counts
        - Latest release info
        - Commit count (from contributors endpoint)
        Uses rate-limit handling and retries.

        Returns a dictionary with all needed fields or None if repo not found.
        """
        match = re.match(r"https://github.com/([^/]+/[^/]+)", repo_url)
        if not match:
            return None

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
            raise RateLimitException("Exceeded max retries due to rate limits.")

        full_name = match.group(1)
        url = f"https://api.github.com/repos/{full_name}"
        response = api_get(url)
        if response.status_code == 404:
            return None
        elif response.status_code != 200:
            return None

        repo_data = response.json()
        full_name = repo_data.get("full_name")
        data = {
            "name": repo_data.get("name"),
            "description": repo_data.get("description", ""),
            "homepage": repo_data.get("homepage", ""),
            "stargazers_count": repo_data.get("stargazers_count", 0),
            "forks_count": repo_data.get("forks_count", 0),
            "subscribers_count": repo_data.get("subscribers_count", 0),
            "network_count": repo_data.get("network_count", 0),
            "language": repo_data.get("language", ""),
            "size": repo_data.get("size", 0),
            "owner_avatar_url": repo_data.get("owner", {}).get("avatar_url", ""),
            "created_at": repo_data.get("created_at", ""),
            "updated_at": repo_data.get("updated_at", ""),
            "pushed_at": repo_data.get("pushed_at", ""),
            "license": repo_data.get("license", {}).get("name")
            if repo_data.get("license")
            else None,
            "html_url": repo_data.get("html_url"),
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
            raise RateLimitException("Exceeded max retries due to rate limits.")

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
        owner, repo_name = match.groups()
        full_name = f"{owner}/{repo_name}"

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
            raise RateLimitException("Exceeded max retries due to rate limits.")

        all_contributors = []
        page = 1
        while True:
            contrib_url = f"https://api.github.com/repos/{full_name}/contributors?anon=true&per_page=100&page={page}"
            c_resp = api_get(contrib_url)
            if c_resp.status_code == 404:
                return None
            if c_resp.status_code != 200:
                self.stderr.write(
                    self.style.WARNING(
                        f"Failed to fetch contributors for {full_name}: {c_resp.status_code}"
                    )
                )
                break

            contributors_data = c_resp.json()
            if not contributors_data:
                break
            all_contributors.extend(contributors_data)
            page += 1

        return all_contributors

    def update_contributors_for_entity(self, entity, contributors_data):
        contributor_ids = []
        for c in contributors_data:
            github_id = c.get("id")
            if not github_id:
                continue
            name = c.get("login", "")
            github_url = c.get("html_url", "")
            avatar_url = c.get("avatar_url", "")
            contributor_type = c.get("type", "User")
            contributions = c.get("contributions", 0)

            contributor_obj, _ = Contributor.objects.get_or_create(
                github_id=github_id,
                defaults={
                    "name": name,
                    "github_url": github_url,
                    "avatar_url": avatar_url,
                    "contributor_type": contributor_type,
                    "contributions": contributions,
                },
            )
            contributor_obj.name = name
            contributor_obj.github_url = github_url
            contributor_obj.avatar_url = avatar_url
            contributor_obj.contributor_type = contributor_type
            contributor_obj.contributions = contributions
            contributor_obj.save()

            contributor_ids.append(contributor_obj.id)

        entity.contributors.set(contributor_ids)
        entity.save()
        self.stdout.write(
            self.style.SUCCESS(
                f"   -> Updated contributors for {entity.__class__.__name__} '{entity}' with {len(contributor_ids)} contributors."
            )
        )
