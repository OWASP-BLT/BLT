from django.db.models import Count, Sum
from django.views.generic import TemplateView

from website.models import Project


class ProjectLeaderboardView(TemplateView):
    template_name = "projects/project_leaderboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        projects = Project.objects.prefetch_related("repos").annotate(
            repo_count=Count("repos", distinct=True),
            total_stars=Sum("repos__stars"),
            total_forks=Sum("repos__forks"),
            open_issues=Sum("repos__open_issues"),
        )

        context["dashboard_projects"] = projects.order_by("-total_stars")[:20]
        context["projects"] = projects.order_by("-repo_count")
        context["activity"] = projects.order_by("-open_issues")

        return context
