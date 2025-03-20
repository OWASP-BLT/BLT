import logging
import time
from datetime import datetime, timedelta

import requests
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

# GitHub API
GITHUB_API_BASE = "https://api.github.com"
GITHUB_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
}

if hasattr(settings, "GITHUB_TOKEN"):
    GITHUB_HEADERS["Authorization"] = f"token {settings.GITHUB_TOKEN}"

# Code quality API endpoints
CODECOV_API = "https://codecov.io/api/v2"
SONARQUBE_API = "https://sonarcloud.io/api"

# Social media API endpoints
TWITTER_API = "https://api.twitter.com/2"
LINKEDIN_API = "https://api.linkedin.com/v2"


@shared_task
def sync_all_repositories(force=False):
    """Sync all repositories' data from external sources"""
    from website.models import Repo

    repos = Repo.objects.all()
    logger.info(f"Starting sync for {repos.count()} repositories")

    for repo in repos:
        # Sync GitHub data
        if force or repo.needs_github_sync():
            sync_github_data.delay(repo.id)

        # Sync code quality data
        if force or repo.needs_quality_sync():
            sync_code_quality.delay(repo.id)

        # Sync social media data
        if force or repo.needs_social_sync():
            sync_social_media.delay(repo.id)

        # Sync download stats
        if force or repo.needs_downloads_sync():
            sync_package_downloads.delay(repo.id)

    logger.info("Repo sync tasks queued successfully")
    return True


@shared_task
def sync_github_data(repo_id):
    """Sync repo data from GitHub API"""
    from website.models import Repo

    try:
        repo = Repo.objects.get(id=repo_id)

        # Skip if not a GitHub repo
        if not repo.url or "github.com" not in repo.url:
            logger.info(f"Repo {repo.name} is not a GitHub repo, skipping.")
            return False

        # Extract owner/repo from GitHub URL
        parts = repo.url.rstrip("/").split("/")
        if len(parts) < 2:
            logger.error(f"Invalid GitHub URL for {repo.name}: {repo.url}")
            return False

        owner_repo = "/".join(parts[-2:])
        cache_key = f"github_repo_data_{owner_repo}"

        # Check cache first
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Using cached GitHub data for {repo.name}")
            repo_data = cached_data
        else:
            # Make API request with rate limit handling
            api_url = f"{GITHUB_API_BASE}/repos/{owner_repo}"
            response = requests.get(api_url, headers=GITHUB_HEADERS)

            if response.status_code == 403 and "rate limit exceeded" in response.text.lower():
                logger.warning("GitHub API rate limit exceeded, retrying in 60 seconds")
                time.sleep(60)
                response = requests.get(api_url, headers=GITHUB_HEADERS)

            if response.status_code != 200:
                logger.error(f"Failed to fetch data for {repo.name}: {response.status_code} - {response.text}")
                return False

            repo_data = response.json()

            # Cache the result for 1 hour
            cache.set(cache_key, repo_data, 3600)

        # Update basic repo data
        repo.stars = repo_data.get("stargazers_count", 0)
        repo.forks = repo_data.get("forks_count", 0)
        repo.open_issues = repo_data.get("open_issues_count", 0)
        repo.watchers = repo_data.get("watchers_count", 0)

        # Get additional data

        # 1. Contributors
        contributors_cache_key = f"github_contributors_{owner_repo}"
        contributors = cache.get(contributors_cache_key)

        if not contributors:
            contributors_url = f"{api_url}/contributors?per_page=100"
            contributors_resp = requests.get(contributors_url, headers=GITHUB_HEADERS)
            if contributors_resp.status_code == 200:
                contributors = contributors_resp.json()
                cache.set(contributors_cache_key, contributors, 3600)
                repo.contributors_count = len(contributors)
        else:
            repo.contributors_count = len(contributors)

        # 2. Pull Requests
        pulls_cache_key = f"github_pulls_{owner_repo}"
        pulls_data = cache.get(pulls_cache_key)

        if not pulls_data:
            # Just get stats, not all PRs
            pulls_url = f"{api_url}/pulls?state=all&per_page=1"
            pulls_resp = requests.get(pulls_url, headers=GITHUB_HEADERS)
            if pulls_resp.status_code == 200:
                # Get total from header
                if "Link" in pulls_resp.headers:
                    link_header = pulls_resp.headers["Link"]
                    if 'rel="last"' in link_header:
                        # Extract the last page number
                        last_page = link_header.split("page=")[-1].split("&")[0].split(">")[0]
                        repo.pull_requests = int(last_page)
                    else:
                        repo.pull_requests = 1  # Only one page

                # Get open PRs
                open_pulls_url = f"{api_url}/pulls?state=open&per_page=1"
                open_pulls_resp = requests.get(open_pulls_url, headers=GITHUB_HEADERS)
                if open_pulls_resp.status_code == 200 and "Link" in open_pulls_resp.headers:
                    link_header = open_pulls_resp.headers["Link"]
                    if 'rel="last"' in link_header:
                        last_page = link_header.split("page=")[-1].split("&")[0].split(">")[0]
                        repo.open_pull_requests = int(last_page)
                    else:
                        repo.open_pull_requests = 1  # Only one page

                pulls_data = {"total": repo.pull_requests, "open": repo.open_pull_requests}
                cache.set(pulls_cache_key, pulls_data, 3600)
        else:
            repo.pull_requests = pulls_data.get("total", 0)
            repo.open_pull_requests = pulls_data.get("open", 0)

        # 3. Issues and closed issues
        issues_cache_key = f"github_issues_{owner_repo}"
        issues_data = cache.get(issues_cache_key)

        if not issues_data:
            # Get closed issues count
            closed_issues_url = f"{api_url}/issues?state=closed&per_page=1"
            closed_issues_resp = requests.get(closed_issues_url, headers=GITHUB_HEADERS)
            if closed_issues_resp.status_code == 200 and "Link" in closed_issues_resp.headers:
                link_header = closed_issues_resp.headers["Link"]
                if 'rel="last"' in link_header:
                    last_page = link_header.split("page=")[-1].split("&")[0].split(">")[0]
                    repo.closed_issues = int(last_page)
                else:
                    repo.closed_issues = 1  # Only one page

            repo.total_issues = repo.open_issues + repo.closed_issues

            issues_data = {"total": repo.total_issues, "closed": repo.closed_issues, "open": repo.open_issues}
            cache.set(issues_cache_key, issues_data, 3600)
        else:
            repo.total_issues = issues_data.get("total", 0)
            repo.closed_issues = issues_data.get("closed", 0)
            repo.open_issues = issues_data.get("open", 0)

        # 4. Recent commits (last 30 days)
        commits_cache_key = f"github_commits_{owner_repo}"
        commits_data = cache.get(commits_cache_key)

        if not commits_data:
            # Get commit count for last 30 days
            since_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
            commits_url = f"{api_url}/commits?since={since_date}&per_page=100"
            commits_resp = requests.get(commits_url, headers=GITHUB_HEADERS)

            if commits_resp.status_code == 200:
                commits = commits_resp.json()
                repo.recent_commits = len(commits)

                # If there are potentially more commits, look at Link header
                if "Link" in commits_resp.headers and 'rel="next"' in commits_resp.headers["Link"]:
                    # This is a crude estimate - we'd need to follow all pages for exact count
                    repo.recent_commits = 100 + repo.recent_commits

                commits_data = {"recent": repo.recent_commits}
                cache.set(commits_cache_key, commits_data, 3600)
        else:
            repo.recent_commits = commits_data.get("recent", 0)

        # 5. Releases
        releases_cache_key = f"github_releases_{owner_repo}"
        releases_data = cache.get(releases_cache_key)

        if not releases_data:
            releases_url = f"{api_url}/releases?per_page=1"
            releases_resp = requests.get(releases_url, headers=GITHUB_HEADERS)

            if releases_resp.status_code == 200:
                releases = releases_resp.json()

                # Get release count from header
                if "Link" in releases_resp.headers and 'rel="last"' in releases_resp.headers["Link"]:
                    link_header = releases_resp.headers["Link"]
                    last_page = link_header.split("page=")[-1].split("&")[0].split(">")[0]
                    repo.releases_count = int(last_page)
                else:
                    repo.releases_count = len(releases)

                # Get latest release details
                if releases:
                    latest = releases[0]
                    repo.latest_release = latest.get("tag_name", "")
                    repo.latest_release_date = latest.get("published_at", None)

                releases_data = {
                    "count": repo.releases_count,
                    "latest": repo.latest_release,
                    "latest_date": repo.latest_release_date,
                }
                cache.set(releases_cache_key, releases_data, 3600)
        else:
            repo.releases_count = releases_data.get("count", 0)
            repo.latest_release = releases_data.get("latest", "")
            repo.latest_release_date = releases_data.get("latest_date", None)

        # Update sync timestamp
        repo.last_github_sync = timezone.now()
        repo.save()

        logger.info(f"Successfully updated GitHub data for {repo.name}")
        return True

    except Repo.DoesNotExist:
        logger.error(f"Repo with ID {repo_id} does not exist")
        return False
    except Exception as e:
        logger.exception(f"Error updating GitHub data for repo {repo_id}: {str(e)}")
        return False


@shared_task
def sync_code_quality(repo_id):
    """Sync code quality metrics from services like Codecov, SonarQube, etc."""
    from website.models import Repo

    try:
        repo = Repo.objects.get(id=repo_id)

        # Skip if not a GitHub repo
        if not repo.url or "github.com" not in repo.url:
            return False

        # Extract owner/repo from GitHub URL
        parts = repo.url.rstrip("/").split("/")
        if len(parts) < 2:
            return False

        owner_repo = "/".join(parts[-2:])
        owner, repo_name = owner_repo.split("/")

        # This would integrate with real services like Codecov and SonarQube
        # For this example, we'll simulate the data

        # 1. Code coverage from Codecov
        coverage_cache_key = f"codecov_{owner_repo}"
        coverage_data = cache.get(coverage_cache_key)

        if not coverage_data:
            # Simulate a call to Codecov API
            # In a real implementation, you would use:
            # codecov_url = f"{CODECOV_API}/github/{owner}/{repo_name}"
            # coverage_resp = requests.get(codecov_url, headers=codecov_headers)

            # Simulated code coverage (random value between 60-100%)
            import random

            repo.code_coverage = random.uniform(60.0, 100.0)

            coverage_data = {"coverage": repo.code_coverage}
            cache.set(coverage_cache_key, coverage_data, 86400)  # Cache for 24 hours
        else:
            repo.code_coverage = coverage_data.get("coverage", 0)

        # 2. Code quality metrics from SonarQube/SonarCloud
        quality_cache_key = f"sonar_{owner_repo}"
        quality_data = cache.get(quality_cache_key)

        if not quality_data:
            # Simulate a call to SonarQube API
            # In a real implementation, you would use:
            # sonar_url = f"{SONARQUBE_API}/measures/component?component={owner}_{repo_name}&metricKeys=reliability_rating,security_rating,sqale_rating"
            # quality_resp = requests.get(sonar_url, headers=sonar_headers)

            # Simulated code quality metrics
            import random

            repo.code_quality_score = random.uniform(70.0, 98.0)
            repo.maintainability_index = random.uniform(65.0, 95.0)
            repo.vulnerabilities = random.randint(0, 5)

            quality_data = {
                "quality_score": repo.code_quality_score,
                "maintainability": repo.maintainability_index,
                "vulnerabilities": repo.vulnerabilities,
            }
            cache.set(quality_cache_key, quality_data, 86400)  # Cache for 24 hours
        else:
            repo.code_quality_score = quality_data.get("quality_score", 0)
            repo.maintainability_index = quality_data.get("maintainability", 0)
            repo.vulnerabilities = quality_data.get("vulnerabilities", 0)

        # Update sync timestamp
        repo.last_quality_sync = timezone.now()
        repo.save()

        logger.info(f"Successfully updated code quality data for {repo.name}")
        return True

    except Repo.DoesNotExist:
        logger.error(f"Repo with ID {repo_id} does not exist")
        return False
    except Exception as e:
        logger.exception(f"Error updating code quality data for repo {repo_id}: {str(e)}")
        return False


@shared_task
def sync_social_media(repo_id):
    """Sync social media mentions and influence metrics"""
    from website.models import Repo

    try:
        repo = Repo.objects.get(id=repo_id)

        # Skip if not a GitHub repo
        if not repo.url or "github.com" not in repo.url:
            return False

        # Extract owner/repo from GitHub URL
        parts = repo.url.rstrip("/").split("/")
        if len(parts) < 2:
            return False

        owner_repo = "/".join(parts[-2:])

        # This would integrate with real social media APIs
        # For this example, we'll simulate the data

        # 1. Twitter mentions
        twitter_cache_key = f"twitter_{owner_repo}"
        twitter_data = cache.get(twitter_cache_key)

        if not twitter_data:
            # Simulate a call to Twitter API
            # In a real implementation, you would use:
            # twitter_url = f"{TWITTER_API}/tweets/search/recent?query={owner_repo}&max_results=100"
            # twitter_resp = requests.get(twitter_url, headers=twitter_headers)

            # Simulated twitter mentions
            import random

            repo.twitter_mentions = random.randint(0, 1000)

            twitter_data = {"mentions": repo.twitter_mentions}
            cache.set(twitter_cache_key, twitter_data, 43200)  # Cache for 12 hours
        else:
            repo.twitter_mentions = twitter_data.get("mentions", 0)

        # 2. LinkedIn mentions
        linkedin_cache_key = f"linkedin_{owner_repo}"
        linkedin_data = cache.get(linkedin_cache_key)

        if not linkedin_data:
            # Simulate a call to LinkedIn API
            # In a real implementation, you would use LinkedIn's API

            # Simulated LinkedIn mentions
            import random

            repo.linkedin_mentions = random.randint(0, 500)

            linkedin_data = {"mentions": repo.linkedin_mentions}
            cache.set(linkedin_cache_key, linkedin_data, 43200)  # Cache for 12 hours
        else:
            repo.linkedin_mentions = linkedin_data.get("mentions", 0)

        # Update sync timestamp
        repo.last_social_sync = timezone.now()
        repo.save()

        logger.info(f"Successfully updated social media data for {repo.name}")
        return True

    except Repo.DoesNotExist:
        logger.error(f"Repo with ID {repo_id} does not exist")
        return False
    except Exception as e:
        logger.exception(f"Error updating social media data for repo {repo_id}: {str(e)}")
        return False


@shared_task
def sync_package_downloads(repo_id):
    """Sync package download statistics from npm, PyPI, etc."""
    from website.models import Repo

    try:
        repo = Repo.objects.get(id=repo_id)
        project = repo.project

        # Skip if no project
        if not project:
            return False

        # This would integrate with package registries
        # For this example, we'll simulate the data

        # Determine package registry type based on project name or repo
        registry_type = None
        if "python" in project.name.lower() or "py" in project.name.lower():
            registry_type = "pypi"
        elif "node" in project.name.lower() or "js" in project.name.lower():
            registry_type = "npm"
        elif "java" in project.name.lower() or "maven" in project.name.lower():
            registry_type = "maven"

        if not registry_type:
            return False

        # Cache key based on project and registry
        downloads_cache_key = f"{registry_type}_{project.slug}"
        downloads_data = cache.get(downloads_cache_key)

        if not downloads_data:
            # Simulate API calls to different package registries
            import random

            if registry_type == "pypi":
                # Simulate PyPI downloads
                repo.package_downloads = random.randint(1000, 1000000)
                repo.recent_package_downloads = random.randint(100, 50000)
            elif registry_type == "npm":
                # Simulate npm downloads
                repo.package_downloads = random.randint(5000, 5000000)
                repo.recent_package_downloads = random.randint(500, 100000)
            elif registry_type == "maven":
                # Simulate Maven downloads
                repo.package_downloads = random.randint(500, 200000)
                repo.recent_package_downloads = random.randint(50, 10000)

            downloads_data = {"total": repo.package_downloads, "recent": repo.recent_package_downloads}
            cache.set(downloads_cache_key, downloads_data, 86400)  # Cache for 24 hours
        else:
            repo.package_downloads = downloads_data.get("total", 0)
            repo.recent_package_downloads = downloads_data.get("recent", 0)

        # Update sync timestamp
        repo.last_downloads_sync = timezone.now()
        repo.save()

        logger.info(f"Successfully updated package download data for {repo.name}")
        return True

    except Repo.DoesNotExist:
        logger.error(f"Repo with ID {repo_id} does not exist")
        return False
    except Exception as e:
        logger.exception(f"Error updating package download data for repo {repo_id}: {str(e)}")
        return False


@shared_task
def refresh_project_stats(project_id):
    """Refresh all stats for a specific project"""
    from website.models import Project, Repo

    try:
        project = Project.objects.get(id=project_id)
        repos = Repo.objects.filter(project=project)

        for repo in repos:
            sync_github_data.delay(repo.id)
            sync_code_quality.delay(repo.id)
            sync_social_media.delay(repo.id)
            sync_package_downloads.delay(repo.id)

        logger.info(f"Refresh tasks queued for all repositories of project {project.name}")
        return True

    except Project.DoesNotExist:
        logger.error(f"Project with ID {project_id} does not exist")
        return False
    except Exception as e:
        logger.exception(f"Error refreshing stats for project {project_id}: {str(e)}")
        return False
