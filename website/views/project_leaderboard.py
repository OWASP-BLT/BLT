import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.views.generic import ListView

from website.models import Organization, Project
from website.tasks import refresh_project_stats


class ProjectLeaderboardView(ListView):
    model = Project
    template_name = "project_leaderboard.html"
    context_object_name = "projects"

    def get_queryset(self):
        queryset = Project.objects.all().prefetch_related("repos")

        # Cache key for filtered queryset
        cache_params = []

        # Apply filters
        status_filter = self.request.GET.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            cache_params.append(f"status={status_filter}")

        org_filter = self.request.GET.get("organization")
        if org_filter:
            try:
                org_filter = int(org_filter)
                queryset = queryset.filter(organization__id=org_filter)
                cache_params.append(f"org={org_filter}")
            except (ValueError, TypeError):
                pass

        # Get sort parameter
        sort_by = self.request.GET.get("sort", "stars")
        sort_dir = self.request.GET.get("dir", "desc")
        cache_params.append(f"sort={sort_by}")
        cache_params.append(f"dir={sort_dir}")

        # Try to get from cache if params exist
        if cache_params:
            cache_key = f"project_list_{'_'.join(cache_params)}"
            cached_projects = cache.get(cache_key)
            if cached_projects:
                return cached_projects

        # Apply Django ORM sorting for fields that exist directly on Project
        if sort_by in ["name", "created", "modified"]:
            order_field = f"{'-' if sort_dir == 'desc' else ''}{sort_by}"
            queryset = queryset.order_by(order_field)

        # Cache this queryset for 10 minutes
        if cache_params:
            cache_key = f"project_list_{'_'.join(cache_params)}"
            cache.set(cache_key, queryset, 600)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Cache key for context data
        cache_key = "project_leaderboard_context"
        cached_context = cache.get(cache_key)

        if cached_context:
            # Update with the current projects
            cached_context["projects"] = context["projects"]
            cached_context["page_obj"] = context.get("page_obj")
            cached_context["paginator"] = context.get("paginator")
            cached_context["filters"] = {
                "organization": self.request.GET.get("organization", ""),
                "status": self.request.GET.get("status", ""),
                "sort": self.request.GET.get("sort", "stars"),
                "dir": self.request.GET.get("dir", "desc"),
            }
            return cached_context

        # If not cached, compute everything

        # Add organizations for filter dropdown
        context["organizations"] = Organization.objects.all()

        # Add status choices for filter dropdown
        context["statuses"] = dict(Project.STATUS_CHOICES)

        # Get active filters for form persistence
        context["filters"] = {
            "organization": self.request.GET.get("organization", ""),
            "status": self.request.GET.get("status", ""),
            "sort": self.request.GET.get("sort", "stars"),
            "dir": self.request.GET.get("dir", "desc"),
        }

        # Aggregate stats
        projects = context["projects"]

        # Post-process projects to add aggregated repo stats
        for project in projects:
            repos = project.repos.all()

            # Compute GitHub metrics
            project.total_stars = sum(repo.stars or 0 for repo in repos)
            project.total_forks = sum(repo.forks or 0 for repo in repos)
            project.total_issues = sum(repo.open_issues or 0 for repo in repos)
            project.total_pull_requests = sum(
                repo.open_pull_requests or 0 for repo in repos if hasattr(repo, "open_pull_requests")
            )
            project.recent_commits = sum(repo.recent_commits or 0 for repo in repos if hasattr(repo, "recent_commits"))

            # Compute code quality metrics
            quality_scores = [
                repo.code_quality_score
                for repo in repos
                if hasattr(repo, "code_quality_score") and repo.code_quality_score is not None
            ]
            project.avg_code_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None

            coverage_scores = [
                repo.code_coverage
                for repo in repos
                if hasattr(repo, "code_coverage") and repo.code_coverage is not None
            ]
            project.avg_code_coverage = sum(coverage_scores) / len(coverage_scores) if coverage_scores else None

            # Compute community metrics
            project.total_contributors = sum(
                repo.contributors_count or 0 for repo in repos if hasattr(repo, "contributors_count")
            )

            # Social media metrics
            project.twitter_mentions = sum(
                repo.twitter_mentions or 0 for repo in repos if hasattr(repo, "twitter_mentions")
            )
            project.linkedin_mentions = sum(
                repo.linkedin_mentions or 0 for repo in repos if hasattr(repo, "linkedin_mentions")
            )

            # External integrations
            project.package_downloads = sum(
                repo.package_downloads or 0 for repo in repos if hasattr(repo, "package_downloads")
            )

        # Sort by computed properties if needed
        sort_by = self.request.GET.get("sort", "stars")
        sort_dir = self.request.GET.get("dir", "desc")

        if sort_by == "stars":
            projects = sorted(projects, key=lambda x: x.total_stars, reverse=(sort_dir == "desc"))
        elif sort_by == "forks":
            projects = sorted(projects, key=lambda x: x.total_forks, reverse=(sort_dir == "desc"))
        elif sort_by == "issues":
            projects = sorted(projects, key=lambda x: x.total_issues, reverse=(sort_dir == "desc"))
        elif sort_by == "contributors":
            projects = sorted(projects, key=lambda x: getattr(x, "total_contributors", 0), reverse=(sort_dir == "desc"))
        elif sort_by == "quality":
            projects = sorted(
                projects, key=lambda x: getattr(x, "avg_code_quality", 0) or 0, reverse=(sort_dir == "desc")
            )
        elif sort_by == "coverage":
            projects = sorted(
                projects, key=lambda x: getattr(x, "avg_code_coverage", 0) or 0, reverse=(sort_dir == "desc")
            )
        elif sort_by == "commits":
            projects = sorted(
                projects, key=lambda x: getattr(x, "recent_commits", 0) or 0, reverse=(sort_dir == "desc")
            )
        elif sort_by == "downloads":
            projects = sorted(
                projects, key=lambda x: getattr(x, "package_downloads", 0) or 0, reverse=(sort_dir == "desc")
            )
        elif sort_by == "social":
            projects = sorted(
                projects,
                key=lambda x: (getattr(x, "twitter_mentions", 0) or 0) + (getattr(x, "linkedin_mentions", 0) or 0),
                reverse=(sort_dir == "desc"),
            )

        context["projects"] = projects

        # Calculate total stats for the dashboard
        context["total_projects"] = len(projects)
        context["total_stars"] = sum(getattr(project, "total_stars", 0) or 0 for project in projects)
        context["total_forks"] = sum(getattr(project, "total_forks", 0) or 0 for project in projects)
        context["total_issues"] = sum(getattr(project, "total_issues", 0) or 0 for project in projects)
        context["total_contributors"] = sum(getattr(project, "total_contributors", 0) or 0 for project in projects)
        context["total_downloads"] = sum(getattr(project, "package_downloads", 0) or 0 for project in projects)

        # Get top projects by stars for charts
        context["top_projects"] = sorted(projects, key=lambda x: x.total_stars, reverse=True)[:10]

        # Calculate status distribution for charts
        status_counts = {}
        for status, label in Project.STATUS_CHOICES:
            status_counts[label] = len([p for p in projects if p.status == status])
        context["status_distribution"] = status_counts

        # Add quality metrics for charts
        quality_data = []
        for project in sorted(projects, key=lambda x: getattr(x, "avg_code_quality", 0) or 0, reverse=True)[:10]:
            if hasattr(project, "avg_code_quality") and project.avg_code_quality:
                quality_data.append(
                    {
                        "name": project.name,
                        "quality": round(project.avg_code_quality, 2),
                        "coverage": round(project.avg_code_coverage, 2) if project.avg_code_coverage else 0,
                    }
                )
        context["quality_data"] = quality_data

        # Add social metrics for charts
        social_data = []
        for project in sorted(
            projects,
            key=lambda x: (getattr(x, "twitter_mentions", 0) or 0) + (getattr(x, "linkedin_mentions", 0) or 0),
            reverse=True,
        )[:10]:
            if hasattr(project, "twitter_mentions") or hasattr(project, "linkedin_mentions"):
                social_data.append(
                    {
                        "name": project.name,
                        "twitter": project.twitter_mentions or 0,
                        "linkedin": project.linkedin_mentions or 0,
                    }
                )
        context["social_data"] = social_data

        # Add activity timeline data
        activity_data = {}
        for i in range(7):
            date = (timezone.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            activity_data[date] = {"commits": 0, "pull_requests": 0, "issues": 0}

        # In a real implementation, you would query the database for actual data
        # For this example, we'll use simulated data

        # Simulate some activity data
        import random

        for date in activity_data.keys():
            activity_data[date]["commits"] = random.randint(5, 50)
            activity_data[date]["pull_requests"] = random.randint(1, 15)
            activity_data[date]["issues"] = random.randint(2, 20)

        context["activity_data"] = activity_data

        # Cache the context data for 10 minutes
        # Exclude the projects queryset which may be paginated
        cache_data = {}

        # Only copy serializable data to the cache
        for key, value in context.items():
            if key not in ["projects", "page_obj", "paginator"]:
                try:
                    # Test if the value is serializable
                    json.dumps(value)
                    cache_data[key] = value
                except (TypeError, OverflowError):
                    # If it's not serializable, don't cache it
                    pass

        cache.set(cache_key, cache_data, 600)

        return context


@login_required
def refresh_project_stats_view(request, project_id):
    """
    Endpoint to refresh GitHub stats for a specific project
    This will queue background tasks to update the data
    """
    try:
        project = Project.objects.get(id=project_id)

        # Queue background tasks through Celery
        refresh_project_stats.delay(project_id)

        return JsonResponse({"status": "success", "message": f"Stats refresh for {project.name} has been initiated."})
    except Project.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Project not found."}, status=404)


@login_required
def project_leaderboard_data(request):
    """
    API endpoint to get project data for the leaderboard in JSON format
    Used for AJAX calls and potentially external consumers
    """
    # Check cache first
    cache_key = f"project_leaderboard_data_{request.GET.urlencode()}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)

    # Get projects with filters (similar to the ListView)
    projects = Project.objects.all().prefetch_related("repos")

    # Apply filters
    status_filter = request.GET.get("status")
    if status_filter:
        projects = projects.filter(status=status_filter)

    org_filter = request.GET.get("organization")
    if org_filter:
        try:
            org_filter = int(org_filter)
            projects = projects.filter(organization__id=org_filter)
        except (ValueError, TypeError):
            pass

    # Prepare projects data with computed metrics
    projects_data = []

    for project in projects:
        repos = project.repos.all()

        # Basic metrics
        total_stars = sum(repo.stars or 0 for repo in repos)
        total_forks = sum(repo.forks or 0 for repo in repos)
        total_issues = sum(repo.open_issues or 0 for repo in repos)

        # Advanced metrics
        total_contributors = sum(repo.contributors_count or 0 for repo in repos if hasattr(repo, "contributors_count"))
        total_pull_requests = sum(repo.open_pull_requests or 0 for repo in repos if hasattr(repo, "open_pull_requests"))
        recent_commits = sum(repo.recent_commits or 0 for repo in repos if hasattr(repo, "recent_commits"))

        # Code quality metrics
        quality_scores = [
            repo.code_quality_score
            for repo in repos
            if hasattr(repo, "code_quality_score") and repo.code_quality_score is not None
        ]
        avg_code_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None

        coverage_scores = [
            repo.code_coverage for repo in repos if hasattr(repo, "code_coverage") and repo.code_coverage is not None
        ]
        avg_code_coverage = sum(coverage_scores) / len(coverage_scores) if coverage_scores else None

        # Social media metrics
        twitter_mentions = sum(repo.twitter_mentions or 0 for repo in repos if hasattr(repo, "twitter_mentions"))
        linkedin_mentions = sum(repo.linkedin_mentions or 0 for repo in repos if hasattr(repo, "linkedin_mentions"))

        # External integrations
        package_downloads = sum(repo.package_downloads or 0 for repo in repos if hasattr(repo, "package_downloads"))

        # FIX: Don't include the file object directly, just use the URL string
        logo_url = None
        if project.logo and hasattr(project.logo, "url"):
            try:
                logo_url = project.logo.url
            except:
                logo_url = None

        projects_data.append(
            {
                "id": project.id,
                "name": project.name,
                "slug": project.slug,
                "description": project.description,
                "status": project.get_status_display(),
                "status_code": project.status,
                "organization": project.organization.name if project.organization else "Independent",
                "organization_id": project.organization.id if project.organization else None,
                "url": project.url,
                "logo": logo_url,  # Use the string URL instead of the file object
                "created": project.created.isoformat() if hasattr(project, "created") else None,
                "modified": project.modified.isoformat() if hasattr(project, "modified") else None,
                # Aggregated GitHub metrics
                "stars": total_stars,
                "forks": total_forks,
                "issues": total_issues,
                "pull_requests": total_pull_requests,
                "contributors": total_contributors,
                "recent_commits": recent_commits,
                # Code quality metrics
                "code_quality": round(avg_code_quality, 2) if avg_code_quality else None,
                "code_coverage": round(avg_code_coverage, 2) if avg_code_coverage else None,
                # Social metrics
                "twitter_mentions": twitter_mentions,
                "linkedin_mentions": linkedin_mentions,
                "social_total": twitter_mentions + linkedin_mentions,
                # External data
                "package_downloads": package_downloads,
            }
        )

    # Sort the data
    sort_by = request.GET.get("sort", "stars")
    sort_dir = request.GET.get("dir", "desc")
    reverse_sort = sort_dir == "desc"

    sort_mapping = {
        "stars": "stars",
        "forks": "forks",
        "issues": "issues",
        "contributors": "contributors",
        "quality": "code_quality",
        "coverage": "code_coverage",
        "commits": "recent_commits",
        "downloads": "package_downloads",
        "social": "social_total",
    }

    sort_field = sort_mapping.get(sort_by, "stars")

    if sort_by == "name":
        projects_data.sort(key=lambda x: x.get("name", ""), reverse=reverse_sort)
    elif sort_by in ["created", "modified"]:
        projects_data.sort(key=lambda x: x.get(sort_by), reverse=reverse_sort)
    else:
        projects_data.sort(key=lambda x: x.get(sort_field, 0) or 0, reverse=reverse_sort)

    response_data = {"projects": projects_data, "total_count": len(projects_data)}

    # Cache the response for 5 minutes
    cache.set(cache_key, response_data, 300)

    return JsonResponse(response_data)
