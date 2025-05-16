import concurrent.futures
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

import requests
import sentry_sdk
from dateutil.parser import parse as parse_datetime
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.core.validators import URLValidator
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.timezone import localtime, now
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView
from django_filters.views import FilterView
from PIL import Image, ImageDraw, ImageFont
from rest_framework.views import APIView

from website.bitcoin_utils import create_bacon_token
from website.filters import ProjectRepoFilter
from website.models import IP, BaconToken, Contribution, Contributor, ContributorStats, Organization, Project, Repo
from website.utils import admin_required

# logging.getLogger("matplotlib").setLevel(logging.ERROR)


# Helper function to parse date
def parse_date(date_str):
    """Parse GitHub API date string to datetime object"""
    return parse_datetime(date_str) if date_str else None


def repo_activity_data(request, slug):
    """API endpoint for repository activity data"""
    repo = get_object_or_404(Repo, slug=slug)
    owner_repo = repo.repo_url.rstrip("/").split("github.com/")[-1]
    owner, repo_name = owner_repo.split("/")

    # Get activity data
    activity_data = RepoDetailView().fetch_activity_data(owner, repo_name)

    return JsonResponse(activity_data)


def blt_tomato(request):
    current_dir = Path(__file__).parent.parent
    json_file_path = current_dir / "fixtures" / "blt_tomato_project_link.json"

    try:
        with json_file_path.open("r") as json_file:
            data = json.load(json_file)
    except Exception:
        data = []

    processed_projects = []
    for project in data:
        funding_details = project.get("funding_details", "").split(", ")
        funding_links = [url.strip() for url in funding_details if url.startswith("https://")]
        funding_link = funding_links[0] if funding_links else "#"

        proposal_url = project.get("proposal_url")
        # Treat "#", "", or anything invalid as None for sorting
        if proposal_url in ("", "#"):
            proposal_url = None
        processed_projects.append(
            {
                "project_name": project.get("project_name"),
                "repo_url": project.get("repo_url"),
                "funding_hyperlinks": funding_link,
                "funding_details": project.get("funding_details"),
                "proposal_url": proposal_url,
            }
        )
    processed_projects.sort(key=lambda x: x["proposal_url"] is None)

    return render(request, "blt_tomato.html", {"projects": processed_projects})


@user_passes_test(admin_required)
def select_contribution(request):
    contributions = Contribution.objects.filter(status="closed").exclude(
        id__in=BaconToken.objects.values_list("contribution_id", flat=True)
    )
    return render(request, "select_contribution.html", {"contributions": contributions})


@user_passes_test(admin_required)
def distribute_bacon(request, contribution_id):
    contribution = Contribution.objects.get(id=contribution_id)
    if contribution.status == "closed" and not BaconToken.objects.filter(contribution=contribution).exists():
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
        current_time = now()
        today = current_time.date()

        # Get the real client IP
        user_ip = self.get_client_ip(request)

        # Check if we have a record for today
        visited_data = IP.objects.filter(address=user_ip, path=request.path, created__date=today).first()

        if visited_data:
            # If we have a record for today, only update project visit count if needed
            if visited_data.count == 1:
                project.project_visit_count = F("project_visit_count") + 1
                project.save()
        else:
            # If no record exists for today, create a new one
            IP.objects.create(address=user_ip, path=request.path, created=current_time, count=1)

            # Increment the project's visit count
            project.project_visit_count = F("project_visit_count") + 1
            project.save()

        # Get unique visits, grouped by date (last 7 days)
        seven_days_ago = today - timedelta(days=7)
        visit_counts = (
            IP.objects.filter(path=request.path, created__date__gte=seven_days_ago)
            .annotate(date=TruncDate("created"))
            .values("date")
            .annotate(visit_count=Count("address"))
            .order_by("date")
        )

        # Refresh project to get the latest visit count
        project.refresh_from_db()

        # Extract dates and counts
        dates = [entry["date"] for entry in visit_counts]
        counts = [entry["visit_count"] for entry in visit_counts]
        total_views = project.project_visit_count

        # Create a new image with a white background
        width = 600
        height = 200
        img = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(img)

        # Define colors
        bar_color = "#e05d44"
        text_color = "#333333"
        grid_color = "#eeeeee"

        # Calculate chart dimensions
        margin = 40
        chart_width = width - 2 * margin
        chart_height = height - 2 * margin

        if counts:
            max_count = max(counts)
            bar_width = chart_width / (len(counts) * 2)  # Leave space between bars
        else:
            max_count = 1
            bar_width = chart_width / 14  # Default for empty data

        # Draw grid lines
        for i in range(5):
            y = margin + (chart_height * i) // 4
            draw.line([(margin, y), (width - margin, y)], fill=grid_color)

        # Draw bars
        if dates and counts:
            for i, count in enumerate(counts):
                bar_height = (count / max_count) * chart_height
                x1 = margin + (i * 2 * bar_width)
                y1 = height - margin - bar_height
                x2 = x1 + bar_width
                y2 = height - margin

                # Draw bar with a slight gradient effect
                for h in range(int(y1), int(y2)):
                    alpha = int(255 * (1 - (h - y1) / bar_height * 0.2))
                    r, g, b = 224, 93, 68  # RGB values for #e05d44
                    current_color = f"#{r:02x}{g:02x}{b:02x}"
                    draw.line([(x1, h), (x2, h)], fill=current_color)

        # Draw total views text
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 32)
        except OSError:
            font = ImageFont.load_default()

        text = f"Total Views: {total_views}"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        draw.text(((width - text_width) // 2, margin // 2), text, font=font, fill=bar_color)

        # Save the image to a buffer
        buffer = BytesIO()
        img.save(buffer, format="PNG", quality=95)
        buffer.seek(0)

        # Return the image with appropriate headers
        response = HttpResponse(buffer, content_type="image/png")
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"

        return response


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

        # Group repos by project and filter out projects with empty slugs
        projects = {}
        for repo in context["repos"]:
            # Skip projects with empty slugs
            if repo.project and repo.project.slug:
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
                        {"error": "You do not have permission to add projects to this organization"},
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
                    release_datetime=(parse_datetime(release_datetime) if release_datetime else None),
                    open_pull_requests=open_pull_requests,
                )

            except requests.exceptions.RequestException as e:
                continue

        return JsonResponse({"message": "Project created successfully"}, status=201)

    except Organization.DoesNotExist:
        return JsonResponse({"error": "Organization not found", "code": "ORG_NOT_FOUND"}, status=404)
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
            Repo.objects.select_related("project").filter(project=project).prefetch_related("tags", "contributor")
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

        # Add organization context if it exists!
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

    def fetch_github_milestones(self, repo):
        """
        Fetch milestones from the GitHub API for the given repository.
        """
        try:
            repo_url = repo.repo_url.strip("/")

            # Parse the URL properly using urllib
            parsed_url = urlparse(repo_url)

            # Verify it's actually a GitHub domain
            if parsed_url.netloc != "github.com":
                return []

            # Extract the path and remove leading slash
            path = parsed_url.path.strip("/")

            # Split path into components
            path_parts = path.split("/")

            # Verify we have at least owner/repo in the path
            if len(path_parts) >= 2:
                owner, repo_name = path_parts[0], path_parts[1]

                # API URL for public repository milestones
                api_url = f"https://api.github.com/repos/{owner}/{repo_name}/milestones?state=all"

                headers = {"Accept": "application/vnd.github.v3+json"}

                # Add GitHub token if available for higher rate limits
                if hasattr(settings, "GITHUB_TOKEN") and settings.GITHUB_TOKEN and settings.GITHUB_TOKEN != "blank":
                    headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

                response = requests.get(api_url, headers=headers, timeout=10)

                if response.status_code == 200:
                    return response.json()

            return []

        except Exception:
            return []

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

    def fetch_activity_data(self, owner, repo_name):
        """Fetch detailed activity data for charts"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=60)
        headers = {
            "Authorization": f"token {settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }
        base_url = f"https://api.github.com/repos/{owner}/{repo_name}"

        def fetch_all_pages(url):
            results = []
            page = 1
            while True:
                response = requests.get(f"{url}&page={page}", headers=headers)
                if response.status_code != 200 or not response.json():
                    break
                results.extend(response.json())
                page += 1
                if "Link" not in response.headers or 'rel="next"' not in response.headers["Link"]:
                    break
            return results

        # Fetching data concurrently
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                "issues": executor.submit(
                    fetch_all_pages, f"{base_url}/issues?state=all&since={start_date.isoformat()}&per_page=100"
                ),
                "pulls": executor.submit(
                    fetch_all_pages, f"{base_url}/pulls?state=all&since={start_date.isoformat()}&per_page=100"
                ),
                "commits": executor.submit(
                    fetch_all_pages, f"{base_url}/commits?since={start_date.isoformat()}&per_page=100"
                ),
            }

            data = {}
            for key, future in futures.items():
                try:
                    data[key] = future.result()
                except Exception as e:
                    print(f"Error fetching {key}: {e}")
                    data[key] = []

        # Processing data for charts
        dates = [(end_date - timedelta(days=x)).strftime("%Y-%m-%d") for x in range(30)]

        # Defining time periods
        current_month_start = end_date - timedelta(days=30)
        previous_month_start = current_month_start - timedelta(days=30)

        def calculate_period_metrics(data, start_date, end_date):
            """Calculate metrics for a specific time period"""
            start_date = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
            end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

            return {
                "issues_opened": len(
                    [
                        i
                        for i in data["issues"]
                        if i.get("created_at")
                        and start_date <= parse_date(i["created_at"]) <= end_date
                        and "pull_request" not in i
                    ]
                ),
                "issues_closed": len(
                    [
                        i
                        for i in data["issues"]
                        if i.get("closed_at")
                        and start_date <= parse_date(i["closed_at"]) <= end_date
                        and "pull_request" not in i
                    ]
                ),
                "prs_opened": len(
                    [
                        p
                        for p in data["pulls"]
                        if p.get("created_at") and start_date <= parse_date(p["created_at"]) <= end_date
                    ]
                ),
                "prs_closed": len(
                    [
                        p
                        for p in data["pulls"]
                        if p.get("closed_at") and start_date <= parse_date(p["closed_at"]) <= end_date
                    ]
                ),
                "commits": len(
                    [
                        c
                        for c in data["commits"]
                        if c.get("commit", {}).get("author", {}).get("date")
                        and start_date <= parse_date(c["commit"]["author"]["date"]) <= end_date
                    ]
                ),
            }

        # Calculating metrics for both periods
        current_metrics = calculate_period_metrics(data, current_month_start.date(), end_date.date())
        previous_metrics = calculate_period_metrics(data, previous_month_start.date(), current_month_start.date())

        # Calculating percentage changes
        def calculate_percentage_change(current, previous):
            """Calculates percentage change between two periods"""
            if previous == 0:
                return 100 if current > 0 else 0
            return ((current - previous) / previous) * 100

        def calculate_ratio(current, previous):
            if previous == 0:
                return 1 if current > 0 else 0
            return current / previous

        changes = {
            "issue_ratio_percentage_change": calculate_percentage_change(
                (calculate_ratio(current_metrics["issues_opened"], current_metrics["issues_closed"])),
                (calculate_ratio(previous_metrics["issues_opened"], previous_metrics["issues_closed"])),
            ),
            "issue_ratio_change": (calculate_ratio(current_metrics["issues_opened"], current_metrics["issues_closed"]))
            - (calculate_ratio(previous_metrics["issues_opened"], previous_metrics["issues_closed"])),
            "pr_percentage_change": calculate_percentage_change(
                current_metrics["prs_opened"], previous_metrics["prs_opened"]
            ),
            "pr_change": current_metrics["prs_opened"] - previous_metrics["prs_opened"],
            "commit_percentage_change": calculate_percentage_change(
                current_metrics["commits"], previous_metrics["commits"]
            ),
            "commit_change": current_metrics["commits"] - previous_metrics["commits"],
        }

        chart_data = {
            "issues_labels": dates,
            "issues_opened": [],
            "issues_closed": [],
            "pr_labels": dates,
            "pr_opened_data": [],
            "pr_closed_data": [],
            "commits_labels": dates,
            "commits_data": [],
            "pushes_data": [],
            "issue_ratio_change": round(changes["issue_ratio_change"], 2),
            "pr_change": changes["pr_change"],
            "commit_change": changes["commit_change"],
            "issue_ratio_percentage_change": round(changes["issue_ratio_percentage_change"], 2),
            "pr_percentage_change": round(changes["pr_percentage_change"], 2),
            "commit_percentage_change": round(changes["commit_percentage_change"], 2),
        }

        for date in dates:
            # Counting issues with safe null checks
            issues_opened = len(
                [
                    i
                    for i in data["issues"]
                    if i.get("created_at") and i["created_at"].startswith(date) and "pull_request" not in i
                ]
            )

            issues_closed = len(
                [
                    i
                    for i in data["issues"]
                    if i.get("closed_at") and i["closed_at"].startswith(date) and "pull_request" not in i
                ]
            )

            # Counting PRs with safe null checks
            prs_opened = len([p for p in data["pulls"] if p.get("created_at") and p["created_at"].startswith(date)])

            prs_closed = len([p for p in data["pulls"] if p.get("closed_at") and p["closed_at"].startswith(date)])

            # Counting commits with safe null checks
            day_commits = [
                c
                for c in data["commits"]
                if (
                    c.get("commit", {}).get("author", {}).get("date") and c["commit"]["author"]["date"].startswith(date)
                )
            ]
            commits_count = len(day_commits)
            pushes_count = len(set(c.get("sha", "") for c in day_commits))

            # Adding to chart data
            chart_data["issues_opened"].append(issues_opened)
            chart_data["issues_closed"].append(issues_closed)
            chart_data["pr_opened_data"].append(prs_opened)
            chart_data["pr_closed_data"].append(prs_closed)
            chart_data["commits_data"].append(commits_count)
            chart_data["pushes_data"].append(pushes_count)

        return chart_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        repo = self.get_object()

        # Extract owner and repo name from repo URL
        owner_repo = repo.repo_url.rstrip("/").split("github.com/")[-1]
        owner, repo_name = owner_repo.split("/")

        # Add show_repo_stats parameter set to False to hide stats section
        context["show_repo_stats"] = False

        # Get activity data only if we're showing repo stats
        activity_data = None
        if context["show_repo_stats"]:
            activity_data = self.fetch_activity_data(owner, repo_name)
        else:
            # Create empty activity data structure to avoid template errors
            activity_data = {
                "issues_labels": [],
                "issues_opened": [],
                "issues_closed": [],
                "pr_labels": [],
                "pr_opened_data": [],
                "pr_closed_data": [],
                "commits_labels": [],
                "commits_data": [],
                "pushes_data": [],
                "issue_ratio_change": 0,
                "pr_change": 0,
                "commit_change": 0,
                "issue_ratio_percentage_change": 0,
                "pr_percentage_change": 0,
                "commit_percentage_change": 0,
            }

        # Add breadcrumbs
        context["breadcrumbs"] = [
            {"title": "Repositories", "url": reverse("project_list")},
            {"title": repo.name, "url": None},
        ]

        # Get other repos from same project
        context["related_repos"] = (
            Repo.objects.filter(project=repo.project).exclude(id=repo.id).select_related("project")[:5]
        )

        # Get top contributors from GitHub
        github_contributors = self.get_github_top_contributors(repo.repo_url)

        if github_contributors:
            # Match by github_id instead of username
            github_ids = [str(c["id"]) for c in github_contributors]
            verified_contributors = repo.contributor.filter(github_id__in=github_ids).select_related()

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
                response = requests.get(f"https://api.github.com/repos/{owner}/{repo_name}", headers=headers)
                if response.status_code == 200:
                    repo_data = response.json()
                    start_date = datetime.strptime(repo_data["created_at"], "%Y-%m-%dT%H:%M:%SZ").date()
                else:
                    start_date = end_date - relativedelta(years=1)  # Fallback to 1 year
            except Exception:
                start_date = end_date - relativedelta(years=1)  # Fallback to 1 year

        # Query contributor stats
        stats_query = ContributorStats.objects.filter(repo=repo, date__gte=start_date, date__lte=end_date)

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
                impact_level = {
                    "class": "bg-green-100 text-green-800",
                    "text": "High Impact",
                }
            elif impact_score > 100:
                impact_level = {
                    "class": "bg-yellow-100 text-yellow-800",
                    "text": "Medium Impact",
                }
            else:
                impact_level = {
                    "class": "bg-blue-100 text-blue-800",
                    "text": "Growing Impact",
                }

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
                "issues_labels": activity_data["issues_labels"],
                "issues_opened": activity_data["issues_opened"],
                "issues_closed": activity_data["issues_closed"],
                "pr_labels": activity_data["pr_labels"],
                "pr_opened_data": activity_data["pr_opened_data"],
                "pr_closed_data": activity_data["pr_closed_data"],
                "commits_labels": activity_data["commits_labels"],
                "commits_data": activity_data["commits_data"],
                "pushes_data": activity_data["pushes_data"],
                "issue_ratio_change": activity_data["issue_ratio_change"],
                "pr_change": activity_data["pr_change"],
                "commit_change": activity_data["commit_change"],
                "issue_ratio_percentage_change": activity_data["issue_ratio_percentage_change"],
                "pr_percentage_change": activity_data["pr_percentage_change"],
                "commit_percentage_change": activity_data["commit_percentage_change"],
            }
        )

        milestones = self.fetch_github_milestones(repo)

        # Get the current page from query parameters
        milestone_page = self.request.GET.get("milestone_page", 1)
        try:
            milestone_page = int(milestone_page)
        except (TypeError, ValueError):
            milestone_page = 1

        # Calculate activity score for each milestone (open_issues + closed_issues)
        for milestone in milestones:
            milestone["activity_score"] = milestone.get("open_issues", 0) + milestone.get("closed_issues", 0)

        # Sort milestones: first by state (open first), then by activity score (highest first)
        milestones.sort(
            key=lambda x: (
                0 if x.get("state") == "open" else 1,  # Open milestones first
                -x.get("activity_score", 0),  # Higher activity score first
                x.get("due_on", "") or "9999-12-31T23:59:59Z",  # Then by due date
            )
        )

        # Paginate the milestones - 5 per page
        milestones_per_page = 5
        total_milestones = len(milestones)
        total_pages = (total_milestones + milestones_per_page - 1) // milestones_per_page

        # Ensure the page number is within valid range
        if milestone_page < 1:
            milestone_page = 1
        elif milestone_page > total_pages and total_pages > 0:
            milestone_page = total_pages

        # Calculate start and end indices for slicing
        start_idx = (milestone_page - 1) * milestones_per_page
        end_idx = min(start_idx + milestones_per_page, total_milestones)

        # Slice the milestones list
        paginated_milestones = milestones[start_idx:end_idx] if milestones else []

        # Add the paginated milestones and pagination info to context
        context["milestones"] = paginated_milestones
        context["milestone_pagination"] = {
            "current_page": milestone_page,
            "total_pages": total_pages,
            "has_previous": milestone_page > 1,
            "has_next": milestone_page < total_pages,
            "previous_page": milestone_page - 1 if milestone_page > 1 else None,
            "next_page": milestone_page + 1 if milestone_page < total_pages else None,
            "page_range": range(1, total_pages + 1),
        }

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()  # Fix the missing object attribute

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            if "time_period" in request.POST:
                context = self.get_context_data()
                return render(request, "includes/_contributor_stats_table.html", context)

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
                        {"status": "error", "message": "GitHub token not configured"},
                        status=500,
                    )

                # Extract owner/repo from GitHub URL
                match = re.match(r"https://github.com/([^/]+)/([^/]+)/?", repo.repo_url)
                if not match:
                    return JsonResponse(
                        {"status": "error", "message": "Invalid repository URL"},
                        status=400,
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
                        {
                            "status": "error",
                            "message": f"GitHub API error: {response.status_code}",
                        },
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
                    {
                        "status": "error",
                        "message": "There was an error processing your data.",
                    },
                    status=400,
                )

        elif section == "metrics":
            try:
                github_token = getattr(settings, "GITHUB_TOKEN", None)
                if not github_token:
                    return JsonResponse(
                        {"status": "error", "message": "GitHub token not configured"},
                        status=500,
                    )

                match = re.match(r"https://github.com/([^/]+)/([^/]+)/?", repo.repo_url)
                if not match:
                    return JsonResponse(
                        {"status": "error", "message": "Invalid repository URL"},
                        status=400,
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
                        {
                            "status": "error",
                            "message": "Failed to fetch repository data",
                        },
                        status=500,
                    )

                repo_data = response.json()
                full_name = repo_data.get("full_name")
                default_branch = repo_data.get("default_branch")
                if not full_name:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "Could not get repository full name",
                        },
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
                            "last_commit_date": (
                                repo.last_commit_date.strftime("%b %d, %Y") if repo.last_commit_date else ""
                            ),
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
                    {
                        "status": "error",
                        "message": "There was an error processing your data.",
                    },
                    status=400,
                )

        elif section == "technical":
            try:
                github_token = getattr(settings, "GITHUB_TOKEN", None)
                if not github_token:
                    return JsonResponse(
                        {"status": "error", "message": "GitHub token not configured"},
                        status=500,
                    )

                match = re.match(r"https://github.com/([^/]+)/([^/]+)/?", repo.repo_url)
                if not match:
                    return JsonResponse(
                        {"status": "error", "message": "Invalid repository URL"},
                        status=400,
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
                        {
                            "status": "error",
                            "message": "Failed to fetch repository data",
                        },
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
                            "release_date": (
                                repo.release_datetime.strftime("%b %d, %Y")
                                if repo.release_datetime
                                else "Not available"
                            ),
                            "last_commit_date": (
                                repo.last_commit_date.strftime("%b %d, %Y")
                                if repo.last_commit_date
                                else "Not available"
                            ),
                        },
                    }
                )

            except requests.RequestException as e:
                sentry_sdk.capture_exception(e)
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Network error: A network error occurred. Please try again later.",
                    },
                    status=503,
                )
            except Exception as e:
                # send to sentry
                sentry_sdk.capture_exception(e)
                return JsonResponse(
                    {"status": "error", "message": "An unexpected error occurred."},
                    status=500,
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
                    {
                        "status": "error",
                        "message": "There was an error processing your data.",
                    },
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

        elif section == "ai_summary":
            try:
                repo = self.get_object()

                # Get GitHub API token
                github_token = getattr(settings, "GITHUB_TOKEN", None)
                if not github_token:
                    return JsonResponse(
                        {"status": "error", "message": "GitHub token not configured"},
                        status=500,
                    )

                # Extract owner/repo from GitHub URL
                match = re.match(r"https://github.com/([^/]+)/([^/]+)/?", repo.repo_url)
                if not match:
                    return JsonResponse(
                        {"status": "error", "message": "Invalid repository URL"},
                        status=400,
                    )

                owner, repo_name = match.groups()

                # Fetch README content from GitHub API
                readme_url = f"https://api.github.com/repos/{owner}/{repo_name}/readme"
                headers = {
                    "Authorization": f"token {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                }

                response = requests.get(readme_url, headers=headers)

                if response.status_code == 200:
                    readme_data = response.json()
                    # README content is base64 encoded
                    import base64

                    readme_content = base64.b64decode(readme_data.get("content", "")).decode("utf-8")

                    # Store README content
                    repo.readme_content = readme_content

                    # Generate AI summary if AI service is configured
                    ai_service_url = getattr(settings, "AI_SERVICE_URL", None)
                    if ai_service_url:
                        try:
                            # Call AI service to generate summary
                            ai_response = requests.post(ai_service_url, json={"text": readme_content}, timeout=10)

                            if ai_response.status_code == 200:
                                ai_data = ai_response.json()
                                repo.ai_summary = ai_data.get("summary", "No summary available.")
                            else:
                                repo.ai_summary = "Failed to generate summary from AI service."
                        except Exception:
                            repo.ai_summary = "Error connecting to AI service."
                    else:
                        # If no AI service is configured, create a simple summary
                        if len(readme_content) > 500:
                            repo.ai_summary = readme_content[:500] + "..."
                        else:
                            repo.ai_summary = readme_content

                    repo.save()

                    return JsonResponse(
                        {
                            "status": "success",
                            "message": "AI summary updated successfully",
                            "data": {"ai_summary": repo.ai_summary or "No summary available."},
                        }
                    )
                else:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": f"GitHub API error: {response.status_code}",
                        },
                        status=response.status_code,
                    )

            except Exception as e:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"An unexpected error occurred: {str(e)}",
                    },
                    status=500,
                )

        # Return a default response if no section matched
        return JsonResponse({"status": "error", "message": "Invalid section specified " + section}, status=400)


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
        current_time = now()
        today = current_time.date()

        # Get the real client IP
        user_ip = self.get_client_ip(request)

        # Check if we have a record for today
        visited_data = IP.objects.filter(address=user_ip, path=request.path, created__date=today).first()

        if visited_data:
            # If we have a record for today, only update repo visit count if needed
            if visited_data.count == 1:
                repo.repo_visit_count = F("repo_visit_count") + 1
                repo.save()
        else:
            # If no record exists for today, create a new one
            IP.objects.create(address=user_ip, path=request.path, created=current_time, count=1)

            # Increment the repo's visit count
            repo.repo_visit_count = F("repo_visit_count") + 1
            repo.save()

        # Get unique visits, grouped by date (last 7 days)
        seven_days_ago = today - timedelta(days=7)
        visit_counts = (
            IP.objects.filter(path=request.path, created__date__gte=seven_days_ago)
            .annotate(date=TruncDate("created"))
            .values("date")
            .annotate(visit_count=Count("address"))
            .order_by("date")
        )

        # Refresh repo to get the latest visit count
        repo.refresh_from_db()

        # Extract dates and counts
        dates = [entry["date"] for entry in visit_counts]
        counts = [entry["visit_count"] for entry in visit_counts]
        total_views = repo.repo_visit_count

        # Create a new image with a white background
        width = 600
        height = 200
        img = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(img)

        # Define colors
        bar_color = "#e05d44"
        text_color = "#333333"
        grid_color = "#eeeeee"

        # Calculate chart dimensions
        margin = 40
        chart_width = width - 2 * margin
        chart_height = height - 2 * margin

        # Draw grid lines
        for i in range(5):
            y = margin + (chart_height * i) // 4
            draw.line([(margin, y), (width - margin, y)], fill=grid_color)

        # Draw bars
        if dates and counts:
            max_count = max(counts)
            bar_width = chart_width / (len(counts) * 2)  # Leave space between bars
            for i, count in enumerate(counts):
                bar_height = (count / max_count) * chart_height
                x1 = margin + (i * 2 * bar_width)
                y1 = height - margin - bar_height
                x2 = x1 + bar_width
                y2 = height - margin

                # Draw bar with a slight gradient effect
                for h in range(int(y1), int(y2)):
                    alpha = int(255 * (1 - (h - y1) / bar_height * 0.2))
                    r, g, b = 224, 93, 68  # RGB values for #e05d44
                    current_color = f"#{r:02x}{g:02x}{b:02x}"
                    draw.line([(x1, h), (x2, h)], fill=current_color)

        # Draw total views text
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 32)
        except OSError:
            font = ImageFont.load_default()

        text = f"Total Views: {total_views}"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        draw.text(((width - text_width) // 2, margin // 2), text, font=font, fill=bar_color)

        # Save the image to a buffer
        buffer = BytesIO()
        img.save(buffer, format="PNG", quality=95)
        buffer.seek(0)

        # Return the image with appropriate headers
        response = HttpResponse(buffer, content_type="image/png")
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"

        return response
