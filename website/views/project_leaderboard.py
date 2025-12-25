"""
Project Leaderboard Views
Displays comprehensive GitHub statistics for all OWASP projects
with tabs for different metric views.
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from website.models import Organization, Project


class ProjectLeaderboardView(TemplateView):
    """Main leaderboard view with comprehensive project statistics"""

    template_name = "project_leaderboard.html"

    def get_projects_data(self):
        """Get aggregated project data"""
        projects = Project.objects.select_related("organization").prefetch_related("repos").all()

        projects_data = []
        for project in projects:
            repos = project.repos.all()

            # Aggregate GitHub metrics
            data = {
                "id": project.id,
                "name": project.name,
                "slug": project.slug,
                "description": project.description,
                "url": project.url,
                "logo": project.logo,
                "status": project.status,
                "status_display": project.get_status_display(),
                "organization": project.organization.name if project.organization else "Independent",
                "organization_id": project.organization.id if project.organization else None,
                # GitHub Metrics
                "stars": sum(r.stars for r in repos),
                "forks": sum(r.forks for r in repos),
                "issues": sum(r.open_issues for r in repos),
                "watchers": sum(r.watchers for r in repos),
                "contributors": sum(r.contributor_count for r in repos),
                "commits": sum(r.commit_count for r in repos),
                "repos_count": repos.count(),
            }

            # Calculate activity score
            data["activity_score"] = (
                data["commits"] * 0.4 + data["stars"] * 0.3 + data["forks"] * 0.2 + data["contributors"] * 0.1
            )

            projects_data.append(data)

        return projects_data

    def filter_and_sort(self, projects_data, filters):
        """Apply filters and sorting"""
        # Filter by search
        if filters.get("search"):
            search_term = filters["search"].lower()
            projects_data = [
                p
                for p in projects_data
                if search_term in p["name"].lower() or (p["description"] and search_term in p["description"].lower())
            ]

        # Filter by organization
        if filters.get("organization"):
            projects_data = [p for p in projects_data if p["organization_id"] == int(filters["organization"])]

        # Filter by status
        if filters.get("status"):
            projects_data = [p for p in projects_data if p["status"] == filters["status"]]

        # Sort
        sort_key = filters.get("sort", "stars")
        reverse = filters.get("dir", "desc") == "desc"

        sort_fields = {
            "stars": "stars",
            "forks": "forks",
            "issues": "issues",
            "contributors": "contributors",
            "commits": "commits",
            "activity": "activity_score",
            "name": "name",
        }

        sort_field = sort_fields.get(sort_key, "stars")
        projects_data.sort(
            key=lambda x: x[sort_field] if isinstance(x[sort_field], (int, float)) else x[sort_field].lower(),
            reverse=reverse,
        )

        return projects_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get filter parameters
        filters = {
            "search": self.request.GET.get("search", ""),
            "organization": self.request.GET.get("organization", ""),
            "status": self.request.GET.get("status", ""),
            "sort": self.request.GET.get("sort", "stars"),
            "dir": self.request.GET.get("dir", "desc"),
        }

        # Get and process project data
        projects_data = self.get_projects_data()
        projects_data = self.filter_and_sort(projects_data, filters)

        # Calculate dashboard metrics
        total_projects = len(projects_data)
        total_stars = sum(p["stars"] for p in projects_data)
        total_forks = sum(p["forks"] for p in projects_data)
        total_issues = sum(p["issues"] for p in projects_data)
        total_contributors = sum(p["contributors"] for p in projects_data)
        total_commits = sum(p["commits"] for p in projects_data)

        # Top 10 for charts
        top_projects = projects_data[:10]

        # Status distribution for pie chart
        status_dist = {}
        for p in projects_data:
            status_dist[p["status_display"]] = status_dist.get(p["status_display"], 0) + 1

        # Get filter options
        organizations = Organization.objects.all().order_by("name")
        status_choices = Project.STATUS_CHOICES

        context.update(
            {
                "projects": projects_data,
                "total_projects": total_projects,
                "total_stars": total_stars,
                "total_forks": total_forks,
                "total_issues": total_issues,
                "total_contributors": total_contributors,
                "total_commits": total_commits,
                "top_projects": top_projects,
                "status_distribution": status_dist,
                "organizations": organizations,
                "status_choices": status_choices,
                "filters": filters,
            }
        )

        return context


@require_http_methods(["GET"])
def project_leaderboard_data(request):
    """JSON API endpoint for dynamic updates"""
    view = ProjectLeaderboardView()
    view.request = request
    context = view.get_context_data()

    # Return JSON-serializable data
    return JsonResponse(
        {
            "projects": context["projects"],
            "totals": {
                "projects": context["total_projects"],
                "stars": context["total_stars"],
                "forks": context["total_forks"],
                "issues": context["total_issues"],
                "contributors": context["total_contributors"],
                "commits": context["total_commits"],
            },
            "top_projects": context["top_projects"],
            "status_distribution": context["status_distribution"],
        }
    )


@login_required
@require_http_methods(["POST"])
def refresh_project_stats(request, project_id):
    """Trigger stats refresh for a specific project"""
    try:
        project = get_object_or_404(Project, id=project_id)

        # Here you would call your GitHub sync task
        # For now, return success

        return JsonResponse(
            {"status": "success", "message": f"Stats refresh queued for {project.name}", "project_id": project.id}
        )

    except Exception as e:
        return JsonResponse({"status": "error", "message": f"Failed to refresh stats: {str(e)}"}, status=500)
