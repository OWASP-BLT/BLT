import json
import os
import urllib
import uuid
from datetime import datetime, timezone

import requests
import requests.exceptions
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialConnectView, SocialLoginView
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import FieldError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView, View
from requests.auth import HTTPBasicAuth
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from sendgrid import SendGridAPIClient

from blt import settings
from website.bot import conversation_chain, is_api_key_valid, load_vector_store
from website.models import (
    ChatBotLog,
    Domain,
    Issue,
    Suggestion,
    SuggestionVotes,
    UserProfile,
    Wallet,
)
from website.utils import safe_redirect_allowed

vector_store = None
DAILY_REQUEST_LIMIT = 10


def check_status(request):
    status = cache.get("service_status")

    if not status:
        status = {
            "bitcoin": False,
            "bitcoin_block": None,
            "sendgrid": False,
            "github": False,
        }

        bitcoin_rpc_user = os.getenv("BITCOIN_RPC_USER")
        bitcoin_rpc_password = os.getenv("BITCOIN_RPC_PASSWORD")
        bitcoin_rpc_host = os.getenv("BITCOIN_RPC_HOST", "127.0.0.1")
        bitcoin_rpc_port = os.getenv("BITCOIN_RPC_PORT", "8332")

        try:
            response = requests.post(
                f"http://{bitcoin_rpc_host}:{bitcoin_rpc_port}",
                json={
                    "jsonrpc": "1.0",
                    "id": "curltest",
                    "method": "getblockchaininfo",
                    "params": [],
                },
                auth=HTTPBasicAuth(bitcoin_rpc_user, bitcoin_rpc_password),
            )
            if response.status_code == 200:
                data = response.json().get("result", {})
                status["bitcoin"] = True
                status["bitcoin_block"] = data.get("blocks", None)
        except Exception as e:
            print(f"Bitcoin Core Node Error: {e}")

        try:
            sg = SendGridAPIClient(os.getenv("SENDGRID_PASSWORD"))
            response = sg.client.api_keys._(sg.api_key).get()
            if response.status_code == 200:
                status["sendgrid"] = True
        except Exception as e:
            print(f"SendGrid Error: {e}")

        github_token = os.getenv("GITHUB_ACCESS_TOKEN")

        if not github_token:
            print(
                "GitHub Access Token not found. Please set the GITHUB_ACCESS_TOKEN environment variable."
            )
            status["github"] = False
        else:
            try:
                headers = {"Authorization": f"token {github_token}"}
                response = requests.get("https://api.github.com/user/repos", headers=headers)

                print(f"Response Status Code: {response.status_code}")
                print(f"Response Content: {response.json()}")

                if response.status_code == 200:
                    status["github"] = True
                    print("GitHub API token has repository access.")
                else:
                    status["github"] = False
                    print(
                        f"GitHub API token check failed with status code {response.status_code}: {response.json().get('message', 'No message provided')}"
                    )

            except requests.exceptions.RequestException as e:
                status["github"] = False
                print(f"GitHub API Error: {e}")

        cache.set("service_status", status, timeout=60)

    return render(request, "status_page.html", {"status": status})


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
    stype = request.GET.get("type")
    context = None
    if query is None:
        return render(request, template)
    query = query.strip()
    if query[:6] == "issue:":
        stype = "issue"
        query = query[6:]
    elif query[:7] == "domain:":
        stype = "domain"
        query = query[7:]
    elif query[:5] == "user:":
        stype = "user"
        query = query[5:]
    elif query[:6] == "label:":
        stype = "label"
        query = query[6:]
    if stype == "issue" or stype is None:
        context = {
            "query": query,
            "type": stype,
            "issues": Issue.objects.filter(Q(description__icontains=query), hunt=None).exclude(
                Q(is_hidden=True) & ~Q(user_id=request.user.id)
            )[0:20],
        }
    elif stype == "domain":
        context = {
            "query": query,
            "type": stype,
            "domains": Domain.objects.filter(Q(url__icontains=query), hunt=None)[0:20],
        }
    elif stype == "user":
        context = {
            "query": query,
            "type": stype,
            "users": UserProfile.objects.filter(Q(user__username__icontains=query))
            .annotate(total_score=Sum("user__points__score"))
            .order_by("-total_score")[0:20],
        }
    elif stype == "label":
        context = {
            "query": query,
            "type": stype,
            "issues": Issue.objects.filter(Q(label__icontains=query), hunt=None).exclude(
                Q(is_hidden=True) & ~Q(user_id=request.user.id)
            )[0:20],
        }

    if request.user.is_authenticated:
        context["wallet"] = Wallet.objects.get(user=request.user)
    return render(request, template, context)


@api_view(["POST"])
def chatbot_conversation(request):
    try:
        today = datetime.now(timezone.utc).date()
        rate_limit_key = f"global_daily_requests_{today}"
        request_count = cache.get(rate_limit_key, 0)

        if request_count >= DAILY_REQUEST_LIMIT:
            return Response(
                {"error": "Daily request limit exceeded."}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        question = request.data.get("question", "")
        if not question:
            return Response({"error": "Invalid question"}, status=status.HTTP_400_BAD_REQUEST)
        check_api = is_api_key_valid(os.getenv("OPENAI_API_KEY"))
        if not check_api:
            ChatBotLog.objects.create(question=question, answer="Error: Invalid API Key")
            return Response({"error": "Invalid API Key"}, status=status.HTTP_400_BAD_REQUEST)

        if not question or not isinstance(question, str):
            ChatBotLog.objects.create(question=question, answer="Error: Invalid question")
            return Response({"error": "Invalid question"}, status=status.HTTP_400_BAD_REQUEST)

        global vector_store
        if not vector_store:
            try:
                vector_store = load_vector_store()
            except FileNotFoundError as e:
                ChatBotLog.objects.create(
                    question=question, answer="Error: Vector store not found {e}"
                )
                return Response(
                    {"error": "Vector store not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except Exception as e:
                ChatBotLog.objects.create(question=question, answer=f"Error: {str(e)}")
                return Response(
                    {"error": "Error loading vector store"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            finally:
                if not vector_store:
                    ChatBotLog.objects.create(
                        question=question, answer="Error: Vector store not loaded"
                    )
                    return Response(
                        {"error": "Vector store not loaded"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

        if question.lower() == "exit":
            if "buffer" in request.session:
                del request.session["buffer"]
            return Response({"answer": "Conversation memory cleared."}, status=status.HTTP_200_OK)

        crc, memory = conversation_chain(vector_store)
        if "buffer" in request.session:
            memory.buffer = request.session["buffer"]

        try:
            response = crc.invoke({"question": question})
        except Exception as e:
            ChatBotLog.objects.create(question=question, answer=f"Error: {str(e)}")
            return Response(
                {"error": "An internal error has occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        cache.set(rate_limit_key, request_count + 1, timeout=86400)  # Timeout set to one day
        request.session["buffer"] = memory.buffer

        ChatBotLog.objects.create(question=question, answer=response["answer"])

        return Response({"answer": response["answer"]}, status=status.HTTP_200_OK)

    except Exception as e:
        ChatBotLog.objects.create(
            question=request.data.get("question", ""), answer=f"Error: {str(e)}"
        )
        return Response(
            {"error": "An internal error has occurred."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


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
                    user=user, suggestion=suggestion, up_vote=up_vote, down_vote=down_vote
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
                voted = SuggestionVotes.objects.create(
                    user=user, suggestion=suggestion, up_vote=True, down_vote=False
                )
                suggestion.up_votes += 1

            if down_vote:
                voted = SuggestionVotes.objects.create(
                    user=user, suggestion=suggestion, down_vote=True, up_vote=False
                )
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

        up_vote = SuggestionVotes.objects.filter(
            suggestion=suggestion, user=user, up_vote=True
        ).exists()
        down_vote = SuggestionVotes.objects.filter(
            suggestion=suggestion, user=user, down_vote=True
        ).exists()

        response = {"up_vote": up_vote, "down_vote": down_vote}
        return JsonResponse(response)

    return JsonResponse({"success": False, "error": "Invalid request method"}, status=400)


@login_required
def add_suggestions(request):
    if request.method == "POST":
        user = request.user
        data = json.loads(request.body)
        title = data.get("title")
        description = data.get("description", "")
        id = str(uuid.uuid4())
        print(description, title, id)
        if title and description and user:
            suggestion = Suggestion(user=user, title=title, description=description, id=id)
            suggestion.save()
            messages.success(request, "Suggestion added successfully.")
            return JsonResponse({"status": "success"})
        else:
            messages.error(request, "Please fill all the fields.")
            return JsonResponse({"status": "error"}, status=400)


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
        result = default_storage.save(
            "uploads\/" + self.kwargs["hash"] + ".png", ContentFile(data.read())
        )
        return JsonResponse({"status": result})


class StatsDetailView(TemplateView):
    template_name = "stats.html"

    def get_historical_counts(self, model):
        # Map models to their date fields
        date_field_map = {
            "Issue": "created",
            "UserProfile": "created",  # From user creation
            "Comment": "created_date",
            "Hunt": "created",
            "Domain": "created",
            "Company": "created",
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
            # Add other models as needed
        }

        date_field = date_field_map.get(model.__name__, "created")
        dates = []
        counts = []

        try:
            # Annotate and count by truncated date
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
            # If the date field doesn't exist, return empty lists
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
            "Company": "fas fa-building",
            "HuntPrize": "fas fa-gift",
            "IssueScreenshot": "fas fa-camera",
            "Winner": "fas fa-trophy",
            "Points": "fas fa-star",
            "InviteFriend": "fas fa-envelope-open",
            "UserProfile": "fas fa-id-badge",
            "IP": "fas fa-network-wired",
            "CompanyAdmin": "fas fa-user-tie",
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
                        "history": json.dumps(counts),  # Serialize counts to JSON
                        "dates": json.dumps(dates),  # Serialize dates to JSON
                        "trend": trend,
                    }
                )
            except Exception as e:
                # Optionally log the exception
                continue

        context["stats"] = sorted(stats_data, key=lambda x: x["count"], reverse=True)
        return context


def view_suggestions(request):
    suggestion = Suggestion.objects.all()
    return render(request, "feature_suggestion.html", {"suggestions": suggestion})


def sitemap(request):
    random_domain = Domain.objects.order_by("?").first()
    return render(request, "sitemap.html", {"random_domain": random_domain})


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


def home(request):
    return render(request, "home.html")


def handler404(request, exception):
    return render(request, "404.html", {}, status=404)


def handler500(request, exception=None):
    return render(request, "500.html", {}, status=500)
