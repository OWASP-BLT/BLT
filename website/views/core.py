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
import redis
import requests
import requests.exceptions
import sentry_sdk
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
from django.db.models import Count, Q, Sum
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
    Domain,
    ForumCategory,
    ForumComment,
    ForumPost,
    ForumVote,
    Hunt,
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
    Post,  
)
from website.utils import analyze_pr_content, fetch_github_data, safe_redirect_allowed, save_analysis_report

# from website.bot import conversation_chain, is_api_key_valid, load_vector_store


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
                    response = requests.get(
                        "https://api.github.com/user/repos",
                        headers={"Authorization": f"token {github_token}"},
                        timeout=5,
                    )
                    status_data["github"] = response.status_code == 200
                except requests.exceptions.RequestException as e:
                    print(f"GitHub API Error: {e}")

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
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'")
                    status_data["db_connection_count"] = cursor.fetchone()[0]

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

        status_data["chart_data"] = chart_data

        # Cache the results
        cache.set("service_status", status_data, timeout=CACHE_TIMEOUT)

    # Prepare the chart data for the template
    template_chart_data = {
        "dates": json.dumps(status_data["chart_data"]["dates"]),
        "team_joins": json.dumps(status_data["chart_data"]["team_joins"]),
        "commands": json.dumps(status_data["chart_data"]["commands"]),
    }

    return render(request, "status_page.html", {"status": status_data, "chart_data": template_chart_data})


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
    template_name = "index.html"

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

                # Get filtered count and total count
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

    from website.models import ForumPost, GitHubIssue, Repo, User, Post  # Add BlogPost model

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

    # Get top PR contributors using the leaderboard method
    top_pr_contributors = (
        GitHubIssue.objects.filter(type="pull_request", is_merged=True)
        .values("user_profile__user__username", "user_profile__user__email", "user_profile__github_url")
        .annotate(total_prs=Count("id"))
        .order_by("-total_prs")[:5]
    )

    # Get latest blog posts
    latest_blog_posts = Post.objects.order_by('-created_at')[:4]

    return render(
        request,
        "home.html",
        {
            "last_commit": last_commit,
            "current_year": timezone.now().year,
            "latest_repos": latest_repos,
            "total_repos": total_repos,
            "recent_posts": recent_posts,
            "top_bug_reporters": top_bug_reporters,
            "top_pr_contributors": top_pr_contributors,
            "latest_blog_posts": latest_blog_posts,  # Add latest blog posts to context
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

    days = period_map.get(period, 30)

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
            "users": {"total": users["total"], "active": users["active"], "total_all_time": total_users},
            "issues": {"total": issues["total"], "open": issues["open"], "total_all_time": total_issues},
            "domains": {"total": domains["total"], "active": domains["active"], "total_all_time": total_domains},
            "organizations": {
                "total": organizations["total"],
                "active": organizations["active"],
                "total_all_time": total_organizations,
            },
            "hunts": {"total": hunts["total"], "active": hunts["active"], "total_all_time": total_hunts},
            "points": {"total": points, "total_all_time": total_points},
            "projects": {"total": projects, "total_all_time": total_projects},
            "activities": {
                "total": activities,
                "total_all_time": total_activities,
                "recent": list(recent_activities),
            },
        }

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

        try:
            # Parse URL to determine if it's a GitHub repository
            is_github = "github.com" in url.lower()
            is_owasp_org = "github.com/owasp" in url.lower()

            # Fetch and analyze website content
            response = requests.get(url, timeout=10, verify=False)
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
                "url": url,
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
    return render(request, "management_commands.html", {"commands": commands})


def run_management_command(request):
    if request.method == "POST":
        # Check if user is superuser
        if not request.user.is_superuser:
            messages.error(request, "Only superusers can run management commands.")
            return redirect("management_commands")

        command = request.POST.get("command")
        logging.info(f"Running command: {command}")
        print(f"Running command: {command}")
        try:
            # Only allow running commands from the website app and exclude initsuperuser
            app_name = get_commands().get(command)
            if app_name != "website" or command == "initsuperuser":
                msg = f"Command {command} is not allowed to run from the web interface"
                messages.error(request, msg)
                return redirect("management_commands")

            # Get or create the command log
            log_entry, created = ManagementCommandLog.objects.get_or_create(
                command_name=command, defaults={"run_count": 0, "success": False, "last_run": timezone.now()}
            )

            # Run the command
            call_command(command)

            # Update the log entry
            log_entry.success = True
            log_entry.last_run = timezone.now()
            log_entry.run_count = log_entry.run_count + 1
            log_entry.error_message = ""
            log_entry.save()

            messages.success(
                request,
                f"Successfully ran command '{command}'. "
                f"This command has been run {log_entry.run_count} time{'s' if log_entry.run_count != 1 else ''}.",
            )

        except Exception as e:
            sentry_sdk.capture_exception(e)

            # Update log entry with error
            if "log_entry" in locals():
                log_entry.success = False
                log_entry.last_run = timezone.now()
                log_entry.run_count = log_entry.run_count + 1
                log_entry.error_message = str(e)
                log_entry.save()

            messages.error(
                request, f"Error running command '{command}': {str(e)}. " f"Check the logs for more details."
            )
    return redirect("management_commands")


def template_list(request):
    from django.db.models import Sum
    from django.urls import URLPattern, URLResolver, get_resolver

    def get_templates_from_dir(directory):
        templates = []
        for template_name in os.listdir(directory):
            if template_name.endswith(".html"):
                template_path = os.path.join(directory, template_name)

                # Get last modified time
                modified_time = datetime.fromtimestamp(os.path.getmtime(template_path))

                # Get view count from IP table
                view_count = (
                    IP.objects.filter(
                        Q(path__endswith=f"/{template_name}") | Q(path__endswith=f"/templates/{template_name}")
                    ).aggregate(total_views=Sum("count"))["total_views"]
                    or 0
                )

                # Get GitHub URL
                github_url = f"https://github.com/OWASP/BLT/blob/main/website/templates/{template_name}"

                # Check template contents for sidenav and base.html extension
                has_sidenav = False
                extends_base = False
                has_style_tags = False
                with open(template_path, "r") as f:
                    content = f.read()
                    if '{% include "includes/sidenav.html" %}' in content:
                        has_sidenav = True
                    if '{% extends "base.html" %}' in content:
                        extends_base = True
                    if "<style" in content:
                        has_style_tags = True

                # Check if template has a URL
                template_url = None
                resolver = get_resolver()

                def check_urlpatterns(urlpatterns, template_name):
                    # Get template name without .html extension for comparison
                    template_base_name = template_name.replace(".html", "")

                    for pattern in urlpatterns:
                        if isinstance(pattern, URLResolver):
                            match = check_urlpatterns(pattern.url_patterns, template_name)
                            if match:
                                return match
                        elif isinstance(pattern, URLPattern):
                            # Get pattern path and name for comparison
                            pattern_path = str(pattern.pattern) if pattern.pattern else ""
                            pattern_name = getattr(pattern, "name", "")

                            # Check class-based views
                            if hasattr(pattern.callback, "view_class"):
                                view_class = pattern.callback.view_class
                                pattern_path = str(pattern.pattern) if pattern.pattern else ""
                                pattern_name = getattr(pattern, "name", "")

                                # Check template_name attribute
                                if hasattr(view_class, "template_name"):
                                    view_template = view_class.template_name
                                    if view_template == template_name or view_template == template_base_name:
                                        return pattern.pattern

                                # Check if pattern path or name matches template name
                                path_match = pattern_path == template_base_name
                                path_replace_match = (
                                    pattern_path and pattern_path.replace("-", "_") == template_base_name
                                )
                                name_match = pattern_name == template_base_name
                                name_replace_match = (
                                    pattern_name and pattern_name.replace("-", "_") == template_base_name
                                )

                                if path_match or path_replace_match or name_match or name_replace_match:
                                    return pattern.pattern

                            # Check function-based views
                            elif hasattr(pattern.callback, "__code__"):
                                func_code = pattern.callback.__code__
                                pattern_path = str(pattern.pattern) if pattern.pattern else ""
                                pattern_name = getattr(pattern, "name", "")

                                if (
                                    template_name in func_code.co_names
                                    or template_base_name in func_code.co_names
                                    or pattern.callback.__name__ == template_base_name
                                    or pattern_path == template_base_name
                                    or (pattern_path and pattern_path.replace("-", "_") == template_base_name)
                                    or pattern_name == template_base_name
                                    or (pattern_name and pattern_name.replace("-", "_") == template_base_name)
                                ):
                                    return pattern.pattern

                            # Check closure-based views
                            elif hasattr(pattern.callback, "__closure__") and pattern.callback.__closure__:
                                for cell in pattern.callback.__closure__:
                                    if isinstance(cell.cell_contents, str):
                                        matches_template = cell.cell_contents.endswith(
                                            template_name
                                        ) or cell.cell_contents.endswith(template_base_name)
                                        if matches_template:
                                            return pattern.pattern
                    return None

                url_pattern = check_urlpatterns(resolver.url_patterns, template_name)
                if url_pattern:
                    template_url = "/" + str(url_pattern).lstrip("^").rstrip("$")
                    if template_url.endswith("/"):
                        template_url = template_url[:-1]

                templates.append(
                    {
                        "name": template_name,
                        "path": template_path,
                        "url": template_url,
                        "modified": modified_time,
                        "views": view_count,
                        "github_url": github_url,
                        "has_sidenav": has_sidenav,
                        "extends_base": extends_base,
                        "has_style_tags": has_style_tags,
                    }
                )
        return templates

    template_dirs = []
    main_template_dir = os.path.join(settings.BASE_DIR, "website", "templates")

    if os.path.exists(main_template_dir):
        template_dirs.append({"name": "Main Templates", "templates": get_templates_from_dir(main_template_dir)})

    for subdir in os.listdir(main_template_dir):
        subdir_path = os.path.join(main_template_dir, subdir)
        if os.path.isdir(subdir_path) and not subdir.startswith("__"):
            template_dirs.append(
                {"name": f"{subdir.title()} Templates", "templates": get_templates_from_dir(subdir_path)}
            )

    # Calculate total templates
    total_templates = sum(len(dir["templates"]) for dir in template_dirs)

    # Get sort parameters
    sort = request.GET.get("sort", "name")
    direction = request.GET.get("dir", "asc")

    # Sort templates in each directory
    for dir in template_dirs:
        dir["templates"].sort(key=lambda x: (x.get(sort, ""), x["name"]), reverse=direction == "desc")

    return render(
        request,
        "template_list.html",
        {
            "template_dirs": template_dirs,
            "total_templates": total_templates,
            "sort": sort,
            "direction": direction,
            "base_dir": settings.BASE_DIR,
        },
    )


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
