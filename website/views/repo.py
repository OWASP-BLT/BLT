import re
import time

import requests
from django.conf import settings
from django.db.models import Count, Q
from django.http import JsonResponse
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
        section = request.POST.get("section")

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

        # Handle other section refreshes...
        return JsonResponse({"status": "error", "message": "Invalid section"}, status=400)

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
