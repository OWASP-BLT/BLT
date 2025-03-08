import os
import re
import time

import psutil
import requests
from django.conf import settings
from django.db import connection
from django.db.models import Count, Q
from django.http import JsonResponse
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView

from website.models import Organization, Repo
from website.utils import ai_summary, markdown_to_text


class RepoListView(ListView):
    model = Repo
    template_name = "repo/repo_list.html"
    context_object_name = "repos"
    paginate_by = 100

    def get_queryset(self):
        # Start with all repos instead of just OWASP repos
        queryset = Repo.objects.all()

        # Handle language filter
        language = self.request.GET.get("language")
        if language:
            queryset = queryset.filter(primary_language=language)

        # Handle organization filter
        organization = self.request.GET.get("organization")
        if organization:
            queryset = queryset.filter(organization__id=organization)

        # Handle search query
        search_query = self.request.GET.get("q")
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(primary_language__icontains=search_query)
            )

        # Get sort parameter from URL, default to -stars
        sort_by = self.request.GET.get("sort", "-stars")
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
            "closed_pull_requests",
            "primary_language",
            "contributor_count",
            "last_updated",
        ]

        if field in valid_fields:
            # Apply the sort
            queryset = queryset.order_by(f"{direction}{field}")
        else:
            # Default sort
            queryset = queryset.order_by("-stars")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_sort"] = self.request.GET.get("sort", "-stars")

        # Get the filtered queryset count instead of all repos
        context["total_repos"] = self.get_queryset().count()

        # Get organizations from related Organization model
        organizations = Organization.objects.filter(repos__isnull=False).distinct()
        context["organizations"] = organizations

        # Get current organization filter
        context["current_organization"] = self.request.GET.get("organization")

        # Get organization name if filtered by organization
        if context["current_organization"]:
            try:
                org = Organization.objects.get(id=context["current_organization"])
                context["current_organization_name"] = org.name
            except Organization.DoesNotExist:
                context["current_organization_name"] = None

        # Get language counts based on current filters
        queryset = Repo.objects.all()

        # Apply organization filter if selected
        if context["current_organization"]:
            queryset = queryset.filter(organization__id=context["current_organization"])

        # Apply search filter if present
        search_query = self.request.GET.get("q")
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(primary_language__icontains=search_query)
            )

        # Get language counts from filtered queryset
        language_counts = (
            queryset.exclude(primary_language__isnull=True)
            .exclude(primary_language="")
            .values("primary_language")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        context["languages"] = language_counts

        # Get current language filter
        context["current_language"] = self.request.GET.get("language")

        return context


class RepoDetailView(DetailView):
    model = Repo
    template_name = "projects/repo_detail.html"
    context_object_name = "repo"

    def post(self, request, *args, **kwargs):
        repo = self.get_object()

        # Debug all POST data
        print(f"POST data: {request.POST}")
        print(f"Content-Type: {request.headers.get('Content-Type', 'Not provided')}")

        # Get section parameter
        section = request.POST.get("section")
        print(f"Section from POST: '{section}'")

        # If section is not in POST data, try to get it from body
        if not section:
            try:
                # Try to parse the request body
                import json
                from urllib.parse import parse_qs

                content_type = request.headers.get("Content-Type", "").lower()
                body_str = request.body.decode("utf-8")
                print(f"Raw body: {body_str}")

                if "application/json" in content_type:
                    # Try to parse as JSON
                    try:
                        body_data = json.loads(body_str)
                        if "section" in body_data:
                            section = body_data["section"]
                            print(f"Section from JSON body: '{section}'")
                    except json.JSONDecodeError:
                        print("Failed to parse body as JSON")

                elif "application/x-www-form-urlencoded" in content_type:
                    # Try to parse as form data
                    body_params = parse_qs(body_str)
                    if "section" in body_params:
                        section = body_params["section"][0]
                        print(f"Section from form body: '{section}'")

                elif "multipart/form-data" in content_type:
                    # For multipart/form-data, we should already have it in request.POST
                    # But we can try to parse the boundary and extract data if needed
                    print("Multipart form data detected, should be in request.POST")

                # If still no section, try a simple key=value parsing
                if not section:
                    body_params = {}
                    for param in body_str.split("&"):
                        if "=" in param:
                            key, value = param.split("=", 1)
                            from urllib.parse import unquote_plus

                            body_params[key] = unquote_plus(value)

                    if "section" in body_params:
                        section = body_params["section"]
                        print(f"Section from simple parsing: '{section}'")
            except Exception as e:
                print(f"Error parsing body: {e}")

        # Normalize the section parameter
        if section:
            if isinstance(section, str):
                section = section.strip().lower()
                print(f"Normalized section: '{section}'")
        else:
            return JsonResponse({"status": "error", "message": "No section parameter provided"}, status=400)

        # Define valid sections
        valid_sections = ["ai_summary", "basic", "metrics", "community", "contributor_stats", "technical"]

        # Check if the section is valid
        if section not in valid_sections:
            error_msg = f"Invalid section specified: '{section}'. Valid sections are: {', '.join(valid_sections)}"
            return JsonResponse({"status": "error", "message": error_msg}, status=400)

        if section == "ai_summary":
            try:
                # Generate new AI summary from readme content
                if repo.readme_content:
                    try:
                        new_summary = ai_summary(markdown_to_text(repo.readme_content))
                        repo.ai_summary = new_summary
                        repo.save()
                        return JsonResponse(
                            {
                                "status": "success",
                                "message": "AI summary regenerated successfully",
                                "data": {"ai_summary": new_summary},
                            }
                        )
                    except Exception as e:
                        # Convert the error to a string and return a proper JSON response
                        error_message = str(e)
                        return JsonResponse(
                            {
                                "status": "error",
                                "message": f"Failed to generate AI summary: {error_message}",
                            },
                            status=500,
                        )
                else:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "No readme content available to generate summary",
                        },
                        status=400,
                    )
            except Exception as e:
                # Convert the error to a string and return a proper JSON response
                error_message = str(e)
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"An unexpected error occurred: {error_message}",
                    },
                    status=500,
                )
        elif section in ["basic", "metrics", "community", "contributor_stats", "technical"]:
            # These sections are handled in the frontend but need a valid response
            # In the future, we can add server-side processing for each section
            try:
                # For now, just return a success response with empty data
                # The frontend will handle displaying the current data
                return JsonResponse(
                    {
                        "status": "success",
                        "message": f"{section.replace('_', ' ').title()} data refreshed successfully",
                        "data": {},
                    }
                )
            except Exception as e:
                error_message = str(e)
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"An error occurred while refreshing {section}: {error_message}",
                    },
                    status=500,
                )

    def fetch_github_milestones(self, repo):
        """
        Fetch milestones from the GitHub API for the given repository.
        """
        milestones_url = f"https://api.github.com/repos/{repo.repo_url.split('github.com/')[-1]}/milestones"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {settings.GITHUB_TOKEN}",
        }
        response = requests.get(milestones_url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        repo = self.get_object()
        context["milestones"] = self.fetch_github_milestones(repo)

        # Add breadcrumbs
        breadcrumbs = [
            {"title": "Repositories", "url": reverse("repo_list")},
        ]
        if repo.project:
            breadcrumbs.append(
                {"title": repo.project.name, "url": reverse("project_detail", kwargs={"slug": repo.project.slug})}
            )
        breadcrumbs.append({"title": repo.name})
        context["breadcrumbs"] = breadcrumbs

        # Add top contributors
        context["top_contributors"] = repo.get_top_contributors()

        # Add current language filter for highlighting in template
        context["current_language"] = self.request.GET.get("language")

        # Get system stats for developer mode
        system_stats = None
        if settings.DEBUG:
            import django

            system_stats = {
                "memory_usage": f"{psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024):.2f} MB",
                "cpu_percent": f"{psutil.Process(os.getpid()).cpu_percent(interval=0.1):.2f}%",
                "python_version": f"{os.sys.version}",
                "django_version": django.get_version(),
                "db_connections": len(connection.queries),
            }

        # Add system stats to context
        context["system_stats"] = system_stats

        return context


@csrf_protect
@require_http_methods(["POST"])
def add_repo(request):
    try:
        # Get repo URL from request and clean it
        repo_url = request.POST.get("repo_url", "").strip()
        # Remove @ if it exists at the start
        repo_url = repo_url.lstrip("@")

        if not repo_url:
            return JsonResponse(
                {"status": "error", "message": "Repository URL is required"},
                status=400,
            )

        # Convert GitHub URL to API URL
        match = re.match(r"^(?:https?://)?github\.com/([^/]+)/([^/]+)/?$", repo_url)
        if not match:
            error_msg = (
                "Invalid GitHub repository URL. " "Please provide a URL in the format: https://github.com/owner/repo"
            )
            return JsonResponse(
                {"status": "error", "message": error_msg},
                status=400,
            )

        owner, repo_name = match.groups()
        api_url = f"https://api.github.com/repos/{owner}/{repo_name}"

        # Check if repo already exists
        if Repo.objects.filter(repo_url=f"https://github.com/{owner}/{repo_name}").exists():
            return JsonResponse(
                {"status": "error", "message": "Repository already exists"},
                status=400,
            )

        # First try with token if available
        github_token = getattr(settings, "GITHUB_TOKEN", None)
        headers = {"Accept": "application/vnd.github.v3+json"}
        use_token = False

        if github_token:
            headers["Authorization"] = f"token {github_token}"
            # Test the token with a request
            test_response = requests.get(api_url, headers=headers)
            use_token = test_response.status_code != 401  # Keep token if not unauthorized

        if not use_token:
            # Remove auth header if token is invalid or missing
            headers.pop("Authorization", None)
            print("Using anonymous GitHub API access")  # Debug log

        # Fetch repository data
        print(f"Fetching repo data from: {api_url}")  # Debug log
        response = requests.get(api_url, headers=headers)
        print(f"GitHub API Response Status: {response.status_code}")  # Debug log

        if response.status_code == 404:
            return JsonResponse(
                {"status": "error", "message": "Repository not found on GitHub"},
                status=404,
            )
        elif response.status_code == 403:
            return JsonResponse(
                {"status": "error", "message": "Rate limit exceeded. Please try again later."},
                status=403,
            )
        elif response.status_code != 200:
            error_data = response.json()
            error_message = error_data.get("message", "Failed to fetch repository data")
            print(f"GitHub API Error: {error_message}")  # Debug log
            return JsonResponse(
                {"status": "error", "message": f"GitHub API Error: {error_message}"},
                status=response.status_code,
            )

        repo_data = response.json()
        full_name = repo_data.get("full_name")
        if not full_name:
            return JsonResponse(
                {"status": "error", "message": "Could not get repository full name"},
                status=500,
            )

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

        # Get issue counts
        def get_issue_count(full_name, query, headers):
            search_url = f"https://api.github.com/search/issues?q=repo:{full_name}+{query}"
            resp = requests.get(search_url, headers=headers)
            if resp.status_code == 200:
                return resp.json().get("total_count", 0)
            return 0

        open_issues = get_issue_count(full_name, "type:issue+state:open", headers)
        closed_issues = get_issue_count(full_name, "type:issue+state:closed", headers)
        open_pull_requests = get_issue_count(full_name, "type:pr+state:open", headers)
        total_issues = open_issues + closed_issues

        # Get contributors count and commit count
        commit_count = 0
        all_contributors = []
        page = 1
        while True:
            contrib_url = f"{api_url}/contributors?anon=true&per_page=100&page={page}"
            c_resp = requests.get(contrib_url, headers=headers)
            if c_resp.status_code != 200:
                break
            contributors_data = c_resp.json()
            if not contributors_data:
                break
            commit_count += sum(c.get("contributions", 0) for c in contributors_data)
            all_contributors.extend(contributors_data)
            page += 1

        # Get latest release info
        release_name = None
        release_datetime = None
        releases_url = f"{api_url}/releases/latest"
        release_resp = requests.get(releases_url, headers=headers)
        if release_resp.status_code == 200:
            release_info = release_resp.json()
            release_name = release_info.get("name") or release_info.get("tag_name")
            release_datetime = release_info.get("published_at")

        # Create repository
        repo = Repo.objects.create(
            slug=unique_slug,
            name=repo_data["name"],
            description=repo_data.get("description", ""),
            repo_url=repo_url,
            homepage_url=repo_data.get("homepage", ""),
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
            is_archived=repo_data.get("archived", False),
        )

        # Try to fetch and generate AI summary from README
        readme_url = f"{api_url}/readme"
        readme_resp = requests.get(readme_url, headers=headers)
        if readme_resp.status_code == 200:
            readme_data = readme_resp.json()
            import base64

            readme_content = base64.b64decode(readme_data["content"]).decode("utf-8")
            repo.readme_content = readme_content
            repo.ai_summary = ai_summary(markdown_to_text(readme_content))
            repo.save()

        return JsonResponse(
            {
                "status": "success",
                "message": "Repository added successfully",
                "data": {"slug": repo.slug},
            }
        )

    except Exception as e:
        return JsonResponse(
            {"status": "error", "message": f"An error occurred: {str(e)}"},
            status=500,
        )
