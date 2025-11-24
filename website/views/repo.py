import logging
import os
import re
import time

import psutil
import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.db import connection
from django.db.models import Count, Q
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import DetailView, ListView

from website.models import GitHubIssue, Organization, Repo
from website.utils import ai_summary, markdown_to_text

logger = logging.getLogger(__name__)


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
            try:
                organization = int(organization)
                queryset = queryset.filter(organization__id=organization)
            except (ValueError, TypeError):
                raise ValueError("Invalid organization ID: must be a valid integer.")

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
        logger.debug(f"POST data: {request.POST}")
        logger.debug(f"Content-Type: {request.headers.get('Content-Type', 'Not provided')}")

        # Get section parameter
        section = request.POST.get("section")
        logger.debug(f"Section from POST: '{section}'")

        # If section is not in POST data, try to get it from body
        if not section:
            try:
                # Try to parse the request body
                import json
                from urllib.parse import parse_qs

                content_type = request.headers.get("Content-Type", "").lower()
                body_str = request.body.decode("utf-8")
                logger.debug(f"Raw body: {body_str}")

                if "application/json" in content_type:
                    # Try to parse as JSON
                    try:
                        body_data = json.loads(body_str)
                        if "section" in body_data:
                            section = body_data["section"]
                            logger.debug(f"Section from JSON body: '{section}'")
                    except json.JSONDecodeError:
                        logger.debug("Failed to parse body as JSON")

                elif "application/x-www-form-urlencoded" in content_type:
                    # Try to parse as form data
                    body_params = parse_qs(body_str)
                    if "section" in body_params:
                        section = body_params["section"][0]
                        logger.debug(f"Section from form body: '{section}'")

                elif "multipart/form-data" in content_type:
                    # For multipart/form-data, we should already have it in request.POST
                    # But we can try to parse the boundary and extract data if needed
                    logger.debug("Multipart form data detected, should be in request.POST")

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
                        logger.debug(f"Section from simple parsing: '{section}'")
            except Exception as e:
                logger.warning(f"Error parsing body: {e}")

        # Normalize the section parameter
        if section:
            if isinstance(section, str):
                section = section.strip().lower()
                logger.debug(f"Normalized section: '{section}'")
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

        # Add GitHub issues and PRs to context
        context["github_issues"] = repo.github_issues.filter(type="issue").order_by("-updated_at")[:10]
        context["github_prs"] = repo.github_issues.filter(type="pull_request").order_by("-updated_at")[:10]

        # Add counts for issues and PRs
        context["github_issues_count"] = repo.github_issues.filter(type="issue").count()
        context["github_prs_count"] = repo.github_issues.filter(type="pull_request").count()

        # Add dollar tag issues
        context["dollar_tag_issues"] = repo.github_issues.filter(has_dollar_tag=True).order_by("-updated_at")[:5]
        context["dollar_tag_issues_count"] = repo.github_issues.filter(has_dollar_tag=True).count()

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
            logger.debug("Using anonymous GitHub API access")

        # Fetch repository data
        logger.debug(f"Fetching repo data from: {api_url}")
        response = requests.get(api_url, headers=headers)
        logger.debug(f"GitHub API Response Status: {response.status_code}")

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
            logger.error(f"GitHub API Error: {error_message}")
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


@login_required
@require_POST
def refresh_repo_data(request, repo_id):
    """
    Run the update_repos_dynamic command for a specific repository
    """
    try:
        logger.info(f"Refresh request received for repo_id: {repo_id}")

        # Check if the repository exists
        repo = Repo.objects.get(id=repo_id)

        # Log the refresh attempt
        logger.info(f"Refreshing repository data for {repo.name} (ID: {repo_id})")
        logger.debug(f"Repository URL: {repo.repo_url}")

        try:
            # Run the command with the specific repo ID
            logger.debug("Calling update_repos_dynamic command...")
            call_command("update_repos_dynamic", repo_id=repo_id)
            logger.debug("Command completed successfully")

            # Refresh the repo object to get the latest data
            repo.refresh_from_db()

            # Get updated counts
            issues_count = repo.github_issues.filter(type="issue").count()
            prs_count = repo.github_issues.filter(type="pull_request").count()
            dollar_tag_count = repo.github_issues.filter(has_dollar_tag=True).count()

            # Log the results
            logger.info(
                f"Repository refresh complete. Issues: {issues_count}, "
                f"PRs: {prs_count}, Bounty Issues: {dollar_tag_count}"
            )

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Repository data refreshed successfully",
                    "data": {
                        "issues_count": issues_count,
                        "prs_count": prs_count,
                        "dollar_tag_count": dollar_tag_count,
                        "last_updated": repo.last_updated.isoformat() if repo.last_updated else None,
                    },
                }
            )
        except Exception as cmd_error:
            logger.error(f"Error running command: {str(cmd_error)}")
            logger.error(f"Error type: {type(cmd_error).__name__}")
            import traceback

            logger.error(traceback.format_exc())

            return JsonResponse(
                {
                    "status": "error",
                    "message": f"Error running update command: {str(cmd_error)}",
                    "error_type": type(cmd_error).__name__,
                },
                status=500,
            )

    except Repo.DoesNotExist:
        logger.warning(f"Repository with ID {repo_id} not found")
        return JsonResponse({"status": "error", "message": "Repository not found"}, status=404)
    except Exception as e:
        logger.error(f"Error refreshing repository data: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback

        logger.error(traceback.format_exc())

        return JsonResponse(
            {
                "status": "error",
                "message": f"An error occurred while refreshing repository data: {str(e)}",
                "error_type": type(e).__name__,
            },
            status=500,
        )


@login_required
def update_repo_data_stream(request, slug):
    """
    Update repository data with real-time SSE (Server-Sent Events) feedback.
    Similar to organization repo updates but for a single repository.
    """
    try:
        repo = get_object_or_404(Repo, slug=slug)

        # Check if repository was updated in the last hour to prevent abuse
        one_hour_ago = timezone.timedelta(hours=1)
        if repo.last_updated and timezone.now() < repo.last_updated + one_hour_ago:
            time_since_update = timezone.now() - repo.last_updated
            minutes_remaining = 60 - int(time_since_update.total_seconds() / 60)

            def rate_limit_stream():
                yield (
                    f"data: $ Error: Repository was updated recently. "
                    f"Please wait {minutes_remaining} minutes before updating again.\n\n"
                )
                yield "data: DONE\n\n"

            return StreamingHttpResponse(rate_limit_stream(), content_type="text/event-stream")

        def event_stream():
            try:
                yield f"data: $ Starting repository update for: {repo.name}\n\n"
                yield f"data: $ Repository URL: {repo.repo_url}\n\n"

                # Check if GitHub token is set
                if not hasattr(settings, "GITHUB_TOKEN") or not settings.GITHUB_TOKEN:
                    logger.error("GitHub token not set in settings")
                    yield "data: $ Error: GitHub API token not configured\n\n"
                    yield "data: DONE\n\n"
                    return

                # Test GitHub API token validity
                yield "data: $ Testing GitHub API token...\n\n"
                try:
                    rate_limit_url = "https://api.github.com/rate_limit"
                    response = requests.get(
                        rate_limit_url,
                        headers={
                            "Authorization": f"token {settings.GITHUB_TOKEN}",
                            "Accept": "application/vnd.github.v3+json",
                        },
                        timeout=10,
                    )

                    if response.status_code == 200:
                        rate_data = response.json()
                        core_rate = rate_data.get("resources", {}).get("core", {})
                        remaining = core_rate.get("remaining", 0)
                        limit = core_rate.get("limit", 0)

                        yield f"data: $ GitHub API token is valid. Rate limit: {remaining}/{limit}\n\n"

                        if remaining < 50:
                            yield "data: $ Warning: GitHub API rate limit is low. Updates may be incomplete.\n\n"
                    else:
                        yield f"data: $ Error: GitHub API returned {response.status_code}\n\n"
                        yield "data: DONE\n\n"
                        return
                except requests.exceptions.RequestException as e:
                    yield f"data: $ Error testing GitHub API: {str(e)[:100]}\n\n"
                    yield "data: DONE\n\n"
                    return

                # Extract owner and repo name from the repo URL
                match = re.match(r"^(?:https?://)?github\.com/([^/]+)/([^/]+)/?$", repo.repo_url)
                if not match:
                    yield "data: $ Error: Invalid GitHub repository URL format\n\n"
                    yield "data: DONE\n\n"
                    return

                owner, repo_name = match.groups()
                api_url = f"https://api.github.com/repos/{owner}/{repo_name}"

                # Fetch repository data
                yield "data: $ Fetching repository data from GitHub API...\n\n"
                try:
                    response = requests.get(
                        api_url,
                        headers={
                            "Authorization": f"token {settings.GITHUB_TOKEN}",
                            "Accept": "application/vnd.github.v3+json",
                        },
                        timeout=10,
                    )

                    if response.status_code == 404:
                        yield "data: $ Error: Repository not found on GitHub\n\n"
                        yield "data: DONE\n\n"
                        return
                    elif response.status_code != 200:
                        yield f"data: $ Error: GitHub API returned {response.status_code}\n\n"
                        yield "data: DONE\n\n"
                        return

                    repo_data = response.json()
                    yield "data: $ Repository data fetched successfully\n\n"

                    # Update basic repository information
                    yield "data: $ Updating repository metadata...\n\n"
                    repo.description = repo_data.get("description", "")
                    repo.stars = repo_data.get("stargazers_count", 0)
                    repo.forks = repo_data.get("forks_count", 0)
                    repo.watchers = repo_data.get("watchers_count", 0)
                    repo.primary_language = repo_data.get("language")
                    repo.license = repo_data.get("license", {}).get("name") if repo_data.get("license") else None
                    repo.last_commit_date = (
                        parse_datetime(repo_data.get("pushed_at")) if repo_data.get("pushed_at") else None
                    )
                    repo.network_count = repo_data.get("network_count", 0)
                    repo.subscribers_count = repo_data.get("subscribers_count", 0)
                    repo.size = repo_data.get("size", 0)
                    repo.is_archived = repo_data.get("archived", False)
                    repo.last_updated = timezone.now()
                    repo.save()
                    yield "data: $ Repository metadata updated [success]\n\n"

                except requests.exceptions.RequestException as e:
                    yield f"data: $ Error fetching repository data: {str(e)[:100]}\n\n"
                    yield "data: DONE\n\n"
                    return

                # Fetch issues and pull requests
                yield "data: $ Fetching issues and pull requests...\n\n"
                try:
                    issues_fetched = 0
                    prs_fetched = 0
                    page = 1

                    # Fetch issues (both issues and PRs)
                    while True:
                        issues_url = f"{api_url}/issues"
                        response = requests.get(
                            issues_url,
                            params={"state": "all", "per_page": 100, "page": page},
                            headers={
                                "Authorization": f"token {settings.GITHUB_TOKEN}",
                                "Accept": "application/vnd.github.v3+json",
                            },
                            timeout=10,
                        )

                        if response.status_code != 200:
                            yield f"data: $ Warning: Failed to fetch issues (page {page})\n\n"
                            break

                        issues = response.json()
                        if not issues:
                            break

                        for issue_data in issues:
                            try:
                                # Determine if it's a PR or issue
                                is_pr = "pull_request" in issue_data
                                issue_type = "pull_request" if is_pr else "issue"

                                # Check for dollar tag in labels
                                has_dollar_tag = any(
                                    "$" in label.get("name", "") for label in issue_data.get("labels", [])
                                )

                                # Create or update the issue
                                issue, created = GitHubIssue.objects.update_or_create(
                                    repo=repo,
                                    issue_id=issue_data["id"],
                                    defaults={
                                        "number": issue_data["number"],
                                        "title": issue_data.get("title", ""),
                                        "state": issue_data.get("state", ""),
                                        "type": issue_type,
                                        "url": issue_data.get("html_url", ""),
                                        "created_at": (
                                            parse_datetime(issue_data.get("created_at"))
                                            if issue_data.get("created_at")
                                            else None
                                        ),
                                        "updated_at": (
                                            parse_datetime(issue_data.get("updated_at"))
                                            if issue_data.get("updated_at")
                                            else None
                                        ),
                                        "closed_at": (
                                            parse_datetime(issue_data.get("closed_at"))
                                            if issue_data.get("closed_at")
                                            else None
                                        ),
                                        "has_dollar_tag": has_dollar_tag,
                                    },
                                )

                                if is_pr:
                                    prs_fetched += 1
                                else:
                                    issues_fetched += 1

                            except Exception as e:
                                yield f"data: $ Error processing issue #{issue_data.get('number', 'unknown')}: {str(e)[:50]}\n\n"

                        yield f"data: $ Processed page {page}: {len(issues)} items\n\n"
                        page += 1

                        # Limit to 10 pages to avoid excessive API calls
                        if page > 10:
                            yield "data: $ Reached page limit (10 pages)\n\n"
                            break

                        time.sleep(0.5)  # Avoid hitting rate limits

                    yield f"data: $ Issues fetched: {issues_fetched}, Pull requests fetched: {prs_fetched}\n\n"

                except Exception as e:
                    yield f"data: $ Error fetching issues: {str(e)[:100]}\n\n"

                # Final summary
                yield "data: $ \n\n"
                yield "data: $ ========================================\n\n"
                yield "data: $ Update Summary:\n\n"
                yield f"data: $ - Repository: {repo.name}\n\n"
                yield f"data: $ - Stars: {repo.stars}\n\n"
                yield f"data: $ - Forks: {repo.forks}\n\n"
                yield f"data: $ - Issues: {issues_fetched}\n\n"
                yield f"data: $ - Pull Requests: {prs_fetched}\n\n"
                yield "data: $ ========================================\n\n"
                yield "data: $ \n\n"
                yield "data: $ Update completed successfully!\n\n"
                yield "data: DONE\n\n"

            except Exception as e:
                logger.error(f"Error in event_stream: {str(e)}")
                yield f"data: $ Unexpected error: {str(e)[:100]}\n\n"
                yield "data: DONE\n\n"

        return StreamingHttpResponse(event_stream(), content_type="text/event-stream")

    except Exception as e:
        logger.error(f"Error in update_repo_data_stream: {str(e)}")

        def error_stream():
            yield f"data: $ Error: {str(e)[:100]}\n\n"
            yield "data: DONE\n\n"

        return StreamingHttpResponse(error_stream(), content_type="text/event-stream")
