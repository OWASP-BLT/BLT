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
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now
from django.views.generic import DetailView, ListView
from rest_framework.views import APIView

from website.bitcoin_utils import create_bacon_token
from website.forms import GitHubURLForm
from website.models import IP, BaconToken, Contribution, Project
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = GitHubURLForm()
        context["sort_by"] = self.request.GET.get("sort_by", "-created")
        context["order"] = self.request.GET.get("order", "desc")
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
                        # Generate a unique slug
                        counter = 1
                        while Project.objects.filter(slug=f"{slug}-{counter}").exists():
                            counter += 1
                        slug = f"{slug}-{counter}"
                        
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
                        messages.info(request, "Project already exists.")
                else:
                    messages.error(request, "Failed to fetch project from GitHub.")
            else:
                messages.error(request, "Invalid GitHub URL.")
            return redirect("project_list")
        context = self.get_context_data()
        context["form"] = form
        return self.render_to_response(context)

    def get_queryset(self):
        queryset = super().get_queryset()
        sort_by = self.request.GET.get("sort_by", "-created")
        order = self.request.GET.get("order", "desc")

        if order == "asc" and sort_by.startswith("-"):
            sort_by = sort_by[1:]
        elif order == "desc" and not sort_by.startswith("-"):
            sort_by = f"-{sort_by}"

        return queryset.order_by(sort_by)
