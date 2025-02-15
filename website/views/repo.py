from django.db.models import Q
from django.views.generic import ListView

from website.models import Repo


class RepoListView(ListView):
    model = Repo
    template_name = "repo/repo_list.html"
    context_object_name = "repos"
    paginate_by = 100

    def get_queryset(self):
        queryset = Repo.objects.all()

        # Get sort parameter from URL
        sort_by = self.request.GET.get("sort", "-created")
        direction = "-" if sort_by.startswith("-") else ""
        field = sort_by.lstrip("-")

        # Validate the field is sortable
        valid_fields = [
            "name",
            "stars",
            "forks",
            "watchers",
            "open_issues",
            "closed_issues",
            "open_pull_requests",
            "contributor_count",
            "commit_count",
            "primary_language",
            "size",
            "created",
            "last_updated",
            "repo_visit_count",
        ]

        if field in valid_fields:
            queryset = queryset.order_by(f"{direction}{field}")

        # Handle search
        search_query = self.request.GET.get("q")
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(primary_language__icontains=search_query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_sort"] = self.request.GET.get("sort", "-created")
        context["total_repos"] = Repo.objects.count()
        return context
