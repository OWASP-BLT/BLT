"""
REST API endpoints for Project Leaderboard
"""
import logging

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
        # Get query parameters
        sort_by = request.GET.get("sort_by", "stars")
        order = request.GET.get("order", "desc")
        language = request.GET.get("language")
        min_stars = request.GET.get("min_stars")
        search = request.GET.get("search")
        limit = int(request.GET.get("limit", 10))

        # Build query
        projects = Project.objects.filter(repos__isnull=False).distinct()

        # Apply filters
        if search:
            projects = projects.filter(Q(name__icontains=search) | Q(description__icontains=search))

        # Get repos with their stats
        repos = Repo.objects.select_related("project").all()

        if language:
            repos = repos.filter(repo_url__icontains=language)

        if min_stars:
            repos = repos.filter(stars__gte=int(min_stars))

        # Sort mapping
        sort_fields = {
            "stars": "stars",
            "forks": "forks",
            "commits": "commit_count",
            "contributors": "contributor_count",
            "issues": "open_issues",
            "watchers": "watchers",
            "prs": "open_pull_requests",
            "activity": "updated_at",
        }

        sort_field = sort_fields.get(sort_by, "stars")
        if order == "asc":
            repos = repos.order_by(sort_field)
        else:
            repos = repos.order_by(f"-{sort_field}")

        repos = repos[:limit]

        # Format response
        data = []
        for repo in repos:
            project = repo.project
            data.append(
                {
                    "id": project.id,
                    "name": project.name,
                    "slug": project.slug,
                    "description": project.description,
                    "repo_url": repo.repo_url,
                    "stats": {
                        "stars": repo.stars,
                        "forks": repo.forks,
                        "open_issues": repo.open_issues,
                        "watchers": repo.watchers,
                        "commits": repo.commit_count,
                        "contributors": repo.contributor_count,
                        "open_prs": repo.open_pull_requests,
                        "closed_prs": repo.closed_pull_requests,
                    },
                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                }
            )

        return JsonResponse(
            {
                "success": True,
                "count": len(data),
                "data": data,
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

    def post(self, request, project_id):
        """Trigger refresh of GitHub stats for a project"""
        try:
            project = Project.objects.get(id=project_id)
            github_service = GitHubService()

            updated_repos = []
            for repo in project.repos.all():
                # Parse owner/repo from URL
                if "github.com" in repo.repo_url:
                    parts = repo.repo_url.rstrip("/").split("/")
                    owner, repo_name = parts[-2], parts[-1]

                    # Fetch fresh data
                    stats = github_service.refresh_repo_cache(owner, repo_name)

                    if stats:
                        # Update repo
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
            return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["GET"])
def leaderboard_filters(request):
    """Get available filter options"""
    # Get unique languages from repos
    languages = Repo.objects.values_list("repo_url", flat=True).distinct()
    # Extract language from GitHub URLs (simplified)

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
