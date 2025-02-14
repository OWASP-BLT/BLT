import json
import os
import subprocess
import tracemalloc
import urllib
from datetime import timedelta
from urllib.parse import urlparse

import psutil
import redis
import requests
import requests.exceptions
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from bs4 import BeautifulSoup
from dj_rest_auth.registration.views import SocialConnectView, SocialLoginView
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import FieldError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
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
from django.views.generic import TemplateView, View

from blt import settings
from website.models import (
    Activity,
    Badge,
    Domain,
    Hunt,
    Issue,
    ManagementCommandLog,
    Organization,
    Points,
    PRAnalysisReport,
    Project,
    Repo,
    SlackBotActivity,
    Suggestion,
    SuggestionVotes,
    Tag,
    User,
    UserBadge,
    UserProfile,
    Wallet,
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


def check_status(request):
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
            "redis_stats": {
                "status": "Not configured",
                "version": None,
                "connected_clients": None,
                "used_memory_human": None,
            }
            if not CHECK_REDIS
            else {},
            "slack_bot": {},
            "management_commands": [],
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
                # Use boolean AND to determine if all runs were successful
                last_success=models.ExpressionWrapper(models.Q(success=True), output_field=models.BooleanField()),
                run_count=models.Max("run_count"),
            )
            .order_by("command_name")
        )

        status_data["management_commands"] = list(command_logs)

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
            openai_api_key = os.getenv("OPENAI_API_KEY")
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

        # Cache the results
        cache.set("service_status", status_data, timeout=CACHE_TIMEOUT)

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
    query = request.GET.get("query")
    stype = request.GET.get("type", "all")
    context = None
    if query is None:
        return render(request, template)
    query = query.strip()

    if stype == "all":
        # Search across multiple models
        organizations = Organization.objects.filter(name__icontains=query)
        issues = Issue.objects.filter(Q(description__icontains=query), hunt=None).exclude(
            Q(is_hidden=True) & ~Q(user_id=request.user.id)
        )[0:20]
        domains = Domain.objects.filter(Q(url__icontains=query), hunt=None)[0:20]
        users = (
            UserProfile.objects.filter(Q(user__username__icontains=query))
            .annotate(total_score=Sum("user__points__score"))
            .order_by("-total_score")[0:20]
        )
        projects = Project.objects.filter(Q(name__icontains=query) | Q(description__icontains=query))
        repos = Repo.objects.filter(Q(name__icontains=query) | Q(description__icontains=query))
        context = {
            "query": query,
            "type": stype,
            "organizations": organizations,
            "issues": issues,
            "domains": domains,
            "users": users,
            "projects": projects,
            "repos": repos,
        }

        for userprofile in users:
            userprofile.badges = UserBadge.objects.filter(user=userprofile.user)
        for org in organizations:
            d = Domain.objects.filter(organization=org).first()
            if d:
                org.absolute_url = d.get_absolute_url()

    elif stype == "issues":
        context = {
            "query": query,
            "type": stype,
            "issues": Issue.objects.filter(Q(description__icontains=query), hunt=None).exclude(
                Q(is_hidden=True) & ~Q(user_id=request.user.id)
            )[0:20],
        }
    elif stype == "domains":
        context = {
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
def vote_suggestions(request):
    if request.method == "POST":
        user = request.userblt_tomato
        data = json.loads(request.body)
        suggestion_id = data.get("suggestion_id")
        suggestion = Suggestion.objects.get(id=suggestion_id)
        up_vote = data.get("up_vote")
        down_vote = data.get("down_vote")
        voted = SuggestionVotes.objects.filter(user=user, suggestion=suggestion).exists()
        if not voted:
            up_vote = True if up_vote else False
            down_vote = True if down_vote else False

            if up_vote or down_vote:
                voted = SuggestionVotes.objects.create(
                    user=user,
                    suggestion=suggestion,
                    up_vote=up_vote,
                    down_vote=down_vote,
                )

                if up_vote:
                    suggestion.up_votes += 1
                if down_vote:
                    suggestion.down_votes += 1
        else:
            if not up_vote:
                suggestion.up_votes -= 1
            if down_vote is False:
                suggestion.down_votes -= 1

            voted = SuggestionVotes.objects.filter(user=user, suggestion=suggestion).delete()

            if up_vote:
                voted = SuggestionVotes.objects.create(user=user, suggestion=suggestion, up_vote=True, down_vote=False)
                suggestion.up_votes += 1

            if down_vote:
                voted = SuggestionVotes.objects.create(user=user, suggestion=suggestion, down_vote=True, up_vote=False)
                suggestion.down_votes += 1

            suggestion.save()

        response = {
            "success": True,
            "up_vote": suggestion.up_votes,
            "down_vote": suggestion.down_votes,
        }
        return JsonResponse(response)

    return JsonResponse({"success": False, "error": "Invalid request method"}, status=402)


@login_required
def set_vote_status(request):
    if request.method == "POST":
        user = request.user
        data = json.loads(request.body)
        id = data.get("id")
        try:
            suggestion = Suggestion.objects.get(id=id)
        except Suggestion.DoesNotExist:
            return JsonResponse({"success": False, "error": "Suggestion not found"}, status=404)

        up_vote = SuggestionVotes.objects.filter(suggestion=suggestion, user=user, up_vote=True).exists()
        down_vote = SuggestionVotes.objects.filter(suggestion=suggestion, user=user, down_vote=True).exists()

        response = {"up_vote": up_vote, "down_vote": down_vote}
        return JsonResponse(response)

    return JsonResponse({"success": False, "error": "Invalid request method"}, status=400)


def add_suggestions(request):
    if request.method == "POST":
        user = request.user if request.user.is_authenticated else None
        data = json.loads(request.body)
        title = data.get("title")
        description = data.get("description", "")
        if title and description:
            suggestion = Suggestion(user=user, title=title, description=description)
            suggestion.save()
            messages.success(request, "Suggestion added successfully.")
            return JsonResponse({"status": "success"})
        else:
            messages.error(request, "Please fill all the fields.")
            return JsonResponse({"status": "error"}, status=400)
    else:
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


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

    def get_historical_counts(self, model):
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
            date_counts = (
                model.objects.annotate(date=TruncDate(date_field))
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
                dates, counts = self.get_historical_counts(model)
                trend = counts[-1] - counts[-2] if len(counts) >= 2 else 0
                total_count = model.objects.count()

                stats_data.append(
                    {
                        "label": model_name,
                        "count": total_count,
                        "icon": known_icons.get(model_name, "fas fa-database"),
                        "history": json.dumps(counts),
                        "dates": json.dumps(dates),
                        "trend": trend,
                    }
                )
            except Exception:
                continue

        context["stats"] = sorted(stats_data, key=lambda x: x["count"], reverse=True)
        return context


def view_suggestions(request):
    suggestion = Suggestion.objects.all()
    return render(request, "feature_suggestion.html", {"suggestions": suggestion})


def sitemap(request):
    random_domain = Domain.objects.order_by("?").first()
    return render(request, "sitemap.html", {"random_domain": random_domain})


def badge_list(request):
    badges = Badge.objects.all()
    badges = Badge.objects.annotate(user_count=Count("userbadge"))
    return render(request, "badges.html", {"badges": badges})


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
        pr_link = request.POST.get("pr_link")
        issue_link = request.POST.get("issue_link")

        if not pr_link or not issue_link:
            return JsonResponse({"error": "Both PR and issue links are required."}, status=400)

        pr_parts = pr_link.split("/")
        issue_parts = issue_link.split("/")
        owner, repo = pr_parts[3], pr_parts[4]
        pr_number, issue_number = pr_parts[-1], issue_parts[-1]

        pr_data = fetch_github_data(owner, repo, "pulls", pr_number)
        roadmap_data = fetch_github_data(owner, repo, "issues", issue_number)

        if "error" in pr_data or "error" in roadmap_data:
            return JsonResponse(
                {"error": (f"Failed to fetch PR or roadmap data: " f"{pr_data.get('error', 'Unknown error')}")},
                status=500,
            )

        analysis = analyze_pr_content(pr_data, roadmap_data)
        save_analysis_report(pr_link, issue_link, analysis)
        return JsonResponse({"message": "PR submitted successfully"})

    return render(request, "submit_roadmap_pr.html")


def view_pr_analysis(request):
    reports = PRAnalysisReport.objects.all()
    return render(request, "view_pr_analysis.html", {"reports": reports})


def home(request):
    # last_commit = get_last_commit_date()
    return render(request, "home.html", {"last_commit": ""})


def test_sentry(request):
    if request.user.is_superuser:
        division_by_zero = 1 / 0  # This will raise a ZeroDivisionError
    return HttpResponse("Test error sent to Sentry!")


def handler404(request, exception):
    return render(request, "404.html", {}, status=404)


def handler500(request, exception=None):
    return render(request, "500.html", {}, status=500)


def stats_dashboard(request):
    # Try to get stats from cache first
    cache_key = "dashboard_stats"
    stats = cache.get(cache_key)

    if stats is None:
        # If not in cache, compute stats with optimized queries
        users = User.objects.aggregate(total=Count("id"), active=Count("id", filter=Q(is_active=True)))

        issues = Issue.objects.aggregate(total=Count("id"), open=Count("id", filter=Q(status="open")))

        domains = Domain.objects.aggregate(total=Count("id"), active=Count("id", filter=Q(is_active=True)))

        organizations = Organization.objects.aggregate(total=Count("id"), active=Count("id", filter=Q(is_active=True)))

        hunts = Hunt.objects.aggregate(total=Count("id"), active=Count("id", filter=Q(is_published=True)))

        # Combine all stats
        stats = {
            "users": {"total": users["total"], "active": users["active"]},
            "issues": {"total": issues["total"], "open": issues["open"]},
            "domains": {"total": domains["total"], "active": domains["active"]},
            "organizations": {"total": organizations["total"], "active": organizations["active"]},
            "hunts": {"total": hunts["total"], "active": hunts["active"]},
            "points": {"total": Points.objects.aggregate(total=Sum("score"))["total"] or 0},
            "projects": {"total": Project.objects.count()},
            "activities": {
                "total": Activity.objects.count(),
                # Only fetch recent activities if needed for display
                "recent": list(
                    Activity.objects.order_by("-timestamp").values("id", "title", "description", "timestamp")[:5]
                ),
            },
        }

        # Cache the results for 5 minutes
        cache.set(cache_key, stats, timeout=300)

    return render(request, "stats_dashboard.html", {"stats": stats})


def sync_github_projects(request):
    if request.method == "POST":
        try:
            call_command("check_owasp_projects")
            messages.success(request, "Successfully synced OWASP GitHub projects.")
        except Exception as e:
            messages.error(request, f"Error syncing OWASP GitHub projects: {str(e)}")
    return redirect("stats_dashboard")


def check_owasp_compliance(request):
    """View to check OWASP project compliance criteria"""
    if request.method == "POST":
        url = request.POST.get("url")
        if not url:
            messages.error(request, "URL is required")
            return redirect("check_owasp_compliance")

        try:
            # Check GitHub compliance
            parsed_url = urlparse(url)
            is_github = parsed_url.netloc == "github.com"
            is_owasp_org = parsed_url.path.startswith("/OWASP/")

            # Check website compliance
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            # Check for OWASP mention
            content = soup.get_text().lower()
            has_owasp_mention = "owasp" in content

            # Check for project page link
            owasp_links = [a for a in soup.find_all("a") if "owasp.org" in a.get("href", "")]
            has_project_link = len(owasp_links) > 0

            # Check for up-to-date info
            has_dates = bool(soup.find_all(["time", "date"]))

            # Check vendor neutrality
            paywall_terms = ["premium", "subscribe", "subscription", "pay", "pricing"]
            has_paywall_indicators = any(term in content for term in paywall_terms)

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

            return render(request, "owasp_compliance_result.html", context)

        except Exception as e:
            messages.error(request, f"Error checking compliance: {str(e)}")
            return redirect("check_owasp_compliance")

    return render(request, "owasp_compliance_check.html")
