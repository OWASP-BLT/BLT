import argparse
import json
import logging
import os
import re
import subprocess
import tracemalloc
import urllib
from datetime import datetime, timedelta
from urllib.parse import urlparse

import psutil
import pytz
import redis
import requests
import requests.exceptions
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from bs4 import BeautifulSoup
from dj_rest_auth.registration.views import SocialAccountDisconnectView as BaseSocialAccountDisconnectView
from dj_rest_auth.registration.views import SocialConnectView, SocialLoginView
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import FieldError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command, get_commands, load_command_class
from django.db import connection, models
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.views.generic import ListView, TemplateView, View

from website.models import (
    IP,
    Activity,
    Badge,
    DailyStats,
    Domain,
    ForumCategory,
    ForumComment,
    ForumPost,
    ForumVote,
    Hunt,
    InviteFriend,
    Issue,
    ManagementCommandLog,
    Organization,
    Points,
    PRAnalysisReport,
    Project,
    Repo,
    SlackBotActivity,
    Tag,
    User,
    UserBadge,
    UserProfile,
    Wallet,
)
from website.utils import (
    analyze_pr_content,
    fetch_github_data,
    rebuild_safe_url,
    safe_redirect_allowed,
    save_analysis_report,
)

# from website.bot import conversation_chain, is_api_key_valid, load_vector_store

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------------
# 1) Helper function to measure memory usage by module using tracemalloc
# ----------------------------------------------------------------------------------


def memory_usage_by_module(limit=1000):
    """
    Returns a list of (filename, size_in_bytes) for the top
    `limit` files by allocated memory, using tracemalloc.
    """
    # tracemalloc.start()
    try:
        snapshot = tracemalloc.take_snapshot()
    except Exception as e:
        print("Error taking memory snapshot: ", e)
        return []
    print("Memory snapshot taken. and it is: ", snapshot)

    stats = snapshot.statistics("traceback")
    for stat in stats[:10]:
        print(stat.traceback.format())
        print(f"Memory: {stat.size / 1024:.2f} KB")

    # Group memory usage by filename
    stats = snapshot.statistics("filename")
    module_usage = {}

    for stat in stats:
        print("stat is: ", stat)
        if stat.traceback:
            filename = stat.traceback[0].filename
            # Accumulate memory usage
            module_usage[filename] = module_usage.get(filename, 0) + stat.size

    # Sort by highest usage
    sorted_by_usage = sorted(module_usage.items(), key=lambda x: x[1], reverse=True)[:limit]

    tracemalloc.stop()
    return sorted_by_usage


# ----------------------------------------------------------------------------------
# 2) Example: Calculate your service/application status
# ----------------------------------------------------------------------------------

DAILY_REQUEST_LIMIT = 10
vector_store = None


def status_page(request):
    """
    Status check function with configurable components.
    Enable/disable specific checks using the CONFIG constants.
    """
    # Configuration flags
    CHECK_BITCOIN = False
    CHECK_SENDGRID = True
    CHECK_GITHUB = True
    CHECK_OPENAI = True
    CHECK_MEMORY = True
    CHECK_DATABASE = True
    CHECK_REDIS = True
    CHECK_SLACK_BOT = True
    CACHE_TIMEOUT = 60

    status_data = cache.get("service_status")

    if not status_data:
        status_data = {
            "bitcoin": None if not CHECK_BITCOIN else False,
            "bitcoin_block": None,
            "sendgrid": None if not CHECK_SENDGRID else False,
            "github": None if not CHECK_GITHUB else False,
            "openai": None if not CHECK_OPENAI else False,
            "db_connection_count": None if not CHECK_DATABASE else 0,
            "db_max_connections": None if not CHECK_DATABASE else 0,
            "db_connection_usage": None if not CHECK_DATABASE else 0,
            "memory_profiling": {"current": 0, "peak": 0},
            "top_memory_consumers": [],
            "redis_stats": (
                {
                    "status": "Not configured",
                    "version": None,
                    "connected_clients": None,
                    "used_memory_human": None,
                }
                if not CHECK_REDIS
                else {}
            ),
            "slack_bot": {},
            "management_commands": [],
            "available_commands": [],
        }

        if CHECK_MEMORY:
            status_data.update(
                {
                    "memory_info": psutil.virtual_memory()._asdict(),
                    "top_memory_consumers": [],
                    "memory_profiling": {},
                    "memory_by_module": [],
                }
            )

        # Get management command logs
        command_logs = (
            ManagementCommandLog.objects.values("command_name")
            .distinct()
            .annotate(
                last_run=models.Max("last_run"),
                last_success=models.ExpressionWrapper(models.Q(success=True), output_field=models.BooleanField()),
                run_count=models.Count("id"),
            )
            .order_by("command_name")
        )

        status_data["management_commands"] = list(command_logs)

        # Get list of available management commands
        available_commands = []
        for name, app_name in get_commands().items():
            # Only include commands from the website app
            if app_name == "website":
                command_class = load_command_class(app_name, name)
                command_info = {
                    "name": name,
                    "help_text": getattr(command_class, "help", "").split("\n")[0],
                }

                # Get command logs if they exist
                log = ManagementCommandLog.objects.filter(command_name=name).first()
                if log:
                    command_info.update(
                        {
                            "last_run": log.last_run,
                            "last_success": log.success,
                            "run_count": log.run_count,
                        }
                    )

                available_commands.append(command_info)

        commands = sorted(available_commands, key=lambda x: x["name"])
        status_data["available_commands"] = commands

        # Bitcoin RPC check
        if CHECK_BITCOIN:
            bitcoin_rpc_user = os.getenv("BITCOIN_RPC_USER")
            bitcoin_rpc_password = os.getenv("BITCOIN_RPC_PASSWORD")
            bitcoin_rpc_host = os.getenv("BITCOIN_RPC_HOST", "127.0.0.1")
            bitcoin_rpc_port = os.getenv("BITCOIN_RPC_PORT", "8332")

            try:
                print("Checking Bitcoin RPC...")
                response = requests.post(
                    f"http://{bitcoin_rpc_host}:{bitcoin_rpc_port}",
                    json={
                        "jsonrpc": "1.0",
                        "id": "curltest",
                        "method": "getblockchaininfo",
                        "params": [],
                    },
                    auth=(bitcoin_rpc_user, bitcoin_rpc_password),
                    timeout=5,
                )
                if response.status_code == 200:
                    status_data["bitcoin"] = True
                    status_data["bitcoin_block"] = response.json().get("result", {}).get("blocks")
            except requests.exceptions.RequestException as e:
                print(f"Bitcoin RPC Error: {e}")

        # SendGrid API check
        if CHECK_SENDGRID:
            sendgrid_api_key = os.getenv("SENDGRID_PASSWORD")
            if sendgrid_api_key:
                try:
                    print("Checking SendGrid API...")
                    response = requests.get(
                        "https://api.sendgrid.com/v3/user/account",
                        headers={"Authorization": f"Bearer {sendgrid_api_key}"},
                        timeout=5,
                    )
                    status_data["sendgrid"] = response.status_code == 200
                except requests.exceptions.RequestException as e:
                    print(f"SendGrid API Error: {e}")

        # GitHub API check
        if CHECK_GITHUB:
            github_token = os.getenv("GITHUB_TOKEN")
            if github_token:
                try:
                    print("Checking GitHub API...")
                    # Check basic API access
                    response = requests.get(
                        "https://api.github.com/user/repos",
                        headers={"Authorization": f"token {github_token}"},
                        timeout=5,
                    )
                    status_data["github"] = response.status_code == 200

                    # Get rate limit information
                    rate_limit_response = requests.get(
                        "https://api.github.com/rate_limit",
                        headers={"Authorization": f"token {github_token}"},
                        timeout=5,
                    )

                    if rate_limit_response.status_code == 200:
                        rate_limit_data = rate_limit_response.json()
                        status_data["github_rate_limit"] = {
                            "core": rate_limit_data.get("resources", {}).get("core", {}),
                            "search": rate_limit_data.get("resources", {}).get("search", {}),
                            "graphql": rate_limit_data.get("resources", {}).get("graphql", {}),
                            "integration_manifest": rate_limit_data.get("resources", {}).get(
                                "integration_manifest", {}
                            ),
                            "code_scanning_upload": rate_limit_data.get("resources", {}).get(
                                "code_scanning_upload", {}
                            ),
                        }

                        # Add recent API calls history from cache if available
                        github_api_history = cache.get("github_api_history", [])
                        status_data["github_api_history"] = github_api_history

                        # Add current rate limit to history
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        core_rate_limit = rate_limit_data.get("resources", {}).get("core", {})

                        if core_rate_limit:
                            new_entry = {
                                "timestamp": current_time,
                                "remaining": core_rate_limit.get("remaining", 0),
                                "limit": core_rate_limit.get("limit", 0),
                                "used": core_rate_limit.get("used", 0),
                                "reset": core_rate_limit.get("reset", 0),
                            }

                            # Add to history and keep last 50 entries
                            github_api_history.append(new_entry)
                            if len(github_api_history) > 50:
                                github_api_history = github_api_history[-50:]

                            # Update cache
                            cache.set("github_api_history", github_api_history, 86400)  # Cache for 24 hours
                    else:
                        status_data["github_rate_limit"] = None
                except requests.exceptions.RequestException as e:
                    print(f"GitHub API Error: {e}")
                    status_data["github_rate_limit"] = None

        # OpenAI API check
        if CHECK_OPENAI:
            openai_api_key = os.getenv("OPENAI_API_KEY", "sk-proj-1234567890")
            if openai_api_key:
                try:
                    print("Checking OpenAI API...")
                    response = requests.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {openai_api_key}"},
                        timeout=5,
                    )
                    status_data["openai"] = response.status_code == 200
                except requests.exceptions.RequestException as e:
                    print(f"OpenAI API Error: {e}")

        # Memory usage checks
        if CHECK_MEMORY:
            print("Getting memory usage information...")
            tracemalloc.start()

            # Get top memory consumers
            for proc in psutil.process_iter(["pid", "name", "memory_info"]):
                try:
                    proc_info = proc.info
                    proc_info["memory_info"] = proc_info["memory_info"]._asdict()
                    status_data["top_memory_consumers"].append(proc_info)
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                ):
                    pass

            status_data["top_memory_consumers"] = sorted(
                status_data["top_memory_consumers"],
                key=lambda x: x["memory_info"]["rss"],
                reverse=True,
            )[:5]

            # Memory profiling info
            current, peak = tracemalloc.get_traced_memory()
            status_data["memory_profiling"]["current"] = current
            status_data["memory_profiling"]["peak"] = peak
            tracemalloc.stop()

        # Database connection check
        if CHECK_DATABASE:
            print("Getting database connection count...")
            if settings.DATABASES.get("default", {}).get("ENGINE") == "django.db.backends.postgresql":
                try:
                    with connection.cursor() as cursor:
                        # Get current connection count
                        cursor.execute("SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'")
                        status_data["db_connection_count"] = cursor.fetchone()[0]

                        # Get max connections
                        cursor.execute("SHOW max_connections")
                        status_data["db_max_connections"] = int(cursor.fetchone()[0])

                        # Calculate connection usage percentage
                        if status_data["db_max_connections"] > 0:
                            status_data["db_connection_usage"] = (
                                status_data["db_connection_count"] / status_data["db_max_connections"]
                            ) * 100
                except Exception as e:
                    logger.error(f"Error getting database connection info: {str(e)}")

        # Redis stats
        if CHECK_REDIS:
            print("Getting Redis stats...")
            redis_url = os.environ.get("REDISCLOUD_URL")

            if redis_url:
                try:
                    # Parse Redis URL
                    parsed_url = urlparse(redis_url)
                    redis_host = parsed_url.hostname or "localhost"
                    redis_port = parsed_url.port or 6379
                    redis_password = parsed_url.password
                    redis_db = 0  # Default database

                    # Create Redis client
                    redis_client = redis.Redis(
                        host=redis_host,
                        port=redis_port,
                        password=redis_password,
                        db=redis_db,
                        socket_timeout=2.0,  # 2 second timeout
                    )

                    # Test connection and get info
                    info = redis_client.info()
                    status_data["redis_stats"] = {
                        "status": "Connected",
                        "version": info.get("redis_version"),
                        "connected_clients": info.get("connected_clients"),
                        "used_memory_human": info.get("used_memory_human"),
                        "uptime_days": info.get("uptime_in_days"),
                    }
                except (redis.ConnectionError, redis.TimeoutError) as e:
                    status_data["redis_stats"] = {
                        "status": "Connection failed",
                        "error": str(e),
                    }
                except Exception as e:
                    status_data["redis_stats"] = {
                        "status": "Error",
                        "error": str(e),
                    }
            else:
                status_data["redis_stats"] = {
                    "status": "Not configured",
                    "error": "REDISCLOUD_URL not set",
                }

        # Slack bot activity metrics
        if CHECK_SLACK_BOT:
            last_24h = timezone.now() - timedelta(hours=24)

            # Get last activity
            last_activity = SlackBotActivity.objects.order_by("-created").first()

            # Get bot activity metrics
            bot_metrics = {
                "total_activities": SlackBotActivity.objects.count(),
                "last_24h_activities": SlackBotActivity.objects.filter(created__gte=last_24h).count(),
                "success_rate": (
                    SlackBotActivity.objects.filter(success=True).count() / SlackBotActivity.objects.count() * 100
                    if SlackBotActivity.objects.exists()
                    else 0
                ),
                "workspace_count": SlackBotActivity.objects.values("workspace_id").distinct().count(),
                "last_activity": last_activity.created if last_activity else None,
                "recent_activities": list(
                    SlackBotActivity.objects.filter(created__gte=last_24h)
                    .values("activity_type", "workspace_name", "created", "success")
                    .order_by("-created")[:5]
                ),
                "activity_types": {
                    activity_type: count
                    for activity_type, count in SlackBotActivity.objects.values("activity_type")
                    .annotate(count=Count("id"))
                    .values_list("activity_type", "count")
                },
            }

            status_data["slack_bot"] = bot_metrics

        # Get the date range for the last 30 days
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)

        # Get daily counts for team joins and commands
        team_joins = (
            SlackBotActivity.objects.filter(activity_type="team_join", created__gte=start_date, created__lte=end_date)
            .annotate(date=TruncDate("created"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        commands = (
            SlackBotActivity.objects.filter(activity_type="command", created__gte=start_date, created__lte=end_date)
            .annotate(date=TruncDate("created"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        # Convert querysets to lists for the template
        team_joins_data = list(team_joins)
        commands_data = list(commands)

        # Create a complete date range with zero counts for missing dates
        date_range = []
        current_date = start_date.date()
        while current_date <= end_date.date():
            date_range.append(current_date)
            current_date += timedelta(days=1)

        # Fill in missing dates with zero counts
        dates = [date.strftime("%Y-%m-%d") for date in date_range]
        team_joins_counts = [0] * len(date_range)
        commands_counts = [0] * len(date_range)

        # Map the actual data to the date range
        for i, date in enumerate(date_range):
            for join in team_joins_data:
                if join["date"] == date:
                    team_joins_counts[i] = join["count"]
            for cmd in commands_data:
                if cmd["date"] == date:
                    commands_counts[i] = cmd["count"]

        # Store the data in a format that can be safely serialized to JSON
        chart_data = {"dates": dates, "team_joins": team_joins_counts, "commands": commands_counts}

        # Prepare GitHub API history data for chart
        if "github_api_history" in status_data and status_data["github_api_history"]:
            # Convert the history data to JSON-serializable format
            for entry in status_data["github_api_history"]:
                # Ensure all values are JSON serializable
                for key, value in entry.items():
                    if not isinstance(value, (str, int, float, bool, type(None))):
                        entry[key] = str(value)

        status_data["chart_data"] = chart_data

        # Prepare the chart data for the template
        template_chart_data = {
            "dates": json.dumps(status_data["chart_data"]["dates"]),
            "team_joins": json.dumps(status_data["chart_data"]["team_joins"]),
            "commands": json.dumps(status_data["chart_data"]["commands"]),
        }

        # Serialize GitHub API history data for the template
        if "github_api_history" in status_data:
            status_data["github_api_history"] = json.dumps(status_data["github_api_history"])

        # Add template chart data to status_data
        status_data["template_chart_data"] = template_chart_data

        # Cache the combined status
        cache.set("service_status", status_data, CACHE_TIMEOUT)

        return render(
            request, "status_page.html", {"status": status_data, "chart_data": status_data["template_chart_data"]}
        )
    return render(request, "status_page.html", {"status": status_data})


def github_callback(request):
    ALLOWED_HOSTS = ["github.com"]
    params = urllib.parse.urlencode(request.GET)
    url = f"{settings.CALLBACK_URL_FOR_GITHUB}?{params}"
    return safe_redirect_allowed(url, ALLOWED_HOSTS)


def google_callback(request):
    ALLOWED_HOSTS = ["accounts.google.com"]
    params = urllib.parse.urlencode(request.GET)
    url = f"{settings.CALLBACK_URL_FOR_GOOGLE}?{params}"
    return safe_redirect_allowed(url, ALLOWED_HOSTS)


def facebook_callback(request):
    ALLOWED_HOSTS = ["www.facebook.com"]
    params = urllib.parse.urlencode(request.GET)
    url = f"{settings.CALLBACK_URL_FOR_FACEBOOK}?{params}"
    return safe_redirect_allowed(url, ALLOWED_HOSTS)


def find_key(request, token):
    if token == os.environ.get("ACME_TOKEN"):
        return HttpResponse(os.environ.get("ACME_KEY"))
    for k, v in list(os.environ.items()):
        if v == token and k.startswith("ACME_TOKEN_"):
            n = k.replace("ACME_TOKEN_", "")
            return HttpResponse(os.environ.get("ACME_KEY_%s" % n))
    raise Http404("Token or key does not exist")


def search(request, template="search.html"):
    query = request.GET.get("query", "").strip()
    stype = request.GET.get("type", "").strip()
    context = {}

    if query:
        # Search across multiple models
        organizations = Organization.objects.filter(name__icontains=query)
        issues = Issue.objects.filter(Q(description__icontains=query), hunt=None).exclude(
            Q(is_hidden=True) & ~Q(user_id=request.user.id)
        )
        domains = Domain.objects.filter(Q(url__icontains=query), hunt=None)[0:20]
        users = User.objects.filter(username__icontains=query).exclude(is_superuser=True).order_by("-points")[0:20]
        projects = Project.objects.filter(Q(name__icontains=query) | Q(description__icontains=query))
        repos = Repo.objects.filter(Q(name__icontains=query) | Q(description__icontains=query))

        context = {
            "request": request,
            "query": query,
            "type": stype,
            "organizations": organizations,
            "domains": domains,
            "users": users,
            "issues": issues,
            "projects": projects,
            "repos": repos,
        }

        # Get badges for each user
        for user in users:
            user.badges = UserBadge.objects.filter(user=user)
            # Ensure user has a username for profile URL
            user.username = user.username

        # Get domain URLs for organizations
        for org in organizations:
            d = Domain.objects.filter(organization=org).first()
            if d:
                org.absolute_url = d.get_absolute_url()

    elif stype == "issues":
        context = {
            "request": request,
            "query": query,
            "type": stype,
            "issues": Issue.objects.filter(Q(description__icontains=query), hunt=None).exclude(
                Q(is_hidden=True) & ~Q(user_id=request.user.id)
            )[0:20],
        }
    elif stype == "domains":
        context = {
            "request": request,
            "query": query,
            "type": stype,
            "domains": Domain.objects.filter(Q(url__icontains=query), hunt=None)[0:20],
        }
    elif stype == "users":
        users = (
            UserProfile.objects.filter(Q(user__username__icontains=query))
            .annotate(total_score=Sum("user__points__score"))
            .order_by("-total_score")[0:20]
        )
        for userprofile in users:
            userprofile.badges = UserBadge.objects.filter(user=userprofile.user)
        context = {
            "request": request,
            "query": query,
            "type": stype,
            "users": users,
        }
    elif stype == "labels":
        context = {
            "query": query,
            "type": stype,
            "issues": Issue.objects.filter(Q(label__icontains=query), hunt=None).exclude(
                Q(is_hidden=True) & ~Q(user_id=request.user.id)
            )[0:20],
        }
    elif stype == "organizations":
        organizations = Organization.objects.filter(name__icontains=query)

        for org in organizations:
            d = Domain.objects.filter(organization=org).first()
            if d:
                org.absolute_url = d.get_absolute_url()
        context = {
            "query": query,
            "type": stype,
            "organizations": Organization.objects.filter(name__icontains=query),
        }
    elif stype == "projects":
        context = {
            "query": query,
            "type": stype,
            "projects": Project.objects.filter(Q(name__icontains=query) | Q(description__icontains=query)),
        }
    elif stype == "repos":
        context = {
            "query": query,
            "type": stype,
            "repos": Repo.objects.filter(Q(name__icontains=query) | Q(description__icontains=query)),
        }
    elif stype == "tags":
        tags = Tag.objects.filter(name__icontains=query)
        matching_organizations = Organization.objects.filter(tags__in=tags).distinct()
        matching_domains = Domain.objects.filter(tags__in=tags).distinct()
        matching_issues = Issue.objects.filter(tags__in=tags).distinct()
        matching_user_profiles = UserProfile.objects.filter(tags__in=tags).distinct()
        matching_repos = Repo.objects.filter(tags__in=tags).distinct()
        for org in matching_organizations:
            d = Domain.objects.filter(organization=org).first()
            if d:
                org.absolute_url = d.get_absolute_url()
        context = {
            "query": query,
            "type": stype,
            "tags": tags,
            "matching_organizations": matching_organizations,
            "matching_domains": matching_domains,
            "matching_issues": matching_issues,
            "matching_user_profiles": matching_user_profiles,
            "matching_repos": matching_repos,
        }
    elif stype == "languages":
        context = {
            "query": query,
            "type": stype,
            "repos": Repo.objects.filter(primary_language__icontains=query),
        }
    if request.user.is_authenticated:
        context["wallet"] = Wallet.objects.get(user=request.user)
    return render(request, template, context)


# @api_view(["POST"])
# def chatbot_conversation(request):
#     try:
#         today = datetime.now(timezone.utc).date()
#         rate_limit_key = f"global_daily_requests_{today}"
#         request_count = cache.get(rate_limit_key, 0)

#         if request_count >= DAILY_REQUEST_LIMIT:
#             return Response(
#                 {"error": "Daily request limit exceeded."},
#                 status=status.HTTP_429_TOO_MANY_REQUESTS,
#             )

#         question = request.data.get("question", "")
#         if not question:
#             return Response({"error": "Invalid question"}, status=status.HTTP_400_BAD_REQUEST)
#         check_api = is_api_key_valid(os.getenv("OPENAI_API_KEY"))
#         if not check_api:
#             ChatBotLog.objects.create(question=question, answer="Error: Invalid API Key")
#             return Response({"error": "Invalid API Key"}, status=status.HTTP_400_BAD_REQUEST)

#         if not question or not isinstance(question, str):
#             ChatBotLog.objects.create(question=question, answer="Error: Invalid question")
#             return Response({"error": "Invalid question"}, status=status.HTTP_400_BAD_REQUEST)

#         global vector_store
#         if not vector_store:
#             try:
#                 vector_store = load_vector_store()
#             except FileNotFoundError as e:
#                 ChatBotLog.objects.create(
#                     question=question, answer="Error: Vector store not found {e}"
#                 )
#                 return Response(
#                     {"error": "Vector store not found"},
#                     status=status.HTTP_400_BAD_REQUEST,
#                 )
#             except Exception as e:
#                 ChatBotLog.objects.create(question=question, answer=f"Error: {str(e)}")
#                 return Response(
#                     {"error": "Error loading vector store"},
#                     status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 )
#             finally:
#                 if not vector_store:
#                     ChatBotLog.objects.create(
#                         question=question, answer="Error: Vector store not loaded"
#                     )
#                     return Response(
#                         {"error": "Vector store not loaded"},
#                         status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                     )

#         if question.lower() == "exit":
#             if "buffer" in request.session:
#                 del request.session["buffer"]
#             return Response({"answer": "Conversation memory cleared."}, status=status.HTTP_200_OK)

#         crc, memory = conversation_chain(vector_store)
#         if "buffer" in request.session:
#             memory.buffer = request.session["buffer"]

#         try:
#             response = crc.invoke({"question": question})
#         except Exception as e:
#             ChatBotLog.objects.create(question=question, answer=f"Error: {str(e)}")
#             return Response(
#                 {"error": "An internal error has occurred."},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )
#         cache.set(rate_limit_key, request_count + 1, timeout=86400)  # Timeout set to one day
#         request.session["buffer"] = memory.buffer

#         ChatBotLog.objects.create(question=question, answer=response["answer"])
#         return Response({"answer": response["answer"]}, status=status.HTTP_200_OK)

#     except Exception as e:
#         ChatBotLog.objects.create(
#             question=request.data.get("question", ""), answer=f"Error: {str(e)}"
#         )
#         return Response(
#             {"error": "An internal error has occurred."},
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#         )


@login_required
def vote_forum_post(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            post_id = data.get("post_id")
            up_vote = data.get("up_vote", False)
            down_vote = data.get("down_vote", False)

            post = ForumPost.objects.get(id=post_id)
            vote, created = ForumVote.objects.get_or_create(
                post=post, user=request.user, defaults={"up_vote": up_vote, "down_vote": down_vote}
            )

            if not created:
                vote.up_vote = up_vote
                vote.down_vote = down_vote
                vote.save()

            # Update vote counts
            post.up_votes = ForumVote.objects.filter(post=post, up_vote=True).count()
            post.down_votes = ForumVote.objects.filter(post=post, down_vote=True).count()
            post.save()

            return JsonResponse({"success": True, "up_vote": post.up_votes, "down_vote": post.down_votes})
        except ForumPost.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Post not found"})
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON data"})
        except Exception:
            return JsonResponse({"status": "error", "message": "Server error occurred"})

    return JsonResponse({"status": "error", "message": "Invalid request method"})


@login_required
def set_vote_status(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            post_id = data.get("id")
            vote = ForumVote.objects.filter(post_id=post_id, user=request.user).first()

            return JsonResponse(
                {"up_vote": vote.up_vote if vote else False, "down_vote": vote.down_vote if vote else False}
            )
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON data"})
        except Exception:
            return JsonResponse({"status": "error", "message": "Server error occurred"})

    return JsonResponse({"status": "error", "message": "Invalid request method"})


@login_required
def add_forum_post(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            title = data.get("title")
            category = data.get("category")
            description = data.get("description")

            if not all([title, category, description]):
                return JsonResponse({"status": "error", "message": "Missing required fields"})

            post = ForumPost.objects.create(
                user=request.user, title=title, category_id=category, description=description
            )

            return JsonResponse({"status": "success", "post_id": post.id})
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON data"})
        except Exception:
            return JsonResponse({"status": "error", "message": "Server error occurred"})

    return JsonResponse({"status": "error", "message": "Invalid request method"})


@login_required
def add_forum_comment(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            post_id = data.get("post_id")
            content = data.get("content")

            if not all([post_id, content]):
                return JsonResponse({"status": "error", "message": "Missing required fields"})

            post = ForumPost.objects.get(id=post_id)
            comment = ForumComment.objects.create(post=post, user=request.user, content=content)

            return JsonResponse({"status": "success", "comment_id": comment.id})
        except ForumPost.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Post not found"})
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON data"})
        except Exception:
            return JsonResponse({"status": "error", "message": "Server error occurred"})

    return JsonResponse({"status": "error", "message": "Invalid request method"})


def view_forum(request):
    categories = ForumCategory.objects.all()
    selected_category = request.GET.get("category")

    posts = ForumPost.objects.select_related("user", "category").prefetch_related("comments").all()

    if selected_category:
        posts = posts.filter(category_id=selected_category)

    return render(
        request, "forum.html", {"categories": categories, "posts": posts, "selected_category": selected_category}
    )


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        return self.request.build_absolute_uri(reverse("google_callback"))


class GithubLogin(SocialLoginView):
    adapter_class = GitHubOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        return self.request.build_absolute_uri(reverse("github_callback"))


class FacebookConnect(SocialConnectView):
    adapter_class = FacebookOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        return self.request.build_absolute_uri(reverse("facebook_callback"))


class GithubConnect(SocialConnectView):
    adapter_class = GitHubOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        return self.request.build_absolute_uri(reverse("github_callback"))


class GoogleConnect(SocialConnectView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        return self.request.build_absolute_uri(reverse("google_callback"))


class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        return self.request.build_absolute_uri(reverse("facebook_callback"))


class UploadCreate(View):
    template_name = "home.html"

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(UploadCreate, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = request.FILES.get("image")
        result = default_storage.save("uploads/" + self.kwargs["hash"] + ".png", ContentFile(data.read()))
        return JsonResponse({"status": result})


class StatsDetailView(TemplateView):
    template_name = "stats.html"

    def get_historical_counts(self, model, start_date=None):
        date_field_map = {
            "Issue": "created",
            "UserProfile": "created",
            "Comment": "created_date",
            "Hunt": "created",
            "Domain": "created",
            "Organization": "created",
            "Project": "created",
            "Contribution": "created",
            "TimeLog": "created",
            "ActivityLog": "created",
            "DailyStatusReport": "created",
            "Suggestion": "created",
            "SuggestionVotes": "created",
            "Bid": "created",
            "Monitor": "created",
            "Payment": "created",
            "Transaction": "created",
            "InviteFriend": "created",
            "Points": "created",
            "Winner": "created",
            "Wallet": "created",
            "BaconToken": "date_awarded",
            "IP": "created",
            "ChatBotLog": "created",
        }

        date_field = date_field_map.get(model.__name__, "created")
        dates = []
        counts = []

        try:
            queryset = model.objects.all()
            if start_date:
                filter_kwargs = {f"{date_field}__gte": start_date}
                queryset = queryset.filter(**filter_kwargs)

            date_counts = (
                queryset.annotate(date=TruncDate(date_field))
                .values("date")
                .annotate(count=Count("id"))
                .order_by("date")
            )
            for entry in date_counts:
                dates.append(entry["date"].strftime("%Y-%m-%d"))
                counts.append(entry["count"])
        except FieldError:
            return [], []

        return dates, counts

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        # Get period from request, default to 30 days
        period = self.request.GET.get("period", "30")

        # Calculate start date based on period
        today = timezone.now()
        if period == "ytd":
            start_date = today.replace(month=1, day=1)
        else:
            try:
                days = int(period)
                start_date = today - timedelta(days=days)
            except ValueError:
                start_date = today - timedelta(days=30)

        stats_data = []
        known_icons = {
            "Issue": "fas fa-bug",
            "User": "fas fa-users",
            "Hunt": "fas fa-crosshairs",
            "Domain": "fas fa-globe",
            "ExtensionUser": "fas fa-puzzle-piece",
            "Subscription": "fas fa-envelope",
            "Organization": "fas fa-building",
            "HuntPrize": "fas fa-gift",
            "IssueScreenshot": "fas fa-camera",
            "Winner": "fas fa-trophy",
            "Points": "fas fa-star",
            "InviteFriend": "fas fa-envelope-open",
            "UserProfile": "fas fa-id-badge",
            "IP": "fas fa-network-wired",
            "OrganizationAdmin": "fas fa-user-tie",
            "Transaction": "fas fa-exchange-alt",
            "Payment": "fas fa-credit-card",
            "ContributorStats": "fas fa-chart-bar",
            "Monitor": "fas fa-desktop",
            "Bid": "fas fa-gavel",
            "ChatBotLog": "fas fa-robot",
            "Suggestion": "fas fa-lightbulb",
            "SuggestionVotes": "fas fa-thumbs-up",
            "Contributor": "fas fa-user-friends",
            "Project": "fas fa-project-diagram",
            "Contribution": "fas fa-hand-holding-heart",
            "BaconToken": "fas fa-coins",
        }

        for model in apps.get_models():
            if model._meta.abstract or model._meta.proxy:
                continue
            model_name = model.__name__

            try:
                dates, counts = self.get_historical_counts(model, start_date)
                trend = counts[-1] - counts[-2] if len(counts) >= 2 else 0

                # Get filtered count and total counts
                total_count = model.objects.count()
                filtered_count = counts[-1] if counts else 0

                stats_data.append(
                    {
                        "label": model_name,
                        "count": filtered_count,
                        "total_count": total_count,
                        "icon": known_icons.get(model_name, "fas fa-database"),
                        "history": json.dumps(counts),
                        "dates": json.dumps(dates),
                        "trend": trend,
                    }
                )
            except Exception:
                continue

        context.update(
            {
                "stats": sorted(stats_data, key=lambda x: x["count"], reverse=True),
                "period": period,
                "period_options": [
                    {"value": "1", "label": "1 Day"},
                    {"value": "7", "label": "1 Week"},
                    {"value": "30", "label": "1 Month"},
                    {"value": "90", "label": "3 Months"},
                    {"value": "ytd", "label": "Year to Date"},
                    {"value": "365", "label": "1 Year"},
                    {"value": "1825", "label": "5 Years"},
                ],
            }
        )
        return context


def view_suggestions(request):
    category_id = request.GET.get("category")
    status = request.GET.get("status")
    sort = request.GET.get("sort", "newest")

    suggestions = ForumPost.objects.all()

    # Apply filters
    if category_id:
        suggestions = suggestions.filter(category_id=category_id)
    if status:
        suggestions = suggestions.filter(status=status)

    # Apply sorting
    if sort == "oldest":
        suggestions = suggestions.order_by("created")
    elif sort == "most_votes":
        suggestions = suggestions.order_by("-up_votes")
    elif sort == "most_comments":
        suggestions = suggestions.annotate(comment_count=Count("comments")).order_by("-comment_count")
    else:  # newest
        suggestions = suggestions.order_by("-created")

    categories = ForumCategory.objects.all()

    return render(
        request,
        "feature_suggestion.html",
        {
            "suggestions": suggestions,
            "categories": categories,
        },
    )


def sitemap(request):
    random_domain = Domain.objects.order_by("?").first()
    return render(request, "sitemap.html", {"random_domain": random_domain})


def badge_list(request):
    badges = Badge.objects.all()
    badges = Badge.objects.annotate(user_count=Count("userbadge")).order_by("-user_count")
    return render(request, "badges.html", {"badges": badges})


def features_view(request):
    return render(request, "features.html")


def sponsor_view(request):
    from bitcash.network import NetworkAPI

    def get_bch_balance(address):
        try:
            balance_satoshis = NetworkAPI.get_balance(address)
            balance_bch = balance_satoshis / 100000000  # Convert from satoshis to BCH
            return balance_bch
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    bch_address = "bitcoincash:qr5yccf7j4dpjekyz3vpawgaarl352n7yv5d5mtzzc"
    balance = get_bch_balance(bch_address)
    if balance is not None:
        print(f"Balance of {bch_address}: {balance} BCH")

    return render(request, "sponsor.html", context={"balance": balance})


def donate_view(request):
    return render(request, "donate.html")


@require_GET
def robots_txt(request):
    lines = [
        "User-Agent: *",
        "Allow: /",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def get_last_commit_date():
    try:
        return (
            subprocess.check_output(
                ["git", "log", "-1", "--format=%cd"],
                cwd=os.path.dirname(os.path.dirname(__file__)),
            )
            .decode("utf-8")
            .strip()
        )
    except FileNotFoundError:
        return "Not available"


def submit_roadmap_pr(request):
    if request.method == "POST":
        pr_link = request.POST.get("pr_link", "").strip()
        issue_link = request.POST.get("issue_link", "").strip()

        if not pr_link or not issue_link:
            return JsonResponse({"error": "Both PR and issue links are required."}, status=400)

        # Validate GitHub URLs
        if not (pr_link.startswith("https://github.com/") and issue_link.startswith("https://github.com/")):
            return JsonResponse({"error": "Invalid GitHub URLs. Both URLs must be from github.com"}, status=400)

        try:
            pr_parts = pr_link.split("/")
            issue_parts = issue_link.split("/")

            # Validate URL parts length
            if len(pr_parts) < 7 or len(issue_parts) < 7:
                return JsonResponse({"error": "Invalid GitHub URL format"}, status=400)

            # Extract owner and repo from PR URL
            owner, repo = pr_parts[3], pr_parts[4]

            # Extract PR and issue numbers
            pr_number = pr_parts[-1]
            issue_number = issue_parts[-1]

            # Validate that we have numeric IDs
            if not (pr_number.isdigit() and issue_number.isdigit()):
                return JsonResponse({"error": "Invalid PR or issue number format"}, status=400)

            pr_data = fetch_github_data(owner, repo, "pulls", pr_number)
            roadmap_data = fetch_github_data(owner, repo, "issues", issue_number)

            if "error" in pr_data or "error" in roadmap_data:
                return JsonResponse(
                    {"error": f"Failed to fetch PR or roadmap data: {pr_data.get('error', 'Unknown error')}"},
                    status=500,
                )

            analysis = analyze_pr_content(pr_data, roadmap_data)
            save_analysis_report(pr_link, issue_link, analysis)
            return JsonResponse({"message": "PR submitted successfully"})

        except (IndexError, ValueError) as e:
            return JsonResponse({"error": f"Invalid URL format: {str(e)}"}, status=400)
        except Exception as e:
            return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)

    return render(request, "submit_roadmap_pr.html")


def view_pr_analysis(request):
    reports = PRAnalysisReport.objects.all()
    return render(request, "view_pr_analysis.html", {"reports": reports})


def home(request):
    from django.db.models import Count, Sum
    from django.utils import timezone

    from website.models import ForumPost, GitHubIssue, Issue, Post, Repo, User, UserProfile

    # Get last commit date
    try:
        last_commit = get_last_commit_date()
    except Exception as e:
        print(f"Error getting last commit date: {e}")
        last_commit = ""

    # Get latest repositories and total count
    latest_repos = Repo.objects.order_by("-created")[:5]
    total_repos = Repo.objects.count()

    # Get recent forum posts
    recent_posts = ForumPost.objects.select_related("user", "category").order_by("-created")[:5]

    # Get top bug reporters for current month
    current_time = timezone.now()
    top_bug_reporters = (
        User.objects.filter(points__created__month=current_time.month, points__created__year=current_time.year)
        .annotate(bug_count=Count("points", filter=Q(points__score__gt=0)), total_score=Sum("points__score"))
        .order_by("-total_score")[:5]
    )

    # Get top PR contributors using the leaderboard method for BLT repo in current month only
    top_pr_contributors = (
        GitHubIssue.objects.filter(
            type="pull_request",
            is_merged=True,
            repo__name="BLT",  # Filter for BLT repo only
            contributor__isnull=False,  # Exclude None values
            merged_at__month=current_time.month,  # Current month only
            merged_at__year=current_time.year,  # Current year
        )
        .values("contributor__name", "contributor__avatar_url", "contributor__github_url")
        .annotate(total_prs=Count("id"))
        .order_by("-total_prs")[:5]
    )

    # Get top earners
    top_earners = UserProfile.objects.filter(winnings__gt=0).select_related("user").order_by("-winnings")[:5]

    # Get top referrals
    top_referrals = (
        InviteFriend.objects.filter(point_by_referral__gt=0)
        .annotate(signup_count=Count("recipients"), total_points=F("point_by_referral"))
        .select_related("sender", "sender__userprofile")
        .order_by("-point_by_referral")[:5]
    )

    # Get or Create InviteFriend object for logged in user
    referral_code = None
    if request.user.is_authenticated:
        invite_friend, created = InviteFriend.objects.get_or_create(sender=request.user)
        referral_code = invite_friend.referral_code

    # Get latest blog posts
    latest_blog_posts = Post.objects.order_by("-created_at")[:2]

    # Get latest bug reports
    latest_bugs = (
        Issue.objects.filter(hunt=None)
        .exclude(Q(is_hidden=True) & ~Q(user_id=request.user.id))
        .order_by("-created")[:2]
    )

    # Get repository star counts for the specific repositories shown on the homepage
    repo_stars = []
    repo_mappings = {
        "blt": "OWASP-BLT/BLT",
        "flutter": "OWASP-BLT/BLT-Flutter",
        "extension": "OWASP-BLT/BLT-Extension",
        "action": "OWASP-BLT/BLT-Action",
    }

    for key, repo_name in repo_mappings.items():
        try:
            # Try to find the repository by name
            repo_parts = repo_name.split("/")
            if len(repo_parts) > 1:
                repo = Repo.objects.filter(name__icontains=repo_parts[1]).first()
            else:
                repo = Repo.objects.filter(name__icontains=repo_name).first()

            if repo:
                repo_stars.append({"key": key, "stars": repo.stars})
        except Exception as e:
            print(f"Error getting star count for {repo_name}: {e}")

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

    return render(
        request,
        "home.html",
        {
            "last_commit": last_commit,
            "current_year": timezone.now().year,
            "current_time": current_time,  # Add current time for month display
            "latest_repos": latest_repos,
            "total_repos": total_repos,
            "recent_posts": recent_posts,
            "top_bug_reporters": top_bug_reporters,
            "top_pr_contributors": top_pr_contributors,
            "latest_blog_posts": latest_blog_posts,
            "top_earners": top_earners,
            "repo_stars": repo_stars,
            "top_referrals": top_referrals,
            "referral_code": referral_code,
            "debug_mode": settings.DEBUG,
            "system_stats": system_stats,
            "latest_bugs": latest_bugs,
        },
    )


def test_sentry(request):
    if request.user.is_superuser:
        1 / 0  # This will raise a ZeroDivisionError
    return HttpResponse("Test error sent to Sentry!")


def handler404(request, exception):
    return render(request, "404.html", {}, status=404)


def handler500(request, exception=None):
    return render(request, "500.html", {}, status=500)


def stats_dashboard(request):
    # Get the time period from request, default to 30 days
    period = request.GET.get("period", "30")

    # Define time periods in days
    period_map = {
        "1": 1,  # 1 day
        "7": 7,  # 1 week
        "30": 30,  # 1 month
        "90": 90,  # 3 months
        "ytd": "ytd",  # Year to date
        "365": 365,  # 1 year
        "1825": 1825,  # 5 years
    }

    # Validate the period parameter
    if period not in period_map:
        period = "30"

    days = period_map[period]

    # Calculate the date range
    end_date = timezone.now()
    if days == "ytd":
        start_date = end_date.replace(month=1, day=1)
    else:
        start_date = end_date - timedelta(days=days)

    # Try to get stats from cache with period-specific key
    cache_key = f"dashboard_stats_{period}"
    stats = cache.get(cache_key)

    if stats is None:
        # If not in cache, compute stats with optimized queries and date filtering
        users = User.objects.filter(date_joined__gte=start_date).aggregate(
            total=Count("id"), active=Count("id", filter=Q(is_active=True))
        )
        total_users = User.objects.count()

        issues = Issue.objects.filter(created__gte=start_date).aggregate(
            total=Count("id"), open=Count("id", filter=Q(status="open"))
        )
        total_issues = Issue.objects.count()

        domains = Domain.objects.filter(created__gte=start_date).aggregate(
            total=Count("id"), active=Count("id", filter=Q(is_active=True))
        )
        total_domains = Domain.objects.count()

        organizations = Organization.objects.filter(created__gte=start_date).aggregate(
            total=Count("id"), active=Count("id", filter=Q(is_active=True))
        )
        total_organizations = Organization.objects.count()

        hunts = Hunt.objects.filter(created__gte=start_date).aggregate(
            total=Count("id"), active=Count("id", filter=Q(is_published=True))
        )
        total_hunts = Hunt.objects.count()

        points = Points.objects.filter(created__gte=start_date).aggregate(total=Sum("score"))["total"] or 0
        total_points = Points.objects.aggregate(total=Sum("score"))["total"] or 0

        projects = Project.objects.filter(created__gte=start_date).count()
        total_projects = Project.objects.count()

        activities = Activity.objects.filter(timestamp__gte=start_date).count()
        total_activities = Activity.objects.count()

        recent_activities = (
            Activity.objects.filter(timestamp__gte=start_date)
            .order_by("-timestamp")
            .values("id", "title", "description", "timestamp")[:5]
        )

        # Combine all stats
        stats = {
            "users": {
                "total": users["total"],
                "active": users["active"],
                "total_all_time": total_users,
                "active_percentage": round((users["active"] / users["total"] * 100) if users["total"] > 0 else 0),
            },
            "issues": {
                "total": issues["total"],
                "open": issues["open"],
                "total_all_time": total_issues,
                "open_percentage": round((issues["open"] / issues["total"] * 100) if issues["total"] > 0 else 0),
                "fixed": Issue.objects.filter(created__gte=start_date, status="fixed").count(),
                "in_review": Issue.objects.filter(created__gte=start_date, status="in_review").count(),
                "invalid": Issue.objects.filter(created__gte=start_date, status="invalid").count(),
            },
            "domains": {
                "total": domains["total"],
                "active": domains["active"],
                "total_all_time": total_domains,
                "active_percentage": round((domains["active"] / domains["total"] * 100) if domains["total"] > 0 else 0),
            },
            "organizations": {
                "total": organizations["total"],
                "active": organizations["active"],
                "total_all_time": total_organizations,
                "active_percentage": round(
                    (organizations["active"] / organizations["total"] * 100) if organizations["total"] > 0 else 0
                ),
            },
            "hunts": {
                "total": hunts["total"],
                "active": hunts["active"],
                "total_all_time": total_hunts,
                "active_percentage": round((hunts["active"] / hunts["total"] * 100) if hunts["total"] > 0 else 0),
            },
            "points": {
                "total": points,
                "total_all_time": total_points,
                "percentage": round((points / total_points * 100) if total_points > 0 else 0),
            },
            "projects": {
                "total": projects,
                "total_all_time": total_projects,
                "percentage": round((projects / total_projects * 100) if total_projects > 0 else 0),
            },
            "activities": {
                "total": activities,
                "total_all_time": total_activities,
                "recent": list(recent_activities),
            },
        }

        # Get time series data for charts (last 12 months or the selected period)
        months_data = []
        if days == "ytd":
            months_to_fetch = end_date.month
        elif days > 365:
            months_to_fetch = min(12, days // 30)
        else:
            months_to_fetch = min(12, max(1, days // 30))

        # Generate time series data
        issues_time_series = []
        users_time_series = []

        for i in range(months_to_fetch):
            month_end = end_date - timedelta(days=i * 30)
            month_start = month_end - timedelta(days=30)

            month_issues = Issue.objects.filter(created__gte=month_start, created__lte=month_end).count()
            month_users = User.objects.filter(date_joined__gte=month_start, date_joined__lte=month_end).count()

            issues_time_series.insert(0, month_issues)
            users_time_series.insert(0, month_users)

        # Fill remaining months with zeros if we have less than 12 months
        while len(issues_time_series) < 12:
            issues_time_series.insert(0, 0)
            users_time_series.insert(0, 0)

        # Add time series data to the stats dictionary
        stats["issues_time_series"] = issues_time_series
        stats["users_time_series"] = users_time_series

        # Cache the results for 5 minutes
        cache.set(cache_key, stats, timeout=300)

    context = {
        "stats": stats,
        "period": period,
        "period_options": [
            {"value": "1", "label": "1 Day"},
            {"value": "7", "label": "1 Week"},
            {"value": "30", "label": "1 Month"},
            {"value": "90", "label": "3 Months"},
            {"value": "ytd", "label": "Year to Date"},
            {"value": "365", "label": "1 Year"},
            {"value": "1825", "label": "5 Years"},
        ],
        "issues_time_series": json.dumps(stats.get("issues_time_series", [])),
        "users_time_series": json.dumps(stats.get("users_time_series", [])),
    }

    return render(request, "stats_dashboard.html", context)


def sync_github_projects(request):
    if request.method == "POST":
        try:
            call_command("check_owasp_projects")
            messages.success(request, "Successfully synced OWASP GitHub projects.")
        except Exception as e:
            messages.error(request, f"Error syncing OWASP GitHub projects: {str(e)}")
    return redirect("stats_dashboard")


def check_owasp_compliance(request):
    """
    View to check OWASP project compliance with guidelines.
    Combines form and results in a single template.
    """
    if request.method == "POST":
        url = request.POST.get("url", "").strip()
        if not url:
            messages.error(request, "Please provide a valid URL")
            return redirect("check_owasp_compliance")

        # SSRF Fix: Validate and sanitize URL first
        try:
            safe_url = rebuild_safe_url(url)
            if not safe_url:
                messages.error(request, "Invalid or unsafe URL provided")
                return redirect("check_owasp_compliance")
        except ValueError as e:
            messages.error(request, f"Error processing URL: {str(e)}")
            return redirect("check_owasp_compliance")
        try:
            # Parse URL to determine if it's a GitHub repository
            parsed_url = urlparse(safe_url)
            is_github = "github.com" == parsed_url.hostname.lower()
            is_owasp_org = is_github and parsed_url.path.lower().startswith("/owasp/")

            # Fetch and analyze website content
            response = requests.get(safe_url, timeout=10, verify=True, allow_redirects=False)
            soup = BeautifulSoup(response.text.lower(), "html.parser")
            content = soup.get_text().lower()

            # Check for OWASP mentions and links
            has_owasp_mention = "owasp" in content
            has_project_link = any(
                "owasp.org/www-project-" in link.get("href", "").lower() for link in soup.find_all("a")
            )

            # Check for dates to determine if content is up-to-date
            date_patterns = [
                r"\b\d{4}-\d{2}-\d{2}\b",  # YYYY-MM-DD
                r"\b\d{2}/\d{2}/\d{4}\b",  # DD/MM/YYYY
                r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{1,2},? \d{4}\b",  # Month DD, YYYY
            ]
            has_dates = any(re.search(pattern, content, re.IGNORECASE) for pattern in date_patterns)

            # Check for potential paywall indicators
            paywall_indicators = [
                "premium",
                "subscription",
                "upgrade to",
                "paid version",
                "enterprise plan",
                "pro version",
            ]
            has_paywall_indicators = any(indicator in content for indicator in paywall_indicators)

            # Compile recommendations
            recommendations = []
            if not is_owasp_org:
                recommendations.append("Project should be hosted under the OWASP GitHub organization")
            if not has_owasp_mention:
                recommendations.append("Website should clearly state it is an OWASP project")
            if not has_project_link:
                recommendations.append("Website should link to the OWASP project page")
            if has_paywall_indicators:
                recommendations.append("Check if the project has features behind a paywall")

            context = {
                "url": safe_url,
                "github_compliance": {
                    "github_hosted": is_github,
                    "under_owasp_org": is_owasp_org,
                },
                "website_compliance": {
                    "has_owasp_mention": has_owasp_mention,
                    "has_project_link": has_project_link,
                    "has_dates": has_dates,
                },
                "vendor_neutrality": {
                    "possible_paywall": has_paywall_indicators,
                },
                "recommendations": recommendations,
                "overall_status": "compliant" if not recommendations else "needs_improvement",
            }

            return render(request, "check_owasp_compliance.html", context)

        except requests.RequestException as e:
            messages.error(request, f"Error accessing the URL: {str(e)}. Please check if the URL is accessible.")
        except Exception as e:
            messages.error(request, f"Error checking compliance: {str(e)}. Please try again.")

    return render(request, "check_owasp_compliance.html")


def management_commands(request):
    # Get list of available management commands
    available_commands = []

    # Get the date 30 days ago for stats
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)

    # Get sort parameter from request
    sort_param = request.GET.get("sort", "name")
    reverse = False

    # Check if sort parameter starts with '-' (descending order)
    if sort_param.startswith("-"):
        reverse = True
        sort_key = sort_param[1:]  # Remove the '-' prefix
    else:
        sort_key = sort_param

    # Validate sort key
    valid_sort_keys = ["name", "last_run", "status", "run_count", "activity"]
    if sort_key not in valid_sort_keys:
        sort_key = "name"
        sort_param = "name"

    for name, app_name in get_commands().items():
        # Only include commands from the website app and exclude initsuperuser
        if (
            app_name == "website"
            and name != "initsuperuser"
            and name != "generate_sample_data"
            and not name.startswith("run_")
        ):
            command_class = load_command_class(app_name, name)
            help_text = getattr(command_class, "help", "").split("\n")[0]
            command_info = {
                "name": name,
                "help_text": help_text,
            }

            # Get command arguments if they exist
            command_args = []
            if hasattr(command_class, "add_arguments"):
                # Create a parser to capture arguments
                from argparse import ArgumentParser

                parser = ArgumentParser()
                # Fix: Call add_arguments directly on the command instance
                command_class.add_arguments(parser)

                # Extract argument information
                for action in parser._actions:
                    if action.dest != "help":  # Skip the default help action
                        arg_info = {
                            "name": action.dest,
                            "flags": ", ".join(action.option_strings),
                            "help": action.help,
                            "required": action.required,
                            "default": action.default if action.default != argparse.SUPPRESS else None,
                            "type": action.type.__name__ if action.type else "str",
                        }
                        command_args.append(arg_info)

            command_info["arguments"] = command_args

            # Get command logs if they exist
            log = ManagementCommandLog.objects.filter(command_name=name).first()
            if log:
                command_info.update(
                    {
                        "last_run": log.last_run,
                        "last_success": log.success,
                        "run_count": log.run_count,
                    }
                )

            # Get stats data for the past 30 days if it exists
            stats_data = []

            # Create a dictionary to store values for each day in the 30-day period
            date_range = []
            date_values = {}

            # Generate all dates in the 30-day range
            for i in range(30):
                date = (timezone.now() - timezone.timedelta(days=29 - i)).date()
                date_range.append(date)
                date_values[date.isoformat()] = 0

            # Get actual stats data
            daily_stats = DailyStats.objects.filter(name=name, created__gte=thirty_days_ago).order_by("created")

            # Fill in the values we have
            max_value = 1  # Minimum value to avoid division by zero
            total_activity = 0  # Track total activity for sorting
            for stat in daily_stats:
                try:
                    value = int(stat.value)
                    date_key = stat.created.date().isoformat()
                    date_values[date_key] = value
                    total_activity += value
                    if value > max_value:
                        max_value = value
                except (ValueError, TypeError, KeyError):
                    pass

            # Convert to list format for the template
            for date in date_range:
                date_key = date.isoformat()
                stats_data.append(
                    {
                        "date": date_key,
                        "value": date_values.get(date_key, 0),
                        "height_percent": (date_values.get(date_key, 0) / max_value) * 100 if max_value > 0 else 0,
                    }
                )

            command_info["stats_data"] = stats_data
            command_info["max_value"] = max_value
            command_info["total_activity"] = total_activity
            available_commands.append(command_info)

    # Sort the commands based on the sort parameter
    def sort_commands(cmd):
        if sort_key == "name":
            return cmd["name"]
        elif sort_key == "last_run":
            return cmd.get("last_run", timezone.datetime.min.replace(tzinfo=pytz.UTC))
        elif sort_key == "status":
            # Sort by success status (True comes after False in ascending order)
            return cmd.get("last_success", False)
        elif sort_key == "run_count":
            return cmd.get("run_count", 0)
        elif sort_key == "activity":
            return cmd.get("total_activity", 0)
        else:
            return cmd["name"]

    commands = sorted(available_commands, key=sort_commands, reverse=reverse)

    return render(request, "management_commands.html", {"commands": commands, "sort": sort_param, "reverse": reverse})


def run_management_command(request):
    if request.method == "POST":
        # Check if user is superuser
        if not request.user.is_superuser:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": "Only superusers can run management commands."})
            messages.error(request, "Only superusers can run management commands.")
            return redirect("management_commands")

        command = request.POST.get("command")
        logging.info(f"Running command: {command}")

        try:
            # Only allow running commands from the website app and exclude initsuperuser
            app_name = get_commands().get(command)
            if app_name != "website" or command == "initsuperuser":
                msg = f"Command {command} is not allowed to run from the web interface"
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "error": msg})
                messages.error(request, msg)
                return redirect("management_commands")

            # Get or create the command log
            log_entry, created = ManagementCommandLog.objects.get_or_create(
                command_name=command, defaults={"run_count": 0, "success": False, "last_run": timezone.now()}
            )

            # Update the log entry
            log_entry.run_count += 1
            log_entry.last_run = timezone.now()
            log_entry.save()

            # Collect command arguments from POST data
            command_args = []
            command_kwargs = {}

            # Get the command class to check for arguments
            command_class = load_command_class(app_name, command)

            # Create a parser to capture arguments
            if hasattr(command_class, "add_arguments"):
                from argparse import ArgumentParser

                parser = ArgumentParser()
                # Fix: Call add_arguments directly on the command instance
                command_class.add_arguments(parser)

                # Extract argument information and collect values from POST
                for action in parser._actions:
                    if action.dest != "help":  # Skip the default help action
                        arg_name = action.dest
                        arg_value = request.POST.get(arg_name)

                        if arg_value:
                            # Convert to appropriate type if needed
                            if action.type:
                                try:
                                    if action.type == int:
                                        arg_value = int(arg_value)
                                    elif action.type == float:
                                        arg_value = float(arg_value)
                                    elif action.type == bool:
                                        arg_value = arg_value.lower() in ("true", "yes", "1")
                                except (ValueError, TypeError):
                                    warning_msg = (
                                        f"Could not convert argument '{arg_name}' to type "
                                        f"{action.type.__name__}. Using as string."
                                    )
                                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                                        return JsonResponse({"success": False, "error": warning_msg})
                                    messages.warning(request, warning_msg)

                            # Add to args or kwargs based on whether it's a positional or optional argument
                            if action.option_strings:  # It's an optional argument
                                command_kwargs[arg_name] = arg_value
                            else:  # It's a positional argument
                                command_args.append(arg_value)

            # Run the command with collected arguments
            try:
                # Capture command output
                import sys
                from io import StringIO

                # Redirect stdout to capture output
                old_stdout = sys.stdout
                sys.stdout = mystdout = StringIO()

                call_command(command, *command_args, **command_kwargs)

                # Get the output and restore stdout
                output = mystdout.getvalue()
                sys.stdout = old_stdout

                log_entry.success = True
                log_entry.save()

                # Record execution in DailyStats
                try:
                    # Get existing stats for today
                    today = timezone.now().date()
                    daily_stat, created = DailyStats.objects.get_or_create(
                        name=command,
                        created__date=today,
                        defaults={"value": "1", "created": timezone.now(), "modified": timezone.now()},
                    )

                    if not created:
                        # Increment the value
                        try:
                            current_value = int(daily_stat.value)
                            daily_stat.value = str(current_value + 1)
                            daily_stat.modified = timezone.now()
                            daily_stat.save()
                        except (ValueError, TypeError):
                            # If value is not an integer, set it to 1
                            daily_stat.value = "1"
                            daily_stat.modified = timezone.now()
                            daily_stat.save()
                except Exception as stats_error:
                    logging.error(f"Error updating DailyStats: {str(stats_error)}")

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"success": True, "output": output})

                messages.success(request, f"Command '{command}' executed successfully.")
            except Exception as e:
                log_entry.success = False
                log_entry.save()

                error_msg = f"Error executing command '{command}': {str(e)}"
                logging.error(error_msg)

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "error": error_msg})

                messages.error(request, error_msg)

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logging.error(error_msg)

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": error_msg})

            messages.error(request, error_msg)

    return redirect("management_commands")


def template_list(request):
    """View function to display templates with optimized pagination."""
    import os
    from concurrent.futures import ThreadPoolExecutor
    from datetime import datetime

    from django.core.cache import cache
    from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
    from django.db.models import Q, Sum
    from django.urls import URLPattern, URLResolver, get_resolver

    # Get request parameters with defaults
    search_query = request.GET.get("search", "").strip()
    filter_by = request.GET.get("filter", "all")
    sort = request.GET.get("sort", "name")
    direction = request.GET.get("dir", "asc")
    page = int(request.GET.get("page", 1))
    per_page = 20

    def extract_template_info(template_path):
        """Extract and cache template metadata."""
        template_name = os.path.basename(template_path)
        cache_key = f"template_info_{template_name}"
        template_info = cache.get(cache_key)

        if template_info is None:
            try:
                with open(template_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    template_info = {
                        "has_sidenav": '{% include "includes/sidenav.html" %}' in content,
                        "extends_base": '{% extends "base.html" %}' in content,
                        "has_style_tags": "<style" in content,
                    }
                cache.set(cache_key, template_info, 24 * 3600)  # Cache for 24 hours
            except IOError:
                template_info = {"has_sidenav": False, "extends_base": False, "has_style_tags": False}

        return template_info

    def check_template_url(template_name):
        resolver = get_resolver()
        template_base_name = template_name.replace(".html", "")

        for pattern in resolver.url_patterns:
            if isinstance(pattern, URLResolver):
                url = check_template_url_in_patterns(pattern.url_patterns, template_name)
                if url:
                    return url
            elif isinstance(pattern, URLPattern):
                url = check_pattern(pattern, template_name, template_base_name)
                if url:
                    return url
        return None

    def check_template_url_in_patterns(urlpatterns, template_name):
        template_base_name = template_name.replace(".html", "")
        for pattern in urlpatterns:
            if isinstance(pattern, URLResolver):
                url = check_template_url_in_patterns(pattern.url_patterns, template_name)
                if url:
                    return url
            elif isinstance(pattern, URLPattern):
                url = check_pattern(pattern, template_name, template_base_name)
                if url:
                    return url
        return None

    def check_pattern(pattern, template_name, template_base_name):
        pattern_path = str(pattern.pattern) if pattern.pattern else ""
        pattern_name = getattr(pattern, "name", "")

        if hasattr(pattern.callback, "view_class"):
            view_class = pattern.callback.view_class
            if hasattr(view_class, "template_name") and view_class.template_name in (template_name, template_base_name):
                return "/" + str(pattern.pattern).lstrip("^").rstrip("$")

        if any(
            [
                pattern_path == template_base_name,
                pattern_path and pattern_path.replace("-", "_") == template_base_name,
                pattern_name == template_base_name,
                pattern_name and pattern_name.replace("-", "_") == template_base_name,
            ]
        ):
            return "/" + str(pattern.pattern).lstrip("^").rstrip("$")

        return None

    def get_template_files(directory):
        """Get only template files without processing content"""
        cache_key = f"template_files_{directory}_{search_query}_{filter_by}"
        files = cache.get(cache_key)

        if files is None:
            files = []
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_file() and entry.name.endswith(".html"):
                        if search_query and search_query.lower() not in entry.name.lower():
                            continue
                        files.append(
                            {
                                "name": entry.name,
                                "path": entry.path,
                                "modified": datetime.fromtimestamp(entry.stat().st_mtime),
                            }
                        )

            # Sort files if needed
            files.sort(key=lambda x: (x.get(sort, ""), x["name"]), reverse=direction == "desc")
            cache.set(cache_key, files, 300)  # Cache for 5 minutes

        return files

    def process_template_batch(templates_batch):
        """Process only the templates needed for current page"""
        processed_templates = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}

            for template in templates_batch:
                future = executor.submit(extract_template_info, template["path"])
                futures[future] = template

            for future in futures:
                template_data = futures[future].copy()
                template_info = future.result()

                if filter_by != "all":
                    if (
                        filter_by == "with_sidenav"
                        and not template_info["has_sidenav"]
                        or filter_by == "with_base"
                        and not template_info["extends_base"]
                        or filter_by == "with_styles"
                        and not template_info["has_style_tags"]
                    ):
                        continue

                # Get view count from IP table with caching
                view_count_key = f"template_views_{template_data['name']}"
                view_count = cache.get(view_count_key)
                if view_count is None:
                    view_count = (
                        IP.objects.filter(
                            Q(path__endswith=f"/{template_data['name']}")
                            | Q(path__endswith=f"/templates/{template_data['name']}")
                        ).aggregate(total_views=Sum("count"))["total_views"]
                        or 0
                    )
                    cache.set(view_count_key, view_count, 3600)

                # Get template URL
                url_key = f"template_url_{template_data['name']}"
                template_url = cache.get(url_key)
                if template_url is None:
                    template_url = check_template_url(template_data["name"])
                    cache.set(url_key, template_url, 3600)

                template_data.update({"url": template_url, "views": view_count, **template_info})
                processed_templates.append(template_data)

        return processed_templates

    # Get all template files paths first (lightweight operation)
    template_dirs = []
    all_templates = []
    main_template_dir = os.path.join(settings.BASE_DIR, "website", "templates")

    if os.path.exists(main_template_dir):
        main_templates = get_template_files(main_template_dir)
        if main_templates:
            all_templates.extend([("Main Templates", t) for t in main_templates])

        # Get templates from subdirectories
        for subdir in os.listdir(main_template_dir):
            subdir_path = os.path.join(main_template_dir, subdir)
            if os.path.isdir(subdir_path) and not subdir.startswith("__"):
                subdir_templates = get_template_files(subdir_path)
                if subdir_templates:
                    all_templates.extend([(f"{subdir.title()} Templates", t) for t in subdir_templates])

    # Calculate total for pagination
    total_templates = len(all_templates)

    # Create paginator with ALL templates (but don't process them yet)
    paginator = Paginator(all_templates, per_page)
    try:
        # Get the page object for the current page
        page_obj = paginator.page(page)

        # Now process only the templates for the current page
        processed_templates = []
        for dir_name, template in page_obj.object_list:
            template_dir = {"name": dir_name, "templates": process_template_batch([template])}
            processed_templates.extend([(dir_name, t) for t in template_dir["templates"]])

        # Replace the object_list with processed templates
        page_obj.object_list = processed_templates

    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)
        # Process first page templates if there's an error
        processed_templates = []
        for dir_name, template in page_obj.object_list:
            template_dir = {"name": dir_name, "templates": process_template_batch([template])}
            processed_templates.extend([(dir_name, t) for t in template_dir["templates"]])
        page_obj.object_list = processed_templates

    context = {
        "template_dirs": [
            {"name": dir_name, "templates": [t[1] for t in processed_templates if t[0] == dir_name]}
            for dir_name in set(t[0] for t in processed_templates)
        ],
        "total_templates": total_templates,
        "sort": sort,
        "direction": direction,
        "base_dir": settings.BASE_DIR,
        "search_query": search_query,
        "filter_by": filter_by,
        "page_obj": page_obj,  # Use the page object with correct pagination info
        "filter_options": [
            {"value": "all", "label": "All Templates"},
            {"value": "with_sidenav", "label": "With Sidenav"},
            {"value": "with_base", "label": "Extends Base"},
            {"value": "with_styles", "label": "With Style Tags"},
        ],
    }

    return render(request, "template_list.html", context)


def is_admin_url(path):
    """Check if a URL path is an admin URL"""
    if not path:  # Handle None or empty paths
        return False
    admin_url = settings.ADMIN_URL.strip("/")
    return path.startswith(f"/{admin_url}/") or admin_url in path


def website_stats(request):
    """View to show view counts for each URL route"""
    import json
    from collections import defaultdict
    from datetime import timedelta

    from django.db.models import Sum
    from django.urls import get_resolver
    from django.utils import timezone

    # Get all URL patterns
    resolver = get_resolver()
    url_patterns = resolver.url_patterns

    # Dictionary to store view counts
    view_stats = defaultdict(int)

    # Get admin URL for filtering
    admin_url = settings.ADMIN_URL.strip("/")

    # Get all IP records and group by path, excluding admin URLs
    ip_records = (
        IP.objects.exclude(path__startswith=f"/{admin_url}/")
        .values("path")
        .annotate(total_views=Sum("count"))
        .order_by("-total_views")
    )

    # Map paths to their view counts
    for record in ip_records:
        path = record["path"]
        if not is_admin_url(path):  # Additional check for admin URLs
            view_stats[path] = record["total_views"]

    # Get last 30 days of traffic data, excluding admin URLs
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_views = (
        IP.objects.exclude(path__startswith=f"/{admin_url}/")
        .filter(created__gte=thirty_days_ago)
        .values("created__date")
        .annotate(daily_count=Sum("count"))
        .order_by("created__date")
    )

    # Prepare chart data
    dates = []
    views = []
    for day in daily_views:
        dates.append(day["created__date"].strftime("%Y-%m-%d"))
        views.append(day["daily_count"])

    # Get unique visitors (unique IPs), excluding admin URLs
    unique_visitors = IP.objects.exclude(path__startswith=admin_url).values("address").distinct().count()

    total_views = sum(view_stats.values())

    # Calculate traffic status
    if len(views) >= 2:
        last_day = views[-1] if views else 0
        prev_day = views[-2] if len(views) > 1 else 0
        if last_day < prev_day * 0.5:  # More than 50% drop
            status = "danger"
        elif last_day < prev_day * 0.8:  # More than 20% drop
            status = "warning"
        else:
            status = "normal"
    else:
        status = "normal"

    # Get top 50 user agents
    user_agents = (
        IP.objects.exclude(path__startswith=f"/{admin_url}/")
        .exclude(agent__isnull=True)
        .values("agent")
        .annotate(total_count=Sum("count"), last_request=models.Max("created"))
        .order_by("-total_count")[:50]
    )

    # Count unique user agents
    unique_agents_count = (
        IP.objects.exclude(path__startswith=f"/{admin_url}/")
        .exclude(agent__isnull=True)
        .values("agent")
        .distinct()
        .count()
    )

    # Collect URL pattern info
    url_info = []

    def process_patterns(patterns, parent_path=""):
        for pattern in patterns:
            if hasattr(pattern, "url_patterns"):
                # This is a URL resolver (includes), process its patterns
                process_patterns(pattern.url_patterns, parent_path + str(pattern.pattern))
            else:
                # This is a URL pattern
                full_path = parent_path + str(pattern.pattern)

                # Skip admin URLs
                if is_admin_url(full_path):
                    continue

                view_name = (
                    pattern.callback.__name__ if hasattr(pattern.callback, "__name__") else str(pattern.callback)
                )
                if hasattr(pattern.callback, "view_class"):
                    view_name = pattern.callback.view_class.__name__

                # Get view count for this path
                view_count = 0
                for path, count in view_stats.items():
                    if path and path.strip("/") and full_path.strip("/"):
                        if path.strip("/").endswith(full_path.strip("/")) or full_path.strip("/").endswith(
                            path.strip("/")
                        ):
                            view_count += count

                url_info.append({"path": full_path, "view_name": view_name, "view_count": view_count})

    process_patterns(url_patterns)

    # Sort by view count descending
    url_info.sort(key=lambda x: x["view_count"], reverse=True)

    # Web traffic stats
    web_stats = {
        "dates": json.dumps(dates),
        "views": json.dumps(views),
        "total_views": total_views,
        "unique_visitors": unique_visitors,
        "date": timezone.now(),
        "status": status,
        "total_urls": len(url_info),  # Add total URL count
    }

    context = {
        "url_info": url_info,
        "total_views": total_views,
        "web_stats": web_stats,
        "user_agents": user_agents,
        "unique_agents_count": unique_agents_count,
    }

    return render(request, "website_stats.html", context)


class CustomSocialAccountDisconnectView(BaseSocialAccountDisconnectView):
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SocialAccount.objects.none()
        return super().get_queryset()


class MapView(ListView):
    template_name = "map.html"
    context_object_name = "locations"

    def get_queryset(self):
        # Get the marker type from query params, default to 'organizations'
        marker_type = self.request.GET.get("type", "organizations")

        if marker_type == "organizations":
            return Organization.objects.filter(
                latitude__isnull=False, longitude__isnull=False, is_active=True
            ).order_by("-created")
        # Add more types here as needed
        return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        marker_type = self.request.GET.get("type", "organizations")

        context["marker_type"] = marker_type
        context["marker_types"] = [
            {
                "id": "organizations",
                "name": "Organizations",
                "icon": "fa-building",
                "description": "View organizations around the world",
            },
            # Add more marker types here as needed
        ]

        return context


class RoadmapView(TemplateView):
    template_name = "roadmap.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        milestones = [
            {
                "title": "📺 BLTV - BLT Eduction",
                "due_date": "No due date",
                "last_updated": "about 3 hours ago",
                "description": "Add an educational component to BLT so that users can learn along w…",
                "progress": "100%",
                "open": 0,
                "closed": 1,
            },
            {
                "title": "🚀 Code Reviewer Leaderboard",
                "due_date": "No due date",
                "last_updated": "1 day ago",
                "description": "Here's an Emoji Code Reviewer Leaderboard idea, ranking reviewers b…",
                "progress": "50%",
                "open": 1,
                "closed": 1,
            },
            {
                "title": "Bid on Issues",
                "due_date": "No due date",
                "last_updated": "1 day ago",
                "description": "",
                "progress": "0%",
                "open": 1,
                "closed": 0,
            },
            {
                "title": "🏠 Improvements",
                "due_date": "No due date",
                "last_updated": "5 days ago",
                "description": "",
                "progress": "46%",
                "open": 7,
                "closed": 6,
            },
            {
                "title": "🔒 Protection Of Online Privacy",
                "due_date": "No due date",
                "last_updated": "8 days ago",
                "description": "Web Monitoring System Implementation Plan Overview Enhances user tr…",
                "progress": "88%",
                "open": 1,
                "closed": 8,
            },
            {
                "title": "🧠 AI",
                "due_date": "No due date",
                "last_updated": "10 days ago",
                "description": "",
                "progress": "50%",
                "open": 1,
                "closed": 1,
            },
            {
                "title": "🔧 App Improvements",
                "due_date": "No due date",
                "last_updated": "10 days ago",
                "description": "",
                "progress": "0%",
                "open": 16,
                "closed": 0,
            },
            {
                "title": "🛡️ OWASP tools",
                "due_date": "No due date",
                "last_updated": "10 days ago",
                "description": "",
                "progress": "0%",
                "open": 2,
                "closed": 0,
            },
            {
                "title": "🧰 Extension Improvements",
                "due_date": "No due date",
                "last_updated": "10 days ago",
                "description": "",
                "progress": "0%",
                "open": 4,
                "closed": 0,
            },
            {
                "title": "🏆 Sponsorship in app",
                "due_date": "No due date",
                "last_updated": "10 days ago",
                "description": "",
                "progress": "0%",
                "open": 0,
                "closed": 0,
            },
            {
                "title": "🎤 GitHub Sportscaster",
                "due_date": "No due date",
                "last_updated": "10 days ago",
                "description": "",
                "progress": "0%",
                "open": 1,
                "closed": 0,
            },
            {
                "title": "🥗 Daily Check-ins",
                "due_date": "No due date",
                "last_updated": "10 days ago",
                "description": "New Project: Fresh - Daily Check-In Component for BLT Fresh is a pr…",
                "progress": "18%",
                "open": 9,
                "closed": 2,
            },
            {
                "title": "🔥 Time Tracking",
                "due_date": "No due date",
                "last_updated": "10 days ago",
                "description": "Simplified Project: Sizzle - Multi-Platform Time Tracking for BLT P…",
                "progress": "12%",
                "open": 14,
                "closed": 2,
            },
            {
                "title": "🛡️ Trademark Defense",
                "due_date": "No due date",
                "last_updated": "10 days ago",
                "description": "Protects brand integrity and legal standing, important for long-ter…",
                "progress": "30%",
                "open": 7,
                "closed": 3,
            },
            {
                "title": "🏢 Organization Portal in App",
                "due_date": "No due date",
                "last_updated": "11 days ago",
                "description": "",
                "progress": "0%",
                "open": 1,
                "closed": 0,
            },
            {
                "title": "💌 Invites in app",
                "due_date": "No due date",
                "last_updated": "11 days ago",
                "description": "",
                "progress": "0%",
                "open": 1,
                "closed": 0,
            },
            {
                "title": "🌍 Banned Apps Simulation in app",
                "due_date": "No due date",
                "last_updated": "11 days ago",
                "description": "Simulate app behavior in countries with restrictions to ensure compliance "
                "and accessibility.",
                "progress": "0%",
                "open": 1,
                "closed": 0,
            },
            {
                "title": "🤖 Slack Bot 2.0",
                "due_date": "No due date",
                "last_updated": "11 days ago",
                "description": "",
                "progress": "0%",
                "open": 12,
                "closed": 0,
            },
            {
                "title": "🚀 OWASP BLT Adventures",
                "due_date": "No due date",
                "last_updated": "11 days ago",
                "description": "",
                "progress": "0%",
                "open": 1,
                "closed": 0,
            },
            {
                "title": "🌐 Organizations",
                "due_date": "No due date",
                "last_updated": "11 days ago",
                "description": "Project: Refactor BLT Website to Combine Companies and Teams into O…",
                "progress": "0%",
                "open": 4,
                "closed": 0,
            },
            {
                "title": "🔧 Maintenance",
                "due_date": "No due date",
                "last_updated": "11 days ago",
                "description": "General maintenance issues",
                "progress": "50%",
                "open": 16,
                "closed": 16,
            },
            {
                "title": "Bug / Issue / Project tools",
                "due_date": "No due date",
                "last_updated": "11 days ago",
                "description": "",
                "progress": "0%",
                "open": 1,
                "closed": 0,
            },
            {
                "title": "🏆 Gamification",
                "due_date": "No due date",
                "last_updated": "11 days ago",
                "description": "Project Summary: Gamification Integration for BLT Platform The gami…",
                "progress": "15%",
                "open": 17,
                "closed": 3,
            },
            {
                "title": "GSOC tools",
                "due_date": "No due date",
                "last_updated": "11 days ago",
                "description": "",
                "progress": "0%",
                "open": 3,
                "closed": 0,
            },
            {
                "title": "🚀🎨🔄 Tailwind Migration",
                "due_date": "No due date",
                "last_updated": "11 days ago",
                "description": "Migrate the remaining pages to tailwind "
                "https://blt.owasp.org/template_list/?sort=has_style_tags",
                "progress": "0%",
                "open": 1,
                "closed": 0,
            },
            {
                "title": "🐞 New Issue Detail Page",
                "due_date": "No due date",
                "last_updated": "13 days ago",
                "description": "Improves issue tracking efficiency and developer experience on the site.",
                "progress": "66%",
                "open": 3,
                "closed": 6,
            },
            {
                "title": "🥓 BACON",
                "due_date": "No due date",
                "last_updated": "21 days ago",
                "description": "🥓 BACON: Blockchain Assisted Contribution Network BACON is a cuttin…",
                "progress": "50%",
                "open": 7,
                "closed": 7,
            },
            {
                "title": "💰 Multi-Crypto Donations",
                "due_date": "No due date",
                "last_updated": "about 1 month ago",
                "description": "Overview: The Decentralized Multi-Crypto Payment Integration featur…",
                "progress": "25%",
                "open": 6,
                "closed": 2,
            },
            {
                "title": "💡 Suggestions",
                "due_date": "No due date",
                "last_updated": "about 1 month ago",
                "description": "",
                "progress": "50%",
                "open": 1,
                "closed": 1,
            },
            {
                "title": "💸 Pledge",
                "due_date": "No due date",
                "last_updated": "3 months ago",
                "description": "",
                "progress": "0%",
                "open": 1,
                "closed": 0,
            },
            {
                "title": "🌘Dark Mode",
                "due_date": "No due date",
                "last_updated": "3 months ago",
                "description": "",
                "progress": "0%",
                "open": 1,
                "closed": 0,
            },
            {
                "title": "👷 Contributor Ranking",
                "due_date": "No due date",
                "last_updated": "3 months ago",
                "description": "🌞💻🥉 Shows contributor github username, commits, issues opened, issu…",
                "progress": "80%",
                "open": 1,
                "closed": 4,
            },
            {
                "title": "✅ Bug Verifiers",
                "due_date": "No due date",
                "last_updated": "3 months ago",
                "description": "Ensures bug fixes are valid and effective, maintaining site integrity.",
                "progress": "50%",
                "open": 1,
                "closed": 1,
            },
            {
                "title": "🤖 Artificial Intelligence",
                "due_date": "No due date",
                "last_updated": "7 months ago",
                "description": "",
                "progress": "100%",
                "open": 0,
                "closed": 2,
            },
            {
                "title": "🕹️ Penteston Integration",
                "due_date": "No due date",
                "last_updated": "7 months ago",
                "description": "Enhances site security through integrated pentesting tools. We will…",
                "progress": "0%",
                "open": 1,
                "closed": 0,
            },
            {
                "title": "🔔 Follower notifications",
                "due_date": "No due date",
                "last_updated": "7 months ago",
                "description": "The feature would allow users to follow a company's bug reports and…",
                "progress": "0%",
                "open": 1,
                "closed": 0,
            },
            {
                "title": "📊 Review Queue",
                "due_date": "No due date",
                "last_updated": "7 months ago",
                "description": "Streamlines content moderation, improving site quality.",
                "progress": "0%",
                "open": 3,
                "closed": 0,
            },
            {
                "title": "🕵️ Private Bug Bounties",
                "due_date": "No due date",
                "last_updated": "7 months ago",
                "description": "Allows companies to conduct private, paid bug bounties in a non-com…",
                "progress": "25%",
                "open": 3,
                "closed": 1,
            },
            {
                "title": "📡 Cyber Dashboard",
                "due_date": "No due date",
                "last_updated": "7 months ago",
                "description": "🌞💻🥉 a comprehensive dashboard of stats and information for organiza…",
                "progress": "0%",
                "open": 13,
                "closed": 0,
            },
            {
                "title": "🪝 Webhooks",
                "due_date": "No due date",
                "last_updated": "7 months ago",
                "description": "automate the synchronization of issue statuses between GitHub and t…",
                "progress": "0%",
                "open": 2,
                "closed": 0,
            },
            {
                "title": "🔸 Modern Front-End Redesign with React & Tailwind CSS (~350h)",
                "due_date": "No due date",
                "last_updated": "",
                "description": "A complete redesign of BLT's interface, improving accessibility, usability, "
                "and aesthetics. The new front-end will be built with React and Tailwind CSS, "
                "ensuring high performance while maintaining a lightweight architecture under "
                "100MB. Dark mode will be the default, with full responsiveness and an enhanced "
                "user experience.",
                "progress": "0%",
                "open": 0,
                "closed": 0,
            },
            {
                "title": "🔸 Organization Dashboard – Enhanced Vulnerability & Bug Management (~350h)",
                "due_date": "No due date",
                "last_updated": "",
                "description": "Redesign and expand the organization dashboard to provide seamless management of bug "
                "bounties, security reports, and contributor metrics. Features will include advanced "
                "filtering, real-time analytics, and improved collaboration tools for security teams.",
                "progress": "0%",
                "open": 0,
                "closed": 0,
            },
            {
                "title": "🔸 Secure API Development & Migration to Django Ninja (~350h)",
                "due_date": "No due date",
                "last_updated": "",
                "description": "Migrate our existing and develop a secure, well-documented API with automated "
                "security tests to support the new front-end. This may involve migrating from Django "
                "Rest Framework to Django Ninja for improved performance, maintainability, and API "
                "efficiency.",
                "progress": "0%",
                "open": 0,
                "closed": 0,
            },
            {
                "title": "🔸 Gamification & Blockchain Rewards System (Ordinals & Solana) (~350h)",
                "due_date": "No due date",
                "last_updated": "",
                "description": "Introduce GitHub-integrated contribution tracking that rewards security "
                "researchers with Bitcoin Ordinals and Solana-based incentives. This will "
                "integrate with other parts of the website as well such as daily check-ins "
                "and code quality. Gamification elements such as badges, leaderboards, and "
                "contribution tiers will encourage engagement and collaboration in "
                "open-source security.",
                "progress": "0%",
                "open": 0,
                "closed": 0,
            },
            {
                "title": "🔸 Decentralized Bidding System for Issues (Bitcoin Cash Integration) (~350h)",
                "due_date": "No due date",
                "last_updated": "",
                "description": "Create a decentralized system where developers can bid on GitHub issues "
                "using Bitcoin Cash, ensuring direct transactions between contributors and "
                "project owners without BLT handling funds.",
                "progress": "0%",
                "open": 0,
                "closed": 0,
            },
            {
                "title": "🔸 AI-Powered Code Review & Smart Prioritization System for Maintainers (~350h)",
                "due_date": "No due date",
                "last_updated": "",
                "description": "Develop an AI-driven GitHub assistant that analyzes pull requests, detects "
                "security vulnerabilities, and provides real-time suggestions for improving "
                "code quality. A smart prioritization system will help maintainers rank issues "
                "based on urgency, community impact, and dependencies.",
                "progress": "0%",
                "open": 0,
                "closed": 0,
            },
            {
                "title": "🔸 Enhanced Slack Bot & Automation System (~350h)",
                "due_date": "No due date",
                "last_updated": "",
                "description": "Expand the BLT Slack bot to automate vulnerability tracking, send real-time "
                "alerts for new issues, and integrate GitHub notifications and contributor "
                "activity updates for teams. prioritize them based on community engagement, "
                "growth and securing worldwide applications",
                "progress": "0%",
                "open": 0,
                "closed": 0,
            },
        ]

        context["milestones"] = milestones
        context["milestone_count"] = len(milestones)
        return context


class StyleGuideView(TemplateView):
    template_name = "style_guide.html"
