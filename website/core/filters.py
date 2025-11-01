import django_filters
from django.db.models import Q

from website.models import Repo


class ProjectRepoFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search", label="Search")
    repo_type = django_filters.ChoiceFilter(
        choices=[
            ("all", "All"),
            ("main", "Main"),
            ("wiki", "Wiki"),
            ("normal", "Normal"),
        ],
        method="filter_repo_type",
        label="Repo Type",
    )
    sort = django_filters.ChoiceFilter(
        choices=[
            ("stars", "Stars"),
            ("forks", "Forks"),
            ("open_issues", "Open Issues"),
            ("last_updated", "Recently Updated"),
            ("contributor_count", "Contributors"),
        ],
        method="filter_sort",
        label="Sort By",
    )
    order = django_filters.ChoiceFilter(
        choices=[
            ("asc", "Ascending"),
            ("desc", "Descending"),
        ],
        method="filter_order",
        label="Order",
    )

    class Meta:
        model = Repo
        fields = ["search", "repo_type", "sort", "order"]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(project__name__icontains=value)
            | Q(name__icontains=value)
            | Q(primary_language__icontains=value)
            | Q(ai_summary__icontains=value)
            | Q(readme_content__icontains=value)
        )

    def filter_repo_type(self, queryset, name, value):
        if value == "main":
            return queryset.filter(is_main=True)
        elif value == "wiki":
            return queryset.filter(is_wiki=True)
        elif value == "normal":
            return queryset.filter(is_main=False, is_wiki=False)
        return queryset

    def filter_sort(self, queryset, name, value):
        sort_mapping = {
            "stars": "stars",
            "forks": "forks",
            "open_issues": "open_issues",
            "last_updated": "last_updated",
            "contributor_count": "contributor_count",
        }
        return queryset.order_by(sort_mapping.get(value, "stars"))

    def filter_order(self, queryset, name, value):
        if value == "desc":
            return queryset.reverse()
        return queryset
