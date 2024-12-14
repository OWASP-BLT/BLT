import json
import logging
import re
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import requests
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import escape
from django.utils.text import slugify
from django.utils.timezone import now
from django.views.generic import DetailView, ListView
from rest_framework.views import APIView

from website.bitcoin_utils import create_bacon_token
from website.forms import AdditionalRepoForm, GitHubURLForm
from website.models import IP, AdditionalRepo, BaconToken, Contribution, Project
from website.utils import admin_required

logging.getLogger("matplotlib").setLevel(logging.ERROR)


def blt_tomato(request):
    current_dir = Path(__file__).parent
    json_file_path = current_dir / "fixtures" / "blt_tomato_project_link.json"

    try:
        with json_file_path.open("r") as json_file:
            data = json.load(json_file)
    except Exception:
        data = []

    for project in data:
        funding_details = project.get("funding_details", "").split(", ")
        funding_links = [url.strip() for url in funding_details if url.startswith("https://")]

        funding_link = funding_links[0] if funding_links else "#"
        project["funding_hyperlinks"] = funding_link

    return render(request, "blt_tomato.html", {"projects": data})


@user_passes_test(admin_required)
def select_contribution(request):
    contributions = Contribution.objects.filter(status="closed").exclude(
        id__in=BaconToken.objects.values_list("contribution_id", flat=True)
    )
    return render(request, "select_contribution.html", {"contributions": contributions})


@user_passes_test(admin_required)
def distribute_bacon(request, contribution_id):
    contribution = Contribution.objects.get(id=contribution_id)
    if (
        contribution.status == "closed"
        and not BaconToken.objects.filter(contribution=contribution).exists()
    ):
        token = create_bacon_token(contribution.user, contribution)
        if token:
            messages.success(request, "Bacon distributed successfully")
            return redirect("contribution_detail", contribution_id=contribution.id)
        else:
            messages.error(request, "Failed to distribute bacon")
    contributions = Contribution.objects.filter(status="closed").exclude(
        id__in=BaconToken.objects.values_list("contribution_id", flat=True)
    )
    return render(request, "select_contribution.html", {"contributions": contributions})


class ProjectDetailView(DetailView):
    model = Project
    period = None
    selected_year = None

    def post(self, request, *args, **kwargs):
        from django.core.management import call_command

        project = self.get_object()

        if "refresh_stats" in request.POST:
            call_command("update_projects", "--project_id", project.pk)
            messages.success(request, f"Refreshing stats for {project.name}")

        elif "refresh_contributor_stats" in request.POST:
            owner_repo = project.github_url.rstrip("/").split("/")[-2:]
            repo = f"{owner_repo[0]}/{owner_repo[1]}"
            call_command("fetch_contributor_stats", "--repo", repo)
            messages.success(request, f"Refreshing contributor stats for {project.name}")

        elif "refresh_contributors" in request.POST:
            call_command("fetch_contributors", "--project_id", project.pk)
        return redirect("project_view", slug=project.slug)

    def get(self, request, *args, **kwargs):
        project = self.get_object()
        project.project_visit_count += 1
        project.save()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        end_date = now()
        display_end_date = end_date.date()
        selected_year = self.request.GET.get("year", None)
        if selected_year:
            start_date = datetime(int(selected_year), 1, 1)
            display_end_date = datetime(int(selected_year), 12, 31)
        else:
            self.period = self.request.GET.get("period", "30")
            days = int(self.period)
            start_date = end_date - timedelta(days=days)
            start_date = start_date.date()

        contributions = Contribution.objects.filter(
            created__date__gte=start_date,
            created__date__lte=display_end_date,
            repository=self.get_object(),
        )

        user_stats = {}
        for contribution in contributions:
            username = contribution.github_username
            if username not in user_stats:
                user_stats[username] = {
                    "commits": 0,
                    "issues_opened": 0,
                    "issues_closed": 0,
                    "prs": 0,
                    "comments": 0,
                    "total": 0,
                }
            if contribution.contribution_type == "commit":
                user_stats[username]["commits"] += 1
            elif contribution.contribution_type == "issue_opened":
                user_stats[username]["issues_opened"] += 1
            elif contribution.contribution_type == "issue_closed":
                user_stats[username]["issues_closed"] += 1
            elif contribution.contribution_type == "pull_request":
                user_stats[username]["prs"] += 1
            elif contribution.contribution_type == "comment":
                user_stats[username]["comments"] += 1
            total = (
                user_stats[username]["commits"] * 5
                + user_stats[username]["prs"] * 3
                + user_stats[username]["issues_opened"] * 2
                + user_stats[username]["issues_closed"] * 2
                + user_stats[username]["comments"]
            )
            user_stats[username]["total"] = total

        user_stats = dict(sorted(user_stats.items(), key=lambda x: x[1]["total"], reverse=True))

        current_year = now().year
        year_list = list(range(current_year, current_year - 10, -1))

        context.update(
            {
                "user_stats": user_stats,
                "period": self.period,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": display_end_date.strftime("%Y-%m-%d"),
                "year_list": year_list,
                "selected_year": selected_year,
            }
        )
        return context


class ProjectBadgeView(APIView):
    def get(self, request, slug):
        # Retrieve the project or return 404
        project = get_object_or_404(Project, slug=slug)

        # Get unique visits, grouped by date
        visit_counts = (
            IP.objects.filter(path=request.path)
            .annotate(date=TruncDate("created"))
            .values("date")
            .annotate(visit_count=Count("address"))
            .order_by("date")  # Order from oldest to newest
        )

        # Update project visit count
        project.repo_visit_count += 1
        project.save()

        # Extract dates and counts
        dates = [entry["date"] for entry in visit_counts]
        counts = [entry["visit_count"] for entry in visit_counts]
        total_views = sum(counts)  # Calculate total views

        fig = plt.figure(figsize=(4, 1))
        plt.bar(dates, counts, width=0.5, color="red")

        plt.title(
            f"{total_views}",
            loc="left",
            x=-0.36,
            y=0.3,
            fontsize=15,
            fontweight="bold",
            color="red",
        )

        plt.gca().set_xticks([])  # Remove x-axis ticks
        plt.gca().set_yticks([])
        plt.box(False)

        # Save the plot to an in-memory file
        buffer = BytesIO()
        plt.savefig(buffer, format="png", bbox_inches="tight")
        plt.close()
        buffer.seek(0)

        # Prepare the HTTP response with the bar graph image
        response = HttpResponse(buffer, content_type="image/png")
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"

        return response


class ProjectListView(ListView):
    model = Project
    context_object_name = "projects"
    paginate_by = 5
    template_name = "website/project_list.html"

    def get_queryset(self):
        queryset = Project.objects.all()
        filter_type = self.request.GET.get("filter_type", "all")

        if filter_type == "repos":
            # Get all additional repos
            repos = AdditionalRepo.objects.select_related("project").all()

            # Apply search
            search = self.request.GET.get("search", "")
            if search:
                repos = repos.filter(Q(name__icontains=search) | Q(description__icontains=search))

            # Apply repo-specific filters
            repo_language = self.request.GET.get("repo_language")
            if repo_language:
                repos = repos.filter(primary_language=repo_language)

            # Sorting
            sort_by = self.request.GET.get("sort_by", "-created")
            order = self.request.GET.get("order", "desc")
            if order == "asc" and sort_by.startswith("-"):
                sort_by = sort_by[1:]
            elif order == "desc" and not sort_by.startswith("-"):
                sort_by = f"-{sort_by}"

            return repos.order_by(sort_by)

        # Project queryset
        search = self.request.GET.get("search", "")
        if search:
            if filter_type == "all":
                queryset = queryset.filter(
                    Q(name__icontains=search)
                    | Q(description__icontains=search)
                    | Q(additional_repos__name__icontains=search)
                    | Q(additional_repos__description__icontains=search)
                ).distinct()
            else:  # projects only
                queryset = queryset.filter(
                    Q(name__icontains=search) | Q(description__icontains=search)
                )

        # Project filters
        activity_status = self.request.GET.get("activity_status")
        if activity_status:
            queryset = queryset.filter(activity_status=activity_status)

        project_type = self.request.GET.get("project_type")
        if project_type:
            queryset = queryset.filter(project_type__contains=[project_type])

        project_level = self.request.GET.get("project_label")
        if project_level:
            queryset = queryset.filter(project_label=project_level)

        # Sorting
        sort_by = self.request.GET.get("sort_by", "-created")
        order = self.request.GET.get("order", "desc")
        if order == "asc" and sort_by.startswith("-"):
            sort_by = sort_by[1:]
        elif order == "desc" and not sort_by.startswith("-"):
            sort_by = f"-{sort_by}"

        return queryset.prefetch_related("additional_repos", "contributors", "tags").order_by(
            sort_by
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filter_type = self.request.GET.get("filter_type", "all")

        # Add all filter parameters to context
        context.update(
            {
                "form": GitHubURLForm(),
                "additional_repo_form": AdditionalRepoForm(),
                "filter_type": filter_type,
                "sort_by": self.request.GET.get("sort_by", "-created"),
                "order": self.request.GET.get("order", "desc"),
                "search_query": self.request.GET.get("search", ""),
                "selected_status": self.request.GET.get("activity_status", ""),
                "selected_type": self.request.GET.get("project_type", ""),
                "selected_level": self.request.GET.get("project_label", ""),
                "selected_language": self.request.GET.get("repo_language", ""),
                "activity_statuses": Project.objects.exclude(activity_status__isnull=True)
                .values_list("activity_status", flat=True)
                .distinct(),
                "project_types": Project.objects.exclude(project_type__isnull=True)
                .values_list("project_type", flat=True)
                .distinct(),
                "project_levels": Project.objects.exclude(project_label__isnull=True)
                .values_list("project_label", flat=True)
                .distinct(),
                "repo_languages": AdditionalRepo.objects.values_list(
                    "primary_language", flat=True
                ).distinct(),
            }
        )

        # Add total pages count to context
        paginator = context["paginator"]
        context["total_pages"] = paginator.num_pages

        # Add current search parameters to context
        context["current_params"] = self.request.GET.copy()
        if "page" in context["current_params"]:
            del context["current_params"]["page"]

        return context

    def post(self, request, *args, **kwargs):
        if "refresh_stats" in request.POST:
            from django.core.management import call_command

            call_command("update_projects")
            messages.success(request, "Refreshing project statistics...")
            return redirect("project_list")

        if "refresh_contributors" in request.POST:
            from django.core.management import call_command

            projects = Project.objects.all()
            for project in projects:
                owner_repo = project.github_url.rstrip("/").split("/")[-2:]
                repo = f"{owner_repo[0]}/{owner_repo[1]}"
                call_command("fetch_contributor_stats", "--repo", repo)
            messages.success(request, "Refreshing contributor data...")
            return redirect("project_list")

        # Check if it's an additional repo submission
        if "project" in request.POST:
            form = AdditionalRepoForm(request.POST)
            if form.is_valid():
                try:
                    project = form.cleaned_data["project"]
                    github_url = form.cleaned_data["github_url"]

                    # Extract repo information from GitHub
                    match = re.match(r"https://github.com/([^/]+/[^/]+)", github_url)
                    if match:
                        repo_path = match.group(1)
                        api_url = f"https://api.github.com/repos/{repo_path}"

                        # Fetch main repo data
                        response = requests.get(api_url)
                        if response.status_code == 200:
                            data = response.json()

                            # Generate slug
                            base_slug = slugify(data["name"])
                            slug = base_slug
                            counter = 1
                            while AdditionalRepo.objects.filter(slug=slug).exists():
                                slug = f"{base_slug}-{counter}"
                                counter += 1

                            # Create additional repo
                            additional_repo = AdditionalRepo.objects.create(
                                project=project,
                                name=data["name"],
                                slug=slug,
                                github_url=github_url,
                                description=data.get("description", ""),
                                wiki_url=data.get("html_url", ""),
                                homepage_url=data.get("homepage", ""),
                                logo_url=data["owner"]["avatar_url"],
                                stars=data.get("stargazers_count", 0),
                                forks=data.get("forks_count", 0),
                                watchers=data.get("watchers_count", 0),
                                total_issues=data.get("open_issues_count", 0),
                                primary_language=data.get("language", ""),
                                license=data.get("license", {}).get("name", ""),
                                last_commit_date=data.get("pushed_at"),
                                created_at=data.get("created_at"),
                                updated_at=data.get("updated_at"),
                            )

                            messages.success(
                                request,
                                f"Additional repository '{data['name']}' added successfully!",
                            )
                        else:
                            error_data = response.json()
                            error_message = error_data.get("message", "Unknown error occurred")
                            messages.error(
                                request, f"Failed to fetch repository data: {error_message}"
                            )
                    else:
                        messages.error(request, "Invalid GitHub URL format.")
                except requests.RequestException as e:
                    messages.error(request, f"Network error: {str(e)}")
                except Exception as e:
                    messages.error(request, f"Error adding repository: {str(e)}")
                return redirect("project_list")
            else:
                messages.error(request, "Invalid form data. Please check your input.")
                return redirect("project_list")

        # Handle project form submission
        form = GitHubURLForm(request.POST)
        if form.is_valid():
            github_url = form.cleaned_data["github_url"]
            # Extract the repository part of the URL
            match = re.match(r"https://github.com/([^/]+/[^/]+)", github_url)
            if match:
                repo_path = match.group(1)
                api_url = f"https://api.github.com/repos/{repo_path}"
                response = requests.get(api_url)
                if response.status_code == 200:
                    data = response.json()
                    # if the description is empty, use the name as the description
                    if not data["description"]:
                        data["description"] = data["name"]

                    # Check if a project with the same slug already exists
                    slug = data["name"].lower()
                    if Project.objects.filter(slug=slug).exists():
                        messages.error(request, "A project with this slug already exists.")
                        return redirect("project_list")

                    project, created = Project.objects.get_or_create(
                        github_url=github_url,
                        defaults={
                            "name": data["name"],
                            "slug": slug,
                            "description": data["description"],
                            "wiki_url": data["html_url"],
                            "homepage_url": data.get("homepage", ""),
                            "logo_url": data["owner"]["avatar_url"],
                        },
                    )
                    if created:
                        messages.success(request, "Project added successfully.")
                    else:
                        messages.info(request, f"Project '{data['name']}' already exists.")
                else:
                    error_data = response.json()
                    error_message = error_data.get("message", "Unknown error occurred")
                    messages.error(request, f"Failed to fetch project data: {error_message}")
            else:
                messages.error(request, "Invalid GitHub URL.")
            return redirect("project_list")

        context = self.get_context_data()
        context["form"] = form
        return self.render_to_response(context)

    def get(self, request, *args, **kwargs):
        try:
            # Validate page parameter
            page = request.GET.get("page", "1")
            if not page.isdigit():
                # If page is not a valid number, redirect to page 1
                params = request.GET.copy()
                params["page"] = "1"
                base_url = reverse("project_list")
                return redirect(f"{base_url}?{params.urlencode()}")

            # Sanitize other parameters
            for key, value in request.GET.items():
                # Escape HTML characters to prevent XSS
                if isinstance(value, str):
                    request.GET._mutable = True
                    request.GET[key] = escape(value)
                    request.GET._mutable = False

            return super().get(request, *args, **kwargs)
        except ValueError as e:
            params = request.GET.copy()
            if "page" in params:
                del params["page"]
            base_url = reverse("project_list")
            return redirect(f"{base_url}?{params.urlencode()}")
        except Exception as e:
            # If the page number is invalid
            if "Invalid page" in str(e):
                # Get the current querystring without page parameter
                params = request.GET.copy()
                if "page" in params:
                    del params["page"]

                # Get the queryset and paginator
                queryset = self.get_queryset()
                paginator = self.get_paginator(queryset, self.paginate_by)

                # Redirect to the last page
                params["page"] = paginator.num_pages

                # Build the URL with updated parameters
                base_url = reverse("project_list")
                if params:
                    return redirect(f"{base_url}?{params.urlencode()}")
                return redirect("project_list")

            raise Http404("Page not found")
