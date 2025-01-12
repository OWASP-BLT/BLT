import ipaddress
import json
import re
import socket
import time
from calendar import monthrange
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import django_filters
import matplotlib.pyplot as plt
import requests
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.core.validators import URLValidator
from django.db.models import F, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify
from django.utils.timezone import localtime, now
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView
from django_filters.views import FilterView
from rest_framework.views import APIView

from website.bitcoin_utils import create_bacon_token
from website.forms import GitHubURLForm
from website.models import (
    IP,
    BaconToken,
    Contribution,
    Contributor,
    ContributorStats,
    Organization,
    Project,
    Repo,
)
from website.utils import admin_required

# logging.getLogger("matplotlib").setLevel(logging.ERROR)


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
    def get_client_ip(self, request):
        # Check X-Forwarded-For header first
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # Return first IP in chain (real client IP)
            ip = x_forwarded_for.split(",")[0].strip()
            return ip

        # Try X-Real-IP header next
        x_real_ip = request.META.get("HTTP_X_REAL_IP")
        if x_real_ip:
            return x_real_ip

        # Finally fall back to REMOTE_ADDR
        remote_addr = request.META.get("REMOTE_ADDR")
        return remote_addr

    def get(self, request, slug):
        # Get the project or return 404
        project = get_object_or_404(Project, slug=slug)

        # Get today's date
        today = now().date()

        # Get the real client IP
        user_ip = self.get_client_ip(request)

        # Continue with existing code but use the new user_ip
        visited_data = IP.objects.filter(
            address=user_ip, path=request.path, created__date=today
        ).last()

        if visited_data:
            # If the creation date is today
            if visited_data.created.date() == today:
                # If the visit count is 1, update the project visit count
                if visited_data.count == 1:
                    project.project_visit_count = F("project_visit_count") + 1
                    project.save()
            else:
                # If the creation date is not today, reset the creation date and count
                visited_data.created = now()
                visited_data.count = 1
                visited_data.save()

                # Increment the project visit count
                project.project_visit_count = F("project_visit_count") + 1
                project.save()
        else:
            # If no record exists, create a new one
            IP.objects.create(address=user_ip, path=request.path, created=now(), count=1)

            # Increment the project's visit count
            project.project_visit_count = F("project_visit_count") + 1
            project.save()

        # Refresh project to get the latest visit count
        project.refresh_from_db()

        total_views = project.project_visit_count

        fig = plt.figure(figsize=(4, 1))
        plt.bar(0, total_views, color="red", width=0.5)

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
        return queryset.filter(Q(project__name__icontains=value) | Q(name__icontains=value))

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


class ProjectView(FilterView):
    model = Repo
    template_name = "projects/project_list.html"
    context_object_name = "repos"
    filterset_class = ProjectRepoFilter
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        organization_id = self.request.GET.get("organization")

        if organization_id:
            queryset = queryset.filter(project__organization_id=organization_id)
        return queryset.select_related("project").prefetch_related("tags", "contributor")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            # Get organizations where user is admin or manager
            context["user_organizations"] = Organization.objects.filter(
                Q(admin=self.request.user) | Q(managers=self.request.user)
            ).distinct()

        # Get organizations that have projects
        context["organizations"] = Organization.objects.filter(projects__isnull=False).distinct()

        # Add counts
        context["total_projects"] = Project.objects.count()
        context["total_repos"] = Repo.objects.count()
        context["filtered_count"] = context["repos"].count()

        # Group repos by project
        projects = {}
        for repo in context["repos"]:
            if repo.project not in projects:
                projects[repo.project] = []
            projects[repo.project].append(repo)
        context["projects"] = projects

        return context


@login_required
@require_http_methods(["POST"])
def create_project(request):
    try:
        max_retries = 5
        delay = 20

        def validate_url(url):
            """Validate URL format and accessibility"""
            if not url:
                return True  # URLs are optional

            # Validate URL format
            try:
                URLValidator(schemes=["http", "https"])(url)
                parsed = urlparse(url)
                hostname = parsed.hostname
                if not hostname:
                    return False

                try:
                    addr_info = socket.getaddrinfo(hostname, None)
                except socket.gaierror:
                    # DNS resolution failed; hostname is not resolvable
                    return False
                for info in addr_info:
                    ip = info[4][0]
                    try:
                        ip_obj = ipaddress.ip_address(ip)
                        if (
                            ip_obj.is_private
                            or ip_obj.is_loopback
                            or ip_obj.is_reserved
                            or ip_obj.is_multicast
                            or ip_obj.is_link_local
                            or ip_obj.is_unspecified
                        ):
                            # Disallowed IP range detected
                            return False
                    except ValueError:
                        # Invalid IP address format
                        return False
                return True

            except (ValidationError, ValueError):
                return False

        # Validate project URL
        project_url = request.POST.get("url")
        if project_url and not validate_url(project_url):
            return JsonResponse(
                {
                    "error": "Project URL is not accessible or returns an error",
                    "code": "INVALID_PROJECT_URL",
                },
                status=400,
            )

        # Validate social media URLs
        twitter = request.POST.get("twitter")
        if twitter:
            if twitter.startswith(("http://", "https://")):
                if not validate_url(twitter):
                    return JsonResponse(
                        {
                            "error": "Twitter URL is not accessible",
                            "code": "INVALID_TWITTER_URL",
                        },
                        status=400,
                    )
            elif not twitter.startswith("@"):
                twitter = f"@{twitter}"

        facebook = request.POST.get("facebook")
        if facebook:
            if not validate_url(facebook) or "facebook.com" not in facebook:
                return JsonResponse(
                    {
                        "error": "Invalid or inaccessible Facebook URL",
                        "code": "INVALID_FACEBOOK_URL",
                    },
                    status=400,
                )

        # Validate repository URLs
        repo_urls = request.POST.getlist("repo_urls[]")
        for url in repo_urls:
            if not url:
                continue

            # Validate GitHub URL format
            if not url.startswith("https://github.com/"):
                return JsonResponse(
                    {
                        "error": f"Repository URL must be a GitHub URL: {url}",
                        "code": "NON_GITHUB_URL",
                    },
                    status=400,
                )

            # Verify GitHub URL format and accessibility
            if not re.match(r"https://github\.com/[^/]+/[^/]+/?$", url):
                return JsonResponse(
                    {
                        "error": f"Invalid GitHub repository URL format: {url}",
                        "code": "INVALID_GITHUB_URL_FORMAT",
                    },
                    status=400,
                )

            if not validate_url(url):
                return JsonResponse(
                    {
                        "error": f"GitHub repository is not accessible: {url}",
                        "code": "INACCESSIBLE_REPO",
                    },
                    status=400,
                )

        # Check if project already exists by name
        project_name = request.POST.get("name")
        if Project.objects.filter(name__iexact=project_name).exists():
            return JsonResponse(
                {
                    "error": "A project with this name already exists",
                    "code": "NAME_EXISTS",
                },
                status=409,
            )  # 409 Conflict

        # Check if project URL already exists
        project_url = request.POST.get("url")
        if project_url and Project.objects.filter(url=project_url).exists():
            return JsonResponse(
                {
                    "error": "A project with this URL already exists",
                    "code": "URL_EXISTS",
                },
                status=409,
            )

        # Check if any of the repository URLs are already linked to other projects
        repo_urls = request.POST.getlist("repo_urls[]")
        existing_repos = Repo.objects.filter(repo_url__in=repo_urls)
        if existing_repos.exists():
            existing_urls = list(existing_repos.values_list("repo_url", flat=True))
            return JsonResponse(
                {
                    "error": "One or more repositories are already linked to other projects",
                    "code": "REPOS_EXIST",
                    "existing_repos": existing_urls,
                },
                status=409,
            )

        # Extract project data
        project_data = {
            "name": project_name,
            "description": request.POST.get("description"),
            "url": project_url,
            "twitter": request.POST.get("twitter"),
            "facebook": request.POST.get("facebook"),
        }

        # Handle logo file
        if request.FILES.get("logo"):
            project_data["logo"] = request.FILES["logo"]

        # Handle organization association
        org_id = request.POST.get("organization")
        if org_id:
            try:
                org = Organization.objects.get(id=org_id)
                if not (request.user == org.admin):
                    return JsonResponse(
                        {
                            "error": "You do not have permission to add projects to this organization"
                        },
                        status=403,
                    )
                project_data["organization"] = org
            except Organization.DoesNotExist:
                return JsonResponse({"error": "Organization not found"}, status=404)

        # Create project
        project = Project.objects.create(**project_data)

        # GitHub API configuration
        github_token = getattr(settings, "GITHUB_TOKEN", None)
        if not github_token:
            return JsonResponse({"error": "GitHub token not configured"}, status=500)

        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        # Handle repositories
        repo_urls = request.POST.getlist("repo_urls[]")
        repo_types = request.POST.getlist("repo_types[]")

        def api_get(url):
            for i in range(max_retries):
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                except requests.exceptions.RequestException:
                    time.sleep(delay)
                    continue
                if response.status_code in (403, 429):
                    time.sleep(delay)
                    continue
                return response

        def get_issue_count(full_name, query):
            search_url = f"https://api.github.com/search/issues?q=repo:{full_name}+{query}"
            resp = api_get(search_url)
            if resp.status_code == 200:
                return resp.json().get("total_count", 0)
            return 0

        for url, repo_type in zip(repo_urls, repo_types):
            if not url:
                continue

            # Convert GitHub URL to API URL
            match = re.match(r"https://github.com/([^/]+)/([^/]+)/?", url)
            if not match:
                continue

            owner, repo_name = match.groups()
            api_url = f"https://api.github.com/repos/{owner}/{repo_name}"

            try:
                # Fetch repository data
                response = requests.get(api_url, headers=headers)
                if response.status_code != 200:
                    continue

                repo_data = response.json()

                # Generate unique slug
                base_slug = slugify(repo_data["name"])
                base_slug = base_slug.replace(".", "-")
                if len(base_slug) > 50:
                    base_slug = base_slug[:50]
                if not base_slug:
                    base_slug = f"repo-{int(time.time())}"

                unique_slug = base_slug
                counter = 1
                while Repo.objects.filter(slug=unique_slug).exists():
                    suffix = f"-{counter}"
                    if len(base_slug) + len(suffix) > 50:
                        base_slug = base_slug[: 50 - len(suffix)]
                    unique_slug = f"{base_slug}{suffix}"
                    counter += 1

                # Fetch additional data
                # Contributors count and commits count
                commit_count = 0
                all_contributors = []
                page = 1
                while True:
                    contrib_url = f"{api_url}/contributors?anon=true&per_page=100&page={page}"
                    c_resp = api_get(contrib_url)
                    if c_resp.status_code != 200:
                        break
                    contributors_data = c_resp.json()
                    if not contributors_data:
                        break
                    commit_count += sum(c.get("contributions", 0) for c in contributors_data)
                    all_contributors.extend(contributors_data)
                    page += 1

                # Issues count - Fixed
                full_name = repo_data.get("full_name")
                open_issues = get_issue_count(full_name, "type:issue+state:open")
                closed_issues = get_issue_count(full_name, "type:issue+state:closed")
                open_pull_requests = get_issue_count(full_name, "type:pr+state:open")
                total_issues = open_issues + closed_issues

                # Latest release
                releases_url = f"{api_url}/releases/latest"
                release_response = requests.get(releases_url, headers=headers)
                release_name = None
                release_datetime = None
                if release_response.status_code == 200:
                    release_data = release_response.json()
                    release_name = release_data.get("name") or release_data.get("tag_name")
                    release_datetime = release_data.get("published_at")

                # Create repository with fixed issues count
                repo = Repo.objects.create(
                    project=project,
                    slug=unique_slug,
                    name=repo_data["name"],
                    description=repo_data.get("description", ""),
                    repo_url=url,
                    homepage_url=repo_data.get("homepage", ""),
                    is_wiki=(repo_type == "wiki"),
                    is_main=(repo_type == "main"),
                    stars=repo_data.get("stargazers_count", 0),
                    forks=repo_data.get("forks_count", 0),
                    last_updated=parse_datetime(repo_data.get("updated_at")),
                    watchers=repo_data.get("watchers_count", 0),
                    primary_language=repo_data.get("language"),
                    license=repo_data.get("license", {}).get("name"),
                    last_commit_date=parse_datetime(repo_data.get("pushed_at")),
                    network_count=repo_data.get("network_count", 0),
                    subscribers_count=repo_data.get("subscribers_count", 0),
                    size=repo_data.get("size", 0),
                    logo_url=repo_data.get("owner", {}).get("avatar_url", ""),
                    open_issues=open_issues,
                    closed_issues=closed_issues,
                    total_issues=total_issues,
                    contributor_count=len(all_contributors),
                    commit_count=commit_count,
                    release_name=release_name,
                    release_datetime=(
                        parse_datetime(release_datetime) if release_datetime else None
                    ),
                    open_pull_requests=open_pull_requests,
                )

            except requests.exceptions.RequestException as e:
                continue

        return JsonResponse({"message": "Project created successfully"}, status=201)

    except Organization.DoesNotExist:
        return JsonResponse(
            {"error": "Organization not found", "code": "ORG_NOT_FOUND"}, status=404
        )
    except PermissionError:
        return JsonResponse(
            {
                "error": "You do not have permission to add projects to this organization",
                "code": "PERMISSION_DENIED",
            },
            status=403,
        )


class ProjectsDetailView(DetailView):
    model = Project
    template_name = "projects/project_detail.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()

        # Get all repositories associated with the project
        repositories = (
            Repo.objects.select_related("project")
            .filter(project=project)
            .prefetch_related("tags", "contributor")
        )

        # Calculate aggregate metrics
        repo_metrics = repositories.aggregate(
            total_stars=Sum("stars"),
            total_forks=Sum("forks"),
            total_issues=Sum("total_issues"),
            total_contributors=Sum("contributor_count"),
            total_commits=Sum("commit_count"),
            total_prs=Sum("open_pull_requests"),
        )

        # Format dates for display
        created_date = localtime(project.created)
        modified_date = localtime(project.modified)

        # Add computed context
        context.update(
            {
                "repositories": repositories,
                "repo_metrics": repo_metrics,
                "created_date": {
                    "full": created_date.strftime("%B %d, %Y"),
                    "relative": naturaltime(created_date),
                },
                "modified_date": {
                    "full": modified_date.strftime("%B %d, %Y"),
                    "relative": naturaltime(modified_date),
                },
                "show_org_details": self.request.user.is_authenticated
                and (
                    project.organization
                    and (
                        self.request.user == project.organization.admin
                        or project.organization.managers.filter(id=self.request.user.id).exists()
                    )
                ),
            }
        )

        # Add organization context if it exists
        if project.organization:
            context["organization"] = project.organization

        return context

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        return response


class RepoDetailView(DetailView):
    model = Repo
    template_name = "projects/repo_detail.html"
    context_object_name = "repo"

    def get_github_top_contributors(self, repo_url):
        """Fetch top contributors directly from GitHub API"""
        try:
            # Extract owner/repo from GitHub URL
            owner_repo = repo_url.rstrip("/").split("github.com/")[-1]
            api_url = f"https://api.github.com/repos/{owner_repo}/contributors?per_page=6"

            headers = {
                "Authorization": f"token {settings.GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            }

            response = requests.get(api_url, headers=headers)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error fetching GitHub contributors: {e}")
            return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        repo = self.get_object()

        # Get other repos from same project
        context["related_repos"] = (
            Repo.objects.filter(project=repo.project)
            .exclude(id=repo.id)
            .select_related("project")[:5]
        )

        # Get top contributors from GitHub
        github_contributors = self.get_github_top_contributors(repo.repo_url)

        if github_contributors:
            # Match by github_id instead of username
            github_ids = [str(c["id"]) for c in github_contributors]
            verified_contributors = repo.contributor.filter(
                github_id__in=github_ids
            ).select_related()

            # Create a mapping of github_id to database contributor
            contributor_map = {str(c.github_id): c for c in verified_contributors}

            # Merge GitHub and database data
            merged_contributors = []
            for gh_contrib in github_contributors:
                gh_id = str(gh_contrib["id"])
                db_contrib = contributor_map.get(gh_id)
                if db_contrib:
                    merged_contributors.append(
                        {
                            "name": db_contrib.name,
                            "github_id": db_contrib.github_id,
                            "avatar_url": db_contrib.avatar_url,
                            "contributions": gh_contrib["contributions"],
                            "github_url": db_contrib.github_url,
                            "verified": True,
                        }
                    )
                else:
                    merged_contributors.append(
                        {
                            "name": gh_contrib["login"],
                            "github_id": gh_contrib["id"],
                            "avatar_url": gh_contrib["avatar_url"],
                            "contributions": gh_contrib["contributions"],
                            "github_url": gh_contrib["html_url"],
                            "verified": False,
                        }
                    )

            context["top_contributors"] = merged_contributors
        else:
            # Fallback to database contributors if GitHub API fails
            context["top_contributors"] = [
                {
                    "name": c.name,
                    "github_id": c.github_id,
                    "avatar_url": c.avatar_url,
                    "contributions": c.contributions,
                    "github_url": c.github_url,
                    "verified": True,
                }
                for c in repo.contributor.all()[:6]
            ]

        # Get time period from request, default to
        time_period = self.request.GET.get("time_period", "current_month")
        page_number = self.request.GET.get("page", 1)
        # if time_period  exist in request.post do something
        if self.request.method == "POST":
            time_period = self.request.POST.get("time_period", "current_month")
            page_number = self.request.POST.get("page", 1)

        # Calculate date range based on time period
        end_date = timezone.now().date()
        start_date = None

        if time_period == "today":
            start_date = end_date
        elif time_period == "current_month":
            start_date = end_date.replace(day=1)
        elif time_period == "last_month":
            last_month = end_date - relativedelta(months=1)
            start_date = last_month.replace(day=1)
            end_date = last_month.replace(day=monthrange(last_month.year, last_month.month)[1])
        elif time_period == "last_6_months":
            start_date = end_date - relativedelta(months=6)
        elif time_period == "last_year":
            start_date = end_date - relativedelta(years=1)
        elif time_period == "all_time":
            # Get repository creation date from GitHub
            try:
                owner, repo_name = repo.repo_url.rstrip("/").split("/")[-2:]
                headers = {
                    "Authorization": f"token {settings.GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json",
                }
                response = requests.get(
                    f"https://api.github.com/repos/{owner}/{repo_name}", headers=headers
                )
                if response.status_code == 200:
                    repo_data = response.json()
                    start_date = datetime.strptime(
                        repo_data["created_at"], "%Y-%m-%dT%H:%M:%SZ"
                    ).date()
                else:
                    start_date = end_date - relativedelta(years=1)  # Fallback to 1 year
            except Exception:
                start_date = end_date - relativedelta(years=1)  # Fallback to 1 year

        # Query contributor stats
        stats_query = ContributorStats.objects.filter(
            repo=repo, date__gte=start_date, date__lte=end_date
        )

        # Aggregate the stats
        stats_query = (
            stats_query.values("contributor")
            .annotate(
                total_commits=Sum("commits"),
                total_issues_opened=Sum("issues_opened"),
                total_issues_closed=Sum("issues_closed"),
                total_prs=Sum("pull_requests"),
                total_comments=Sum("comments"),
            )
            .order_by("-total_commits")
        )

        # Calculate impact scores and enrich with contributor details
        processed_stats = []
        for stat in stats_query:
            contributor = Contributor.objects.get(id=stat["contributor"])

            # Calculate impact score using weighted values
            impact_score = (
                stat["total_commits"] * 5
                + stat["total_prs"] * 3
                + stat["total_issues_opened"] * 2
                + stat["total_issues_closed"] * 2
                + stat["total_comments"]
            )

            # Determine impact level based on score
            if impact_score > 200:
                impact_level = {"class": "bg-green-100 text-green-800", "text": "High Impact"}
            elif impact_score > 100:
                impact_level = {"class": "bg-yellow-100 text-yellow-800", "text": "Medium Impact"}
            else:
                impact_level = {"class": "bg-blue-100 text-blue-800", "text": "Growing Impact"}

            processed_stats.append(
                {
                    "contributor": contributor,
                    "commits": stat["total_commits"],
                    "issues_opened": stat["total_issues_opened"],
                    "issues_closed": stat["total_issues_closed"],
                    "pull_requests": stat["total_prs"],
                    "comments": stat["total_comments"],
                    "impact_score": impact_score,
                    "impact_level": impact_level,
                }
            )

        # Sort processed stats by impact score
        processed_stats.sort(key=lambda x: x["impact_score"], reverse=True)

        # Set up pagination
        paginator = Paginator(processed_stats, 10)  # Changed from 2 to 10 entries per page
        try:
            paginated_stats = paginator.page(page_number)
        except PageNotAnInteger:
            paginated_stats = paginator.page(1)
        except EmptyPage:
            paginated_stats = paginator.page(paginator.num_pages)

        # Prepare time period options
        time_period_options = [
            ("today", "Today's Data"),
            ("current_month", "Current Month"),
            ("last_month", "Last Month"),
            ("last_6_months", "Last 6 Months"),
            ("last_year", "1 Year"),
            ("all_time", "All Time"),
        ]

        # Add to context
        context.update(
            {
                "contributor_stats": paginated_stats,
                "page_obj": paginated_stats,  # Add this
                "paginator": paginator,  # Add this
                "time_period": time_period,
                "time_period_options": time_period_options,
                "start_date": start_date,
                "end_date": end_date,
                "is_paginated": paginator.num_pages > 1,  # Add this
            }
        )

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()  # Fix the missing object attribute

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            if "time_period" in request.POST:
                context = self.get_context_data()
                return render(request, "projects/_contributor_stats_table.html", context)

        def get_issue_count(full_name, query, headers):
            search_url = f"https://api.github.com/search/issues?q=repo:{full_name}+{query}"
            resp = requests.get(search_url, headers=headers)
            if resp.status_code == 200:
                return resp.json().get("total_count", 0)
            return 0

        repo = self.get_object()
        section = request.POST.get("section")

        if section == "basic":
            try:
                # Get GitHub API token
                github_token = getattr(settings, "GITHUB_TOKEN", None)
                if not github_token:
                    return JsonResponse(
                        {"status": "error", "message": "GitHub token not configured"}, status=500
                    )

                # Extract owner/repo from GitHub URL
                match = re.match(r"https://github.com/([^/]+)/([^/]+)/?", repo.repo_url)
                if not match:
                    return JsonResponse(
                        {"status": "error", "message": "Invalid repository URL"}, status=400
                    )

                owner, repo_name = match.groups()
                api_url = f"https://api.github.com/repos/{owner}/{repo_name}"

                # Make GitHub API request
                headers = {
                    "Authorization": f"token {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                }
                response = requests.get(api_url, headers=headers)

                if response.status_code == 200:
                    data = response.json()

                    # Update repo with fresh data
                    repo.stars = data.get("stargazers_count", 0)
                    repo.forks = data.get("forks_count", 0)
                    repo.watchers = data.get("watchers_count", 0)
                    repo.open_issues = data.get("open_issues_count", 0)
                    repo.network_count = data.get("network_count", 0)
                    repo.subscribers_count = data.get("subscribers_count", 0)
                    repo.last_updated = parse_datetime(data.get("updated_at"))
                    repo.save()

                    return JsonResponse(
                        {
                            "status": "success",
                            "message": "Basic information updated successfully",
                            "data": {
                                "stars": repo.stars,
                                "forks": repo.forks,
                                "watchers": repo.watchers,
                                "network_count": repo.network_count,
                                "subscribers_count": repo.subscribers_count,
                                "last_updated": naturaltime(repo.last_updated).replace(
                                    "\xa0", " "
                                ),  # Fix unicode space
                            },
                        }
                    )
                else:
                    return JsonResponse(
                        {"status": "error", "message": f"GitHub API error: {response.status_code}"},
                        status=response.status_code,
                    )

            except requests.RequestException as e:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Network error: A network error occurred. Please try again later.",
                    },
                    status=503,
                )
            except requests.HTTPError as e:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "A GitHub API error occurred. Please try again later.",
                    },
                    status=e.response.status_code,
                )
            except ValueError as e:
                return JsonResponse(
                    {"status": "error", "message": "There was an error processing your data."},
                    status=400,
                )

        elif section == "metrics":
            try:
                github_token = getattr(settings, "GITHUB_TOKEN", None)
                if not github_token:
                    return JsonResponse(
                        {"status": "error", "message": "GitHub token not configured"}, status=500
                    )

                match = re.match(r"https://github.com/([^/]+)/([^/]+)/?", repo.repo_url)
                if not match:
                    return JsonResponse(
                        {"status": "error", "message": "Invalid repository URL"}, status=400
                    )

                # Extract owner and repo from API call
                owner, repo_name = match.groups()
                api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
                headers = {
                    "Authorization": f"token {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                }
                response = requests.get(api_url, headers=headers)

                if response.status_code != 200:
                    return JsonResponse(
                        {"status": "error", "message": "Failed to fetch repository data"},
                        status=500,
                    )

                repo_data = response.json()
                full_name = repo_data.get("full_name")
                default_branch = repo_data.get("default_branch")
                if not full_name:
                    return JsonResponse(
                        {"status": "error", "message": "Could not get repository full name"},
                        status=500,
                    )

                full_name = full_name.replace(" ", "+")

                # get the total commit
                url = f"https://api.github.com/repos/{full_name}/commits"
                params = {"per_page": 1, "page": 1}
                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    if "Link" in response.headers:
                        links = response.headers["Link"]
                        last_page = 1
                        for link in links.split(","):
                            if 'rel="last"' in link:
                                last_page = int(link.split("&page=")[1].split(">")[0])
                        commit_count = last_page
                    else:
                        commits = response.json()
                        total_commits = len(commits)
                        commit_count = total_commits
                else:
                    commit_count = 0

                # Get open issues and PRs
                open_issues = get_issue_count(full_name, "type:issue+state:open", headers)
                closed_issues = get_issue_count(full_name, "type:issue+state:closed", headers)
                open_pull_requests = get_issue_count(full_name, "type:pr+state:open", headers)
                total_issues = open_issues + closed_issues

                if (
                    repo.open_issues != open_issues
                    or repo.closed_issues != closed_issues
                    or repo.total_issues != total_issues
                    or repo.open_pull_requests != open_pull_requests
                    or repo.commit_count != commit_count
                ):
                    # Update repository metrics
                    repo.open_issues = open_issues
                    repo.closed_issues = closed_issues
                    repo.total_issues = total_issues
                    repo.open_pull_requests = open_pull_requests
                    repo.commit_count = commit_count

                commits_url = f"{api_url}/commits?sha={default_branch}&per_page=1"
                commits_response = requests.get(commits_url, headers=headers)
                if commits_response.status_code == 200:
                    commit_data = commits_response.json()
                    if commit_data:
                        date_str = commit_data[0]["commit"]["committer"]["date"]
                        repo.last_commit_date = parse_datetime(date_str)
                repo.save()

                return JsonResponse(
                    {
                        "status": "success",
                        "message": "Activity metrics updated successfully",
                        "data": {
                            "open_issues": repo.open_issues,
                            "closed_issues": repo.closed_issues,
                            "total_issues": repo.total_issues,
                            "open_pull_requests": repo.open_pull_requests,
                            "commit_count": repo.commit_count,
                            "last_commit_date": repo.last_commit_date.strftime("%b %d, %Y")
                            if repo.last_commit_date
                            else "",
                        },
                    }
                )

            except requests.RequestException as e:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Network error: A network error occurred. Please try again later.",
                    },
                    status=503,
                )
            except requests.HTTPError as e:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "A GitHub API error occurred. Please try again later.",
                    },
                    status=e.response.status_code,
                )
            except ValueError as e:
                return JsonResponse(
                    {"status": "error", "message": "There was an error processing your data."},
                    status=400,
                )

        elif section == "technical":
            try:
                github_token = getattr(settings, "GITHUB_TOKEN", None)
                if not github_token:
                    return JsonResponse(
                        {"status": "error", "message": "GitHub token not configured"}, status=500
                    )

                match = re.match(r"https://github.com/([^/]+)/([^/]+)/?", repo.repo_url)
                if not match:
                    return JsonResponse(
                        {"status": "error", "message": "Invalid repository URL"}, status=400
                    )

                owner, repo_name = match.groups()
                api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
                headers = {
                    "Authorization": f"token {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                }

                response = requests.get(api_url, headers=headers)
                if response.status_code != 200:
                    return JsonResponse(
                        {"status": "error", "message": "Failed to fetch repository data"},
                        status=500,
                    )

                repo_data = response.json()

                # Update repository technical details
                repo.primary_language = repo_data.get("language")
                repo.size = repo_data.get("size", 0)
                repo.license = repo_data.get("license", {}).get("name")

                # Get latest release info
                releases_url = f"{api_url}/releases/latest"
                release_response = requests.get(releases_url, headers=headers)
                if release_response.status_code == 200:
                    release_data = release_response.json()
                    repo.release_name = release_data.get("name") or release_data.get("tag_name")
                    repo.release_datetime = parse_datetime(release_data.get("published_at"))

                repo.save()

                return JsonResponse(
                    {
                        "status": "success",
                        "message": "Technical information updated successfully",
                        "data": {
                            "primary_language": repo.primary_language or "Not specified",
                            "size": repo.size,
                            "license": repo.license or "Not specified",
                            "release_name": repo.release_name or "Not available",
                            "release_date": repo.release_datetime.strftime("%b %d, %Y")
                            if repo.release_datetime
                            else "Not available",
                            "last_commit_date": repo.last_commit_date.strftime("%b %d, %Y")
                            if repo.last_commit_date
                            else "Not available",
                        },
                    }
                )

            except requests.RequestException as e:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Network error: A network error occurred. Please try again later.",
                    },
                    status=503,
                )
            except Exception as e:
                return JsonResponse(
                    {"status": "error", "message": "An unexpected error occurred."}, status=500
                )

        elif section == "community":
            try:
                from django.core.management import call_command

                repo = self.get_object()

                # Run sync command
                call_command("sync_repo_contributors", "--repo_id", repo.id)

                # Refresh repo instance to get updated contributor_count
                repo.refresh_from_db()

                # Fetch real-time top contributors from GitHub
                github_contributors = self.get_github_top_contributors(repo.repo_url)
                merged_contributors = []
                for gh_contrib in github_contributors:
                    merged_contributors.append(
                        {
                            "name": gh_contrib["login"],
                            "github_id": gh_contrib["id"],
                            "avatar_url": gh_contrib["avatar_url"],
                            "contributions": gh_contrib["contributions"],
                            "github_url": gh_contrib["html_url"],
                            "verified": False,
                        }
                    )

                return JsonResponse(
                    {
                        "status": "success",
                        "message": "Fetched real-time contributor data from GitHub.",
                        "data": {
                            "contributors": merged_contributors,
                            "total_contributors": repo.contributor_count,
                        },
                    }
                )

            except ValueError as e:
                return JsonResponse(
                    {"status": "error", "message": "There was an error processing your data."},
                    status=400,
                )

        elif section == "contributor_stats":
            try:
                repo = self.get_object()
                # we have to run a management command to fetch the contributor stats
                from django.core.management import call_command

                call_command("update_contributor_stats", "--repo_id", repo.id)

                return JsonResponse(
                    {
                        "status": "success",
                        "message": "Contributor statistics updated successfully",
                    }
                )

            except Exception as e:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "An unexpected error occurred",
                    },
                    status=500,
                )

        return super().post(request, *args, **kwargs)


class RepoBadgeView(APIView):
    def get_client_ip(self, request):
        # Check X-Forwarded-For header first
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # Return first IP in chain (real client IP)
            ip = x_forwarded_for.split(",")[0].strip()
            return ip

        # Try X-Real-IP header next
        x_real_ip = request.META.get("HTTP_X_REAL_IP")
        if x_real_ip:
            return x_real_ip

        # Finally fall back to REMOTE_ADDR
        remote_addr = request.META.get("REMOTE_ADDR")
        return remote_addr

    def get(self, request, slug):
        # Get the repo or return 404
        repo = get_object_or_404(Repo, slug=slug)

        # Get today's date
        today = now().date()

        # Get the real client IP
        user_ip = self.get_client_ip(request)

        # Continue with existing code but use the new user_ip
        visited_data = IP.objects.filter(
            address=user_ip, path=request.path, created__date=today
        ).last()

        if visited_data:
            # If the creation date is today
            if visited_data.created.date() == today:
                # If the visit count is 1, update the repo visit count
                if visited_data.count == 1:
                    repo.repo_visit_count = F("repo_visit_count") + 1
                    repo.save()
            else:
                # If the creation date is not today, reset the creation date and count
                visited_data.created = now()
                visited_data.count = 1
                visited_data.save()

                # Increment the repo visit count
                repo.repo_visit_count = F("repo_visit_count") + 1
                repo.save()
        else:
            # If no record exists, create a new one
            IP.objects.create(address=user_ip, path=request.path, created=now(), count=1)

            # Increment the repo's visit count
            repo.repo_visit_count = F("repo_visit_count") + 1
            repo.save()

        # Refresh project to get the latest visit count
        repo.refresh_from_db()

        total_views = repo.repo_visit_count

        fig = plt.figure(figsize=(4, 1))
        plt.bar(0, total_views, color="red", width=0.5)

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
