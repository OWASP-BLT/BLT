import json
import logging
import re
from collections import defaultdict
from functools import wraps

from django.core.cache import cache
from django.db.models import Count, FloatField, Q, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import render

from website.models import OsshArticle, OsshCommunity, OsshDiscussionChannel, Repo
from website.utils import fetch_github_user_data, get_client_ip

from .constants import COMMON_TECHNOLOGIES, COMMON_TOPICS, PROGRAMMING_LANGUAGES, TAG_NORMALIZATION

logger = logging.getLogger(__name__)

CACHE_TIMEOUT = 3600  # 1 hour
MIN_LANGUAGE_PERCENTAGE = 0.05
MAX_REQUEST_SIZE = 1024 * 10  # 10KB
ALLOWED_TAGS = set(PROGRAMMING_LANGUAGES + COMMON_TECHNOLOGIES + COMMON_TOPICS)


def rate_limit(max_requests=10, window_sec=60, methods=("POST",)):
    """
    Fixed-window IP+path limiter using Django cache.
    - No external deps, minimal overhead.
    - In production, use a shared cache (Redis/Memcached) so all workers share limits.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if methods and request.method not in methods:
                return view_func(request, *args, **kwargs)

            key = f"rl:{get_client_ip(request)}:{request.path}"
            try:
                # Create counter with TTL if not present
                created = cache.add(key, 1, timeout=window_sec)
                count = 1 if created else cache.incr(key)
            except Exception:
                # Fallback if backend doesn’t support incr atomically
                current = cache.get(key, 0)
                count = current + 1
                cache.set(key, count, timeout=window_sec)

            if count > max_requests:
                resp = JsonResponse({"error": "Too many requests"}, status=429)
                # Conservative hint; window remaining isn’t tracked precisely without extra keys.
                resp["Retry-After"] = str(window_sec)
                resp["X-RateLimit-Limit"] = str(max_requests)
                resp["X-RateLimit-Remaining"] = "0"
                return resp

            # Optional informational headers for successful requests
            remaining = max(0, max_requests - count)

            response = view_func(request, *args, **kwargs)
            # Add headers to success responses too (optional)
            try:
                response["X-RateLimit-Limit"] = str(max_requests)
                response["X-RateLimit-Remaining"] = str(remaining)
            except Exception:
                logger.warning("Failed to set rate limit headers on response.", exc_info=True)
            return response

        return _wrapped

    return decorator


# --- end limiter ---


def get_cache_key(username):
    # Sanitize username for safe cache key
    safe_username = re.sub(r"[^a-zA-Z0-9_-]", "", username)
    return f"github_data_{safe_username}"


# Helper function to tokenize text
def tokenize(text):
    """Tokenize text into words, handling camelCase and special characters."""
    if not text:
        return set()

    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    return set(word.lower() for word in text.split())


# Helper function to normalize tags
def normalize_tag(tag):
    """Normalize tag variations."""
    return TAG_NORMALIZATION.get(tag, tag)


def ossh_home(request):
    template = "ossh/home.html"
    return render(request, template)


def ossh_results(request):
    template = "ossh/results.html"

    if request.method == "POST":
        github_username = request.POST.get("github-username", "").strip()

        if not github_username:
            return JsonResponse({"error": "GitHub username is required"}, status=400)

        context = {"username": github_username}
        return render(request, template, context)

    return JsonResponse({"error": "Invalid request method"}, status=405)


@rate_limit(max_requests=10, window_sec=60, methods=("POST",))
def get_github_data(request):
    if request.method == "POST":
        try:
            if len(request.body) > MAX_REQUEST_SIZE:
                return JsonResponse({"error": "Request too large"}, status=413)

            data = json.loads(request.body)
            github_username = data.get("github_username")

            if not github_username:
                return JsonResponse({"error": "GitHub username is required"}, status=400)

            cached_data = cache.get(get_cache_key(github_username))
            if cached_data:
                logger.debug("Found cached user data")
                user_data = cached_data
            else:
                user_data = fetch_github_user_data(github_username)
                if not user_data or not isinstance(user_data, dict):
                    return JsonResponse({"error": "Failed to fetch GitHub data"}, status=500)

                # Validate required keys exist
                required_keys = ["repositories", "top_languages", "top_topics"]
                if not all(key in user_data for key in required_keys):
                    return JsonResponse({"error": "Incomplete GitHub data"}, status=500)
                user_tags, language_weights = preprocess_user_data(user_data)
                user_data["user_tags"] = user_tags
                user_data["language_weights"] = language_weights
                cache.set(f"github_data_{github_username}", user_data, timeout=CACHE_TIMEOUT)  # Cache for 1 hour

            return render(request, "ossh/includes/github_stats.html", {"user_data": user_data})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except KeyError:
            return JsonResponse({"error": "Missing required data"}, status=400)
        except Exception as e:
            logger.error(f"Error in get_github_data: {e}", exc_info=True)
            return JsonResponse({"error": "An internal error occurred. Please try again later."}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


def preprocess_user_data(user_data):
    user_tags = defaultdict(int)
    ALLOWED_NORMALIZED_TAGS = {normalize_tag(tag) for tag in ALLOWED_TAGS}

    for repo in user_data["repositories"]:
        if repo.get("description"):
            words = tokenize(repo["description"])
            for word in words:
                normalized_word = normalize_tag(word)
                if normalized_word in ALLOWED_NORMALIZED_TAGS:
                    user_tags[normalized_word] += 1

    if user_data.get("top_topics"):
        for topic in user_data["top_topics"]:
            normalized_topic = normalize_tag(topic)
            if normalized_topic in ALLOWED_NORMALIZED_TAGS:
                user_tags[normalized_topic] += 1

    user_tags = sorted(user_tags.items(), key=lambda x: x[1], reverse=True)

    # Extract user's languages with weights
    total_bytes = sum(lang[1] for lang in user_data["top_languages"])
    if total_bytes == 0:
        language_weights = {}
    else:
        language_weights = {
            lang: (bytes_count / total_bytes * 100)
            for lang, bytes_count in user_data["top_languages"]
            if (bytes_count / total_bytes * 100) >= MIN_LANGUAGE_PERCENTAGE
        }

    logger.debug(f"User tags: {user_tags}")
    logger.debug(f"Language weights: {language_weights}")
    return user_tags, language_weights


def repo_recommender(user_tags, language_weights):
    tag_names = [tag for tag, _ in user_tags]
    language_list = list(language_weights.keys())

    repos = (
        Repo.objects.filter(Q(primary_language__in=language_list) | Q(tags__name__in=tag_names))
        .distinct()
        .prefetch_related("tags")
        .select_related("project")
    )

    repos = repos.annotate(
        tag_score=Coalesce(Count("tags", filter=Q(tags__name__in=tag_names)), Value(0), output_field=FloatField()),
        language_score=Value(0, output_field=FloatField()),
    )

    recommended_repos = []
    for repo in repos:
        tag_score = repo.tag_score
        language_score = language_weights.get(repo.primary_language, 0)

        relevance_score = tag_score + language_score

        if relevance_score > 0:  # Ensure non-zero relevance
            matching_tags = [tag.name for tag in repo.tags.all() if tag.name in dict(user_tags)]
            matching_languages = [repo.primary_language] if repo.primary_language in language_weights else []

            reasoning = []
            if matching_tags:
                reasoning.append(f"Matching tags: {', '.join(matching_tags)}")
            if matching_languages:
                reasoning.append(f"Matching language: {', '.join(matching_languages)}")

            recommended_repos.append(
                {
                    "repo": repo,
                    "relevance_score": relevance_score,
                    "reasoning": " | ".join(reasoning) if reasoning else "No specific reason",
                }
            )

    recommended_repos.sort(key=lambda x: x["relevance_score"], reverse=True)
    return recommended_repos[:5]


@rate_limit(max_requests=20, window_sec=60, methods=("POST",))
def get_recommended_repos(request):
    if request.method == "POST":
        try:
            if len(request.body) > MAX_REQUEST_SIZE:
                return JsonResponse({"error": "Request too large"}, status=413)
            data = json.loads(request.body)
            github_username = data.get("github_username")

            if not github_username:
                return JsonResponse({"error": "GitHub username is required"}, status=400)

            user_data = cache.get(get_cache_key(github_username))
            if not user_data:
                return JsonResponse({"error": "GitHub data not found. Fetch it first."}, status=400)

            recommended_repos = repo_recommender(user_data["user_tags"], user_data["language_weights"])

            return render(request, "ossh/includes/recommended_repos.html", {"repos": recommended_repos})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except KeyError:
            return JsonResponse({"error": "Missing required data"}, status=400)
        except Exception as e:
            logger.error(f"Error in get_recommended_repos: {e}")
            return JsonResponse({"error": "An internal error occurred. Please try again later."}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


def community_recommender(user_tags, language_weights):
    tag_names = [tag for tag, _ in user_tags]
    language_list = list(language_weights.keys())

    communities = (
        OsshCommunity.objects.filter(Q(tags__name__in=tag_names) | Q(metadata__primary_language__in=language_list))
        .distinct()
        .prefetch_related("tags")
    )

    communities = communities.annotate(
        tag_score=Coalesce(Count("tags", filter=Q(tags__name__in=tag_names)), Value(0), output_field=FloatField()),
        language_score=Value(0, output_field=FloatField()),
    )

    recommended_communities = []
    for community in communities:
        tag_score = community.tag_score
        language_score = language_weights.get(community.metadata.get("primary_language", ""), 0)

        relevance_score = tag_score + language_score

        if relevance_score > 0:
            matching_tags = [tag.name for tag in community.tags.all() if tag.name in dict(user_tags)]
            matching_languages = (
                [community.metadata.get("primary_language")]
                if community.metadata.get("primary_language") in language_weights
                else []
            )

            reasoning = []
            if matching_tags:
                reasoning.append(f"Matching tags: {', '.join(matching_tags)}")
            if matching_languages:
                reasoning.append(f"Matching language: {', '.join(matching_languages)}")

            recommended_communities.append(
                {
                    "community": community,
                    "relevance_score": relevance_score,
                    "reasoning": " | ".join(reasoning) if reasoning else "No specific reason",
                }
            )

    recommended_communities.sort(key=lambda x: x["relevance_score"], reverse=True)
    return recommended_communities


@rate_limit(max_requests=20, window_sec=60, methods=("POST",))
def get_recommended_communities(request):
    if request.method == "POST":
        try:
            if len(request.body) > MAX_REQUEST_SIZE:
                return JsonResponse({"error": "Request too large"}, status=413)
            data = json.loads(request.body)
            github_username = data.get("github_username")

            if not github_username:
                return JsonResponse({"error": "GitHub username is required"}, status=400)

            user_data = cache.get(get_cache_key(github_username))
            if not user_data:
                return JsonResponse({"error": "GitHub data not found. Fetch it first."}, status=400)

            recommended_communities = community_recommender(user_data["user_tags"], user_data["language_weights"])

            return render(
                request, "ossh/includes/recommended_communities.html", {"communities": recommended_communities}
            )

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except KeyError:
            return JsonResponse({"error": "Missing required data"}, status=400)
        except Exception as e:
            logger.error(f"Error in get_recommended_communities: {e}")  # Print instead of logging
            return JsonResponse({"error": "An internal error occurred. Please try again later."}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


def discussion_channel_recommender(user_tags, language_weights, top_n=5):
    """
    Recommend discussion channels based on user's tag preferences.

    Note: OsshDiscussionChannel model does not have a metadata field,
    so language_weights parameter is ignored (kept for API consistency).
    """
    tag_names = [tag for tag, _ in user_tags]
    matching_channels = (
        OsshDiscussionChannel.objects.filter(Q(tags__name__in=tag_names))
        .distinct()
        .prefetch_related("tags")  # Performance optimization
    )

    recommended_channels = []
    tag_weight_map = dict(user_tags)

    for channel in matching_channels:
        channel_tag_names = {tag.name for tag in channel.tags.all()}

        # Weighted tag scoring bug fix (replaces main's counting logic)
        # Calculate weighted tag score based on user's tag weights
        tag_score = sum(tag_weight_map.get(tag, 0) for tag in channel_tag_names)

        # Use tag_score as relevance (channels don't have language metadata)
        relevance_score = tag_score

        if relevance_score > 0:
            matching_tags = [tag for tag in channel_tag_names if tag in tag_weight_map]

            reasoning = []
            if matching_tags:
                reasoning.append(f"Matching tags: {', '.join(matching_tags)}")

            recommended_channels.append(
                {
                    "channel": channel,
                    "relevance_score": relevance_score,
                    "reasoning": " | ".join(reasoning) if reasoning else "No specific reason",
                }
            )

    recommended_channels.sort(key=lambda x: x["relevance_score"], reverse=True)
    return recommended_channels[:top_n]


@rate_limit(max_requests=20, window_sec=60, methods=("POST",))
def get_recommended_discussion_channels(request):
    if request.method == "POST":
        try:
            if len(request.body) > MAX_REQUEST_SIZE:
                return JsonResponse({"error": "Request too large"}, status=413)
            data = json.loads(request.body)
            github_username = data.get("github_username")

            if not github_username:
                return JsonResponse({"error": "GitHub username is required"}, status=400)

            user_data = cache.get(get_cache_key(github_username))
            if not user_data:
                return JsonResponse({"error": "GitHub data not found. Fetch it first."}, status=400)

            language_weights = user_data.get("language_weights", {})
            recommended_discussion_channels = discussion_channel_recommender(user_data["user_tags"], language_weights)

            return render(
                request,
                "ossh/includes/recommended_discussion_channels.html",
                {"channels": recommended_discussion_channels},
            )

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except KeyError:
            return JsonResponse({"error": "Missing required data"}, status=400)
        except Exception as e:
            logger.error(f"Error in get_recommended_discussion_channels: {e}")  # Print instead of logging
            return JsonResponse({"error": "An internal error occurred. Please try again later."}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


def article_recommender(user_tags, language_weights, top_n=5):
    tag_names = [tag for tag, _ in user_tags]
    tag_weight_map = dict(user_tags)  # Convert to dictionary for fast lookup
    language_list = list(language_weights.keys())

    articles = (
        OsshArticle.objects.filter(Q(tags__name__in=tag_names))
        .distinct()
        .prefetch_related("tags")
        .annotate(
            tag_score=Coalesce(Count("tags", filter=Q(tags__name__in=tag_names)), Value(0), output_field=FloatField()),
            language_score=Value(0, output_field=FloatField()),
        )
    )

    recommended_articles = []
    for article in articles:
        tag_score = sum(tag_weight_map.get(tag.name, 0) for tag in article.tags.all())
        primary_language = article.metadata.get("primary_language", "") if hasattr(article, "metadata") else ""
        language_score = language_weights.get(primary_language, 0)

        relevance_score = tag_score + language_score
        if relevance_score > 0:
            matching_tags = [tag.name for tag in article.tags.all() if tag.name in tag_weight_map]
            matching_languages = [primary_language] if primary_language in language_weights else []

            reasoning = []
            if matching_tags:
                reasoning.append(f"Matching tags: {', '.join(matching_tags)}")
            if matching_languages:
                reasoning.append(f"Matching language: {', '.join(matching_languages)}")

            recommended_articles.append(
                {
                    "article": article,
                    "relevance_score": relevance_score,
                    "reasoning": " | ".join(reasoning) if reasoning else "No specific reason",
                }
            )

    return sorted(recommended_articles, key=lambda x: x["relevance_score"], reverse=True)[:top_n]


@rate_limit(max_requests=20, window_sec=60, methods=("POST",))
def get_recommended_articles(request):
    if request.method == "POST":
        try:
            if len(request.body) > MAX_REQUEST_SIZE:
                return JsonResponse({"error": "Request too large"}, status=413)
            data = json.loads(request.body)
            github_username = data.get("github_username")

            if not github_username:
                return JsonResponse({"error": "GitHub username is required"}, status=400)

            user_data = cache.get(get_cache_key(github_username))
            if not user_data:
                return JsonResponse({"error": "GitHub data not found. Fetch it first."}, status=400)

            user_tags = user_data.get("user_tags", [])
            language_weights = user_data.get("language_weights", {})

            recommended_articles = article_recommender(user_tags, language_weights)

            return render(request, "ossh/includes/recommended_articles.html", {"articles": recommended_articles})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except KeyError:
            return JsonResponse({"error": "Missing required data"}, status=400)
        except Exception as e:
            logger.error(f"Error in get_recommended_articles: {e}")  # Print instead of logging
            return JsonResponse({"error": "An internal error occurred. Please try again later."}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)
