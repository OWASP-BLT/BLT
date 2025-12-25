"""
REST API endpoints for Project Leaderboard
"""
import logging
import re

from django.contrib.auth.decorators import login_required
from django.db.models import Max, Min, Q
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

from website.models import Project, Repo
from website.services.github_service import GitHubService

logger = logging.getLogger(__name__)


class LeaderboardAPIView(View):
    """API endpoint for leaderboard data"""

    @method_decorator(cache_page(300))  # Cache for 5 minutes
    def get(self, request):
        """
        Get leaderboard data with optional filtering and sorting

        Query Parameters:
        - sort_by: Field to sort by (stars, forks, commits, contributors, etc.)
        - order: asc or desc
        - language: Filter by programming language
        - min_stars: Minimum stars
        - search: Search query for project name
        - limit: Number of results (default: 10)
        """
        # Get query parameters with error handling
        sort_by = request.GET.get("sort_by", "stars")
        order = request.GET.get("order", "desc")
        language = request.GET.get("language")
        search = request.GET.get("search")

        # Safe integer conversions
        try:
            min_stars = int(request.GET.get("min_stars", 0))
        except (ValueError, TypeError):
            min_stars = 0

        try:
            limit = int(request.GET.get("limit", 10))
        except (ValueError, TypeError):
            limit = 10

        # Get projects with their repos
        projects = Project.objects.prefetch_related("repos").all()

        # Apply search filter
        if search:
            projects = projects.filter(Q(name__icontains=search) | Q(description__icontains=search))

        # Build project data with aggregated stats
        projects_data = []
        for project in projects:
            repos = project.repos.all()
            if not repos:
                continue

            # Aggregate stats across all repos
            total_stats = {
                "stars": sum(r.stars or 0 for r in repos),
                "forks": sum(r.forks or 0 for r in repos),
                "open_issues": sum(r.open_issues or 0 for r in repos),
                "watchers": sum(r.watchers or 0 for r in repos),
                "commits": sum(r.commit_count or 0 for r in repos),
                "contributors": sum(r.contributor_count or 0 for r in repos),
                "open_prs": sum(r.open_pull_requests or 0 for r in repos),
                "closed_prs": sum(r.closed_pull_requests or 0 for r in repos),
            }

            # Apply filters
            if language:
                if not any(r.primary_language and r.primary_language.lower() == language.lower() for r in repos):
                    continue

            if min_stars and total_stats["stars"] < min_stars:
                continue

            # Get primary repo URL
            main_repo = repos.filter(is_main=True).first() or repos.first()

            projects_data.append(
                {
                    "id": project.id,
                    "name": project.name,
                    "slug": project.slug,
                    "description": project.description,
                    "repo_url": main_repo.repo_url if main_repo else "",
                    "stats": total_stats,
                    "updated_at": max((r.updated_at for r in repos if r.updated_at), default=None),
                }
            )

        # Sort the aggregated data
        sort_fields = {
            "stars": "stars",
            "forks": "forks",
            "commits": "commits",
            "contributors": "contributors",
            "issues": "open_issues",
            "watchers": "watchers",
            "prs": "open_prs",
            "activity": "updated_at",
        }

        sort_key = sort_fields.get(sort_by, "stars")
        reverse_sort = order == "desc"

        # Handle None values in sorting
        if sort_key == "updated_at":
            projects_data.sort(key=lambda x: x.get(sort_key) or "", reverse=reverse_sort)
        else:
            projects_data.sort(key=lambda x: x["stats"].get(sort_key, 0), reverse=reverse_sort)

        # Apply limit
        projects_data = projects_data[:limit]

        return JsonResponse(
            {
                "success": True,
                "count": len(projects_data),
                "data": projects_data,
                "filters": {
                    "sort_by": sort_by,
                    "order": order,
                    "language": language,
                    "min_stars": min_stars,
                    "search": search,
                },
            }
        )


class ProjectStatsAPIView(View):
    """API endpoint for individual project stats"""

    def get(self, request, project_id):
        """Get detailed stats for a specific project"""
        try:
            project = Project.objects.get(id=project_id)
            repos = project.repos.all()

            total_stats = {
                "stars": sum(r.stars for r in repos),
                "forks": sum(r.forks for r in repos),
                "open_issues": sum(r.open_issues for r in repos),
                "watchers": sum(r.watchers for r in repos),
                "commits": sum(r.commit_count for r in repos),
                "contributors": sum(r.contributor_count for r in repos),
                "open_prs": sum(r.open_pull_requests for r in repos),
                "closed_prs": sum(r.closed_pull_requests for r in repos),
            }

            repos_data = []
            for repo in repos:
                repos_data.append(
                    {
                        "name": repo.name,
                        "url": repo.repo_url,
                        "stars": repo.stars,
                        "forks": repo.forks,
                        "open_issues": repo.open_issues,
                        "commits": repo.commit_count,
                        "contributors": repo.contributor_count,
                    }
                )

            return JsonResponse(
                {
                    "success": True,
                    "project": {
                        "id": project.id,
                        "name": project.name,
                        "slug": project.slug,
                        "description": project.description,
                        "total_stats": total_stats,
                        "repos": repos_data,
                    },
                }
            )
        except Project.DoesNotExist:
            return JsonResponse({"success": False, "error": "Project not found"}, status=404)


class RefreshStatsAPIView(View):
    """API endpoint to refresh GitHub stats"""

    @method_decorator(login_required)
    def post(self, request, project_id):
        """Trigger refresh of GitHub stats for a project"""
        try:
            project = Project.objects.get(id=project_id)
            github_service = GitHubService()

            updated_repos = []
            for repo in project.repos.all():
                # Parse owner/repo from URL with strict validation
                try:
                    # Extract owner/repo from GitHub URL using regex
                    # Expected format: https://github.com/owner/repo or git@github.com:owner/repo
                    match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?(?:/|$)", repo.repo_url)
                    if match:
                        owner, repo_name = match.group(1), match.group(2)

                        # Fetch fresh data
                        stats = github_service.refresh_repo_cache(owner, repo_name)
                        if stats:
                            repo.stars = stats.get("stars", repo.stars)
                            repo.forks = stats.get("forks", repo.forks)
                            repo.open_issues = stats.get("open_issues", repo.open_issues)
                            repo.watchers = stats.get("watchers", repo.watchers)
                            repo.commit_count = stats.get("commit_count", repo.commit_count)
                            repo.contributor_count = stats.get("contributors_count", repo.contributor_count)
                            repo.open_pull_requests = stats.get("open_pull_requests", repo.open_pull_requests)
                            repo.closed_pull_requests = stats.get("closed_pull_requests", repo.closed_pull_requests)
                            repo.save()

                            updated_repos.append(repo.name)
                except Exception as e:
                    logger.warning(f"Failed to parse GitHub URL for repo {repo.id}: {e}")
                    continue

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Refreshed stats for {len(updated_repos)} repositories",
                    "updated_repos": updated_repos,
                }
            )

        except Project.DoesNotExist:
            return JsonResponse({"success": False, "error": "Project not found"}, status=404)
        except Exception as e:
            logger.error(f"Error refreshing stats: {e}")
            return JsonResponse({"success": False, "error": "Failed to refresh stats"}, status=500)


@require_http_methods(["GET"])
def leaderboard_filters(request):
    """Get available filter options"""
    # Get min/max stars
    stats = Repo.objects.aggregate(
        min_stars=Min("stars"),
        max_stars=Max("stars"),
        min_forks=Min("forks"),
        max_forks=Max("forks"),
    )

    return JsonResponse(
        {
            "success": True,
            "filters": {
                "sort_options": [
                    {"value": "stars", "label": "Stars"},
                    {"value": "forks", "label": "Forks"},
                    {"value": "commits", "label": "Commits"},
                    {"value": "contributors", "label": "Contributors"},
                    {"value": "issues", "label": "Open Issues"},
                    {"value": "watchers", "label": "Watchers"},
                    {"value": "prs", "label": "Pull Requests"},
                    {"value": "activity", "label": "Recent Activity"},
                ],
                "stats_range": stats,
            },
        }
    )
