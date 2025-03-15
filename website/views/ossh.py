import json
import re
from collections import defaultdict

from django.core.cache import cache
from django.db.models import Count, FloatField, Q, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import render

from website.models import OsshArticle, OsshCommunity, OsshDiscussionChannel, Repo
from website.utils import fetch_github_user_data

from .constants import COMMON_TECHNOLOGIES, COMMON_TOPICS, PROGRAMMING_LANGUAGES, TAG_NORMALIZATION

ALLOWED_TAGS = set(PROGRAMMING_LANGUAGES + COMMON_TECHNOLOGIES + COMMON_TOPICS)


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


def get_github_data(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            github_username = data.get("github_username")

            if not github_username:
                return JsonResponse({"error": "GitHub username is required"}, status=400)

            cached_data = cache.get(f"github_data_{github_username}")
            if cached_data:
                print("Found cached user data")
                user_data = cached_data
            else:
                user_data = fetch_github_user_data(github_username)
                user_tags, language_weights = preprocess_user_data(user_data)
                user_data["user_tags"] = user_tags
                user_data["language_weights"] = language_weights
                cache.set(f"github_data_{github_username}", user_data, timeout=3600)  # Cache for 1 hour

            return render(request, "ossh/includes/github_stats.html", {"user_data": user_data})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except KeyError:
            return JsonResponse({"error": "Missing required data"}, status=400)
        except Exception as e:
            print(f"Error in get_github_data: {e}", exc_info=True)
            return JsonResponse({"error": "An internal error occurred. Please try again later."}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


def preprocess_user_data(user_data):
    user_tags = defaultdict(int)

    for repo in user_data["repositories"]:
        if repo.get("description"):
            words = tokenize(repo["description"])
            for word in words:
                normalized_word = normalize_tag(word)
                if normalized_word in TAG_NORMALIZATION.values():
                    user_tags[normalized_word] += 1

    if user_data.get("top_topics"):
        for topic in user_data["top_topics"]:
            normalized_topic = normalize_tag(topic)
            if normalized_topic in TAG_NORMALIZATION.values():
                user_tags[normalized_topic] = user_tags.get(normalized_topic, 0) + 1
            else:
                user_tags[normalized_topic] = 1

    user_tags = sorted(user_tags.items(), key=lambda x: x[1], reverse=True)

    # Extract user's languages with weights
    total_bytes = sum(lang[1] for lang in user_data["top_languages"])
    language_weights = {
        lang: (bytes_count / total_bytes * 100)
        for lang, bytes_count in user_data["top_languages"]
        if (bytes_count / total_bytes * 100) >= 0.05
    }

    print(user_tags)
    print(language_weights)
    return user_tags, language_weights


def repo_recommender(user_tags, language_weights):
    tag_names = [tag for tag, _ in user_tags]
    language_list = list(language_weights.keys())

    repos = (
        Repo.objects.filter(Q(primary_language__in=language_list) | Q(tags__name__in=tag_names))
        .distinct()
        .prefetch_related("tags")
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


def get_recommended_repos(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            github_username = data.get("github_username")

            if not github_username:
                return JsonResponse({"error": "GitHub username is required"}, status=400)

            user_data = cache.get(f"github_data_{github_username}")
            if not user_data:
                return JsonResponse({"error": "GitHub data not found. Fetch it first."}, status=400)

            recommended_repos = repo_recommender(user_data["user_tags"], user_data["language_weights"])

            return render(request, "ossh/includes/recommended_repos.html", {"repos": recommended_repos})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except KeyError:
            return JsonResponse({"error": "Missing required data"}, status=400)
        except Exception as e:
            print(f"Error in get_recommended_repos: {e}")  # Print instead of logging
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


def get_recommended_communities(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            github_username = data.get("github_username")

            if not github_username:
                return JsonResponse({"error": "GitHub username is required"}, status=400)

            user_data = cache.get(f"github_data_{github_username}")
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
            print(f"Error in get_recommended_communities: {e}")  # Print instead of logging
            return JsonResponse({"error": "An internal error occurred. Please try again later."}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


def discussion_channel_recommender(user_tags, language_weights, top_n=5):
    matching_channels = OsshDiscussionChannel.objects.filter(Q(tags__name__in=[tag[0] for tag in user_tags])).distinct()

    recommended_channels = []
    for channel in matching_channels:
        tag_matches = sum(1 for tag in user_tags if tag[0] in channel.tags.values_list("name", flat=True))

        language_weight = sum(
            language_weights.get(tag[1], 0)
            for tag in user_tags
            if tag[0] in channel.tags.values_list("name", flat=True)
        )

        relevance_score = tag_matches + language_weight + (channel.member_count // 1000)

        if relevance_score > 0:
            matching_tags = [tag.name for tag in channel.tags.all() if tag.name in dict(user_tags)]
            matching_languages = [
                tag[1]
                for tag in user_tags
                if tag[0] in channel.tags.values_list("name", flat=True) and tag[1] in language_weights
            ]

            reasoning = []
            if matching_tags:
                reasoning.append(f"Matching tags: {', '.join(matching_tags)}")
            if matching_languages:
                reasoning.append(f"Matching language: {', '.join(matching_languages)}")

            recommended_channels.append(
                {
                    "channel": channel,
                    "relevance_score": relevance_score,
                    "reasoning": " | ".join(reasoning) if reasoning else "No specific reason",
                }
            )

    recommended_channels.sort(key=lambda x: x["relevance_score"], reverse=True)
    return recommended_channels[:top_n]


def get_recommended_discussion_channels(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            github_username = data.get("github_username")

            if not github_username:
                return JsonResponse({"error": "GitHub username is required"}, status=400)

            user_data = cache.get(f"github_data_{github_username}")
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
            print(f"Error in get_recommended_discussion_channels: {e}")  # Print instead of logging
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


def get_recommended_articles(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            github_username = data.get("github_username")

            if not github_username:
                return JsonResponse({"error": "GitHub username is required"}, status=400)

            user_data = cache.get(f"github_data_{github_username}")
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
            print(f"Error in get_recommended_articles: {e}")  # Print instead of logging
            return JsonResponse({"error": "An internal error occurred. Please try again later."}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)

