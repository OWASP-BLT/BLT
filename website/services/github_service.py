"""
GitHub API Service for fetching repository statistics
"""
import logging
from typing import Dict, Optional

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class GitHubService:
    """Service for interacting with GitHub API"""

    BASE_URL = "https://api.github.com"
    CACHE_TIMEOUT = 3600  # 1 hour

    def __init__(self):
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        # Add GitHub token if available
        github_token = getattr(settings, "GITHUB_TOKEN", None)
        if github_token:
            self.headers["Authorization"] = f"token {github_token}"

    def get_repo_stats(self, owner: str, repo: str) -> Optional[Dict]:
        """
        Fetch repository statistics from GitHub API

        Args:
            owner: Repository owner (e.g., 'OWASP-BLT')
            repo: Repository name (e.g., 'BLT')

        Returns:
            Dictionary with repo stats or None if error
        """
        cache_key = f"github_repo_{owner}_{repo}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return cached_data

        try:
            # Get main repo data
            repo_url = f"{self.BASE_URL}/repos/{owner}/{repo}"
            response = requests.get(repo_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            repo_data = response.json()

            # Get additional stats
            contributors_count = self._get_contributors_count(owner, repo)
            commit_count = self._get_commit_count(owner, repo)
            pr_stats = self._get_pr_stats(owner, repo)

            stats = {
                "name": repo_data.get("name"),
                "full_name": repo_data.get("full_name"),
                "description": repo_data.get("description"),
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "watchers": repo_data.get("watchers_count", 0),
                "open_issues": repo_data.get("open_issues_count", 0),
                "size": repo_data.get("size", 0),
                "language": repo_data.get("language"),
                "created_at": repo_data.get("created_at"),
                "updated_at": repo_data.get("updated_at"),
                "pushed_at": repo_data.get("pushed_at"),
                "contributors_count": contributors_count,
                "commit_count": commit_count,
                "open_pull_requests": pr_stats["open"],
                "closed_pull_requests": pr_stats["closed"],
                "total_pull_requests": pr_stats["total"],
                "homepage": repo_data.get("homepage"),
                "topics": repo_data.get("topics", []),
                "license": repo_data.get("license", {}).get("name") if repo_data.get("license") else None,
            }

            cache.set(cache_key, stats, self.CACHE_TIMEOUT)
            return stats

        except requests.RequestException as e:
            logger.error(f"Error fetching GitHub data for {owner}/{repo}: {e}")
            return None

    def _get_contributors_count(self, owner: str, repo: str) -> int:
        """Get total number of contributors"""
        try:
            url = f"{self.BASE_URL}/repos/{owner}/{repo}/contributors"
            response = requests.get(url, headers=self.headers, params={"per_page": 1, "anon": "true"}, timeout=10)
            response.raise_for_status()

            # Get total count from Link header
            link_header = response.headers.get("Link", "")
            if "last" in link_header:
                # Parse the last page number from Link header
                import re

                match = re.search(r'page=(\d+)>; rel="last"', link_header)
                if match:
                    return int(match.group(1))

            # Fallback to counting items if no pagination
            return len(response.json())
        except Exception as e:
            logger.warning(f"Could not fetch contributors count: {e}")
            return 0

    def _get_commit_count(self, owner: str, repo: str) -> int:
        """Get approximate commit count"""
        try:
            url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits"
            response = requests.get(url, headers=self.headers, params={"per_page": 1, "sha": "HEAD"}, timeout=10)
            response.raise_for_status()

            # Parse Link header for total pages
            link_header = response.headers.get("Link", "")
            if "last" in link_header:
                import re

                match = re.search(r'page=(\d+)>; rel="last"', link_header)
                if match:
                    return int(match.group(1))

            return 1
        except Exception as e:
            logger.warning(f"Could not fetch commit count: {e}")
            return 0

    def _get_pr_stats(self, owner: str, repo: str) -> Dict[str, int]:
        """Get pull request statistics"""
        try:
            # Get open PRs
            open_url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls"
            open_response = requests.get(
                open_url, headers=self.headers, params={"state": "open", "per_page": 1}, timeout=10
            )
            open_response.raise_for_status()

            open_count = self._parse_total_count(open_response.headers.get("Link", ""))
            if open_count == 0:
                open_count = len(open_response.json())

            # Get closed PRs count (approximate from issues)
            issues_url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues"
            closed_response = requests.get(
                issues_url, headers=self.headers, params={"state": "closed", "per_page": 1}, timeout=10
            )

            closed_count = self._parse_total_count(closed_response.headers.get("Link", ""))

            return {"open": open_count, "closed": closed_count, "total": open_count + closed_count}
        except Exception as e:
            logger.warning(f"Could not fetch PR stats: {e}")
            return {"open": 0, "closed": 0, "total": 0}

    def _parse_total_count(self, link_header: str) -> int:
        """Parse total count from Link header"""
        if "last" in link_header:
            import re

            match = re.search(r'page=(\d+)>; rel="last"', link_header)
            if match:
                return int(match.group(1))
        return 0

    def refresh_repo_cache(self, owner: str, repo: str) -> Optional[Dict]:
        """Force refresh cache for a repository"""
        cache_key = f"github_repo_{owner}_{repo}"
        cache.delete(cache_key)
        return self.get_repo_stats(owner, repo)

    def get_multiple_repos(self, repos: list) -> Dict[str, Dict]:
        """
        Fetch stats for multiple repositories

        Args:
            repos: List of tuples [(owner, repo), ...]

        Returns:
            Dictionary mapping 'owner/repo' to stats
        """
        results = {}
        for owner, repo in repos:
            stats = self.get_repo_stats(owner, repo)
            if stats:
                results[f"{owner}/{repo}"] = stats
        return results
