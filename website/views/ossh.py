from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import render

from website.models import Repo
from website.utils import fetch_github_user_data


def ossh_home(request):
    template = "ossh/home.html"
    return render(request, template)


def ossh_results(request):
    template = "ossh/results.html"

    if request.method == "POST":
        github_username = request.POST.get("github-username")
        user_data = fetch_github_user_data(github_username)
        print(user_data)
        results = recommendation_engine(user_data)
        context = {"username": github_username, "user_data": user_data, "repos": results}
        return render(request, template, context)


def recommendation_engine(user_data):
    # Extract user's languages with weights
    total_bytes = sum(lang[1] for lang in user_data["top_languages"])
    language_weights = {lang: bytes_count / total_bytes * 100 for lang, bytes_count in user_data["top_languages"]}

    # Get the top 5 languages (those that make up most of the user's code)
    primary_languages = set(lang for lang, _ in sorted(language_weights.items(), key=lambda x: x[1], reverse=True))

    # Extract tags from user's repositories
    user_tags = set()
    for repo in user_data["repositories"]:
        if repo["description"]:
            # Extract keywords from descriptions as tags
            words = set(word.lower() for word in repo["description"].replace(",", " ").replace("-", " ").split())
            user_tags.update(words)

    # Add any topics if available
    if user_data.get("top_topics"):
        user_tags.update(user_data["top_topics"])

    # Query to find matching repositories
    recommended_repos = (
        Repo.objects.filter(
            Q(primary_language__in=primary_languages)  # Match user's main languages
            | Q(open_issues__gt=0)  # Has active issues to work on
            | Q(tags__name__in=user_tags)  # Match repository tags with user interests
        )
        .annotate(
            # Calculate a comprehensive relevance score
            relevance_score=(
                # Language match gets weighted score based on user's language preferences
                Case(
                    *[
                        When(
                            primary_language=lang,
                            then=Value(int(min(weight * 1.5, 100))),  # Cap at 100 points
                        )
                        for lang, weight in language_weights.items()
                    ],
                    default=Value(0),
                    output_field=IntegerField(),
                )
                # Add weighted stars to the score
                + Case(
                    When(stars__gt=1000, then=Value(50)),
                    When(stars__gt=100, then=Value(30)),
                    When(stars__gt=10, then=Value(10)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
                # Add points for active issues
                + Case(
                    When(open_issues__gt=10, then=Value(20)),
                    When(open_issues__gt=0, then=Value(10)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
                # Add points for tag matches
                + Case(
                    When(tags__name__in=user_tags, then=Value(40)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
                # Add points for repository size
                + Case(
                    When(size__gt=1000000, then=Value(15)),  # >1GB
                    When(size__gt=100000, then=Value(10)),  # >100MB
                    When(size__gt=10000, then=Value(5)),  # >10MB
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
        )
        .order_by("-relevance_score", "-stars")
        .distinct()[:50]  # Limit to top 50 recommendations
    )

    return list(recommended_repos)
