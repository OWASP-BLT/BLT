import hashlib
import hmac
import json
import logging
import os
from datetime import datetime

from allauth.account.signals import user_signed_up
from dateutil import parser as dateutil_parser
from dateutil.parser import ParserError
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.core.mail import send_mail
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import ExtractMonth
from django.dispatch import receiver
from django.http import Http404, HttpResponse, HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import DetailView, ListView, TemplateView, View
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response

from website.decorators import ratelimit
from website.forms import MonitorForm, UserDeleteForm, UserProfileForm
from website.models import (
    IP,
    BaconEarning,
    BaconSubmission,
    Badge,
    Challenge,
    Contributor,
    ContributorStats,
    Domain,
    GitHubIssue,
    GitHubReview,
    Hunt,
    InviteFriend,
    Issue,
    IssueScreenshot,
    Monitor,
    Notification,
    Points,
    Repo,
    Tag,
    Thread,
    User,
    UserBadge,
    UserProfile,
    Wallet,
)

logger = logging.getLogger(__name__)


def extract_github_username(github_url):
    """
    Extract GitHub username from a GitHub URL for avatar display.

    Args:
        github_url (str): GitHub URL like 'https://github.com/username' or 'https://github.com/apps/dependabot'

    Returns:
        str or None: The username part of the URL, or None if invalid/empty
    """
    if not github_url or not isinstance(github_url, str):
        return None

    # Strip trailing slashes and whitespace
    github_url = github_url.strip().rstrip("/")  # Clean URL format

    # Remove query parameters and fragments if present
    github_url = github_url.split("?")[0].split("#")[0]

    # Ensure URL contains at least one slash
    if "/" not in github_url:
        return None

    # Split on "/" and get the last segment
    segments = github_url.split("/")
    username = segments[-1] if segments else None

    # Return username only if it's non-empty and not domain parts or protocol prefixes
    if username and username not in ["github.com", "www.github.com", "www", "http:", "https:"]:
        return username

    return None


@receiver(user_signed_up)
def handle_user_signup(request, user, **kwargs):
    referral_token = request.session.get("ref")
    if referral_token:
        try:
            invite = InviteFriend.objects.get(referral_code=referral_token)
            invite.recipients.add(user)
            invite.point_by_referral += 2
            invite.save()
            reward_sender_with_points(invite.sender)
            del request.session["ref"]
        except InviteFriend.DoesNotExist:
            pass


def update_bch_address(request):
    if request.method == "POST":
        selected_crypto = request.POST.get("selected_crypto")
        new_address = request.POST.get("new_address")
        if selected_crypto and new_address:
            try:
                user_profile = request.user.userprofile
                if selected_crypto == "Bitcoin":
                    user_profile.btc_address = new_address
                elif selected_crypto == "Ethereum":
                    user_profile.eth_address = new_address
                elif selected_crypto == "BitcoinCash":
                    user_profile.bch_address = new_address
                else:
                    messages.error(request, f"Invalid crypto selected: {selected_crypto}")
                    return redirect(reverse("profile", args=[request.user.username]))
                user_profile.save()
                messages.success(request, f"{selected_crypto} Address updated successfully.")
            except Exception as e:
                messages.error(request, f"Failed to update {selected_crypto} Address.")
        else:
            messages.error(request, f"Please provide a valid {selected_crypto} Address.")
    else:
        messages.error(request, "Invalid request method.")

        username = request.user.username if request.user.username else "default_username"
        return redirect(reverse("profile", args=[username]))


@login_required
def profile_edit(request):
    from allauth.account.models import EmailAddress

    Tag.objects.get_or_create(name="GSOC")
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    # Get the user's current email BEFORE changes
    original_email = request.user.email

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=user_profile)

        if form.is_valid():
            new_email = form.cleaned_data["email"]

            # Check email uniqueness
            if User.objects.exclude(pk=request.user.pk).filter(email=new_email).exists():
                form.add_error("email", "This email is already in use")
                return render(request, "profile_edit.html", {"form": form})

            # Check if the user already has this email
            existing_email = EmailAddress.objects.filter(user=request.user, email=new_email).first()
            if existing_email:
                if existing_email.verified:
                    form.add_error("email", "You already have this email verified. Please set it as primary instead.")
                    return render(request, "profile_edit.html", {"form": form})

            if EmailAddress.objects.exclude(user=request.user).filter(email=new_email).exists():
                form.add_error("email", "This email is already registered or pending verification")
                return render(request, "profile_edit.html", {"form": form})

            # Detect email change before saving profile fields
            email_changed = new_email != original_email

            # Save profile form (does "not" touch email in user model)
            form.save()

            if email_changed:
                # Remove any pending unverified emails
                EmailAddress.objects.filter(user=request.user, verified=False).delete()

                # Create new unverified email entry
                # Create or update email entry as unverified
                email_address, created = EmailAddress.objects.update_or_create(
                    user=request.user,
                    email=new_email,
                    defaults={"verified": False, "primary": False},
                )

                # Rate limit: atomic check-and-set to prevent race conditions
                rate_key = f"email_verification_rate_{request.user.id}"

                # add() only sets if key doesn't exist (atomic operation)
                if not cache.add(rate_key, True, timeout=60):
                    messages.warning(
                        request,
                        "Too many requests. Please wait a minute before trying again.",
                    )
                    return redirect("profile", slug=request.user.username)

                # Send verification email
                try:
                    email_address.send_confirmation(request, signup=False)
                except Exception as e:
                    logger.exception(f"Failed to send email confirmation to {new_email}: {e}")
                    messages.error(request, "Failed to send verification email. Please try again later.")
                    return redirect("profile", slug=request.user.username)

                messages.info(
                    request,
                    "A verification link has been sent to your new email. Please verify to complete the update.",
                )
                return redirect("profile", slug=request.user.username)

            # No email change=normal success
            messages.success(request, "Profile updated successfully!")
            return redirect("profile", slug=request.user.username)

        else:
            messages.error(request, "Please correct the errors below.")

    else:
        form = UserProfileForm(
            instance=user_profile,
            initial={"email": request.user.email},
        )

    return render(request, "profile_edit.html", {"form": form})


@login_required(login_url="/accounts/login")
def user_dashboard(request, template="index_user.html"):
    hunts = Hunt.objects.filter(is_published=True)
    upcoming_hunt = []
    ongoing_hunt = []
    previous_hunt = []
    for hunt in hunts:
        if ((hunt.starts_on - datetime.now(timezone.utc)).total_seconds()) > 0:
            upcoming_hunt.append(hunt)
        elif ((hunt.end_on - datetime.now(timezone.utc)).total_seconds()) < 0:
            previous_hunt.append(hunt)
        else:
            ongoing_hunt.append(hunt)
    context = {
        "upcoming_hunts": upcoming_hunt,
        "ongoing_hunt": ongoing_hunt,
        "previous_hunt": previous_hunt,
    }
    return render(request, template, context)


class UserDeleteView(LoginRequiredMixin, View):
    """
    Deletes the currently signed-in user and all associated data.
    """

    def get(self, request, *args, **kwargs):
        form = UserDeleteForm()
        return render(request, "user_deletion.html", {"form": form})

    def post(self, request, *args, **kwargs):
        form = UserDeleteForm(request.POST)
        if form.is_valid():
            user = request.user
            logout(request)
            user.delete()
            messages.success(request, "Account successfully deleted")
            return redirect(reverse("home"))
        return render(request, "user_deletion.html", {"form": form})


class InviteCreate(TemplateView):
    template_name = "invite.html"

    def post(self, request, *args, **kwargs):
        email = request.POST.get("email")
        exists = False
        domain = None
        if email:
            domain = email.split("@")[-1]
        context = {
            "domain": domain,
            "email": email,
        }
        return render(request, "invite.html", context)


def get_github_stats(user_profile):
    # Get all PRs with repo info
    user_prs = (
        GitHubIssue.objects.filter(
            Q(user_profile=user_profile) | Q(reviews__reviewer=user_profile), type="pull_request"
        )
        .select_related("repo")
        .distinct()
        .order_by("-created_at")
    )

    # Calculate reviewed PRs
    reviewed_count = GitHubIssue.objects.filter(
        reviews__reviewer=user_profile,
    ).count()

    logger.debug(f"Total PRs found: {user_prs.count()}")

    # Overall stats
    merged_count = user_prs.filter(is_merged=True).count()
    open_count = user_prs.filter(state="open").count()
    closed_count = user_prs.filter(state="closed", is_merged=False).count()

    users_with_github = UserProfile.objects.exclude(github_url="").exclude(github_url=None)
    contributor_count = users_with_github.count()

    # Group PRs by repo
    repos_with_prs = {}
    for pr in user_prs:
        repo_name = pr.repo.name if pr.repo else "Other"
        repo_id = pr.repo.id if pr.repo else None
        repo_url = pr.repo.repo_url if pr.repo else None

        repos_with_prs.setdefault(
            repo_name,
            {
                "repo_name": repo_name,
                "repo_id": repo_id,
                "repo_url": repo_url,
                "pull_requests": [],
                "stats": {"merged_count": 0, "open_count": 0, "closed_count": 0, "reviewed_count": 0},
            },
        )

        repos_with_prs[repo_name]["pull_requests"].append(pr)

        # Track authored vs reviewed contributions
        if pr.user_profile == user_profile:
            if pr.is_merged:
                repos_with_prs[repo_name]["stats"]["merged_count"] += 1
            elif pr.state == "open":
                repos_with_prs[repo_name]["stats"]["open_count"] += 1
            elif pr.state == "closed" and not pr.is_merged:
                repos_with_prs[repo_name]["stats"]["closed_count"] += 1
        elif pr.reviews.filter(reviewer=user_profile).exists():
            repos_with_prs[repo_name]["stats"]["reviewed_count"] += 1

    # Get review ranking
    all_reviewers = (
        UserProfile.objects.annotate(review_count=Count("reviews_made_as_user"))
        .filter(review_count__gt=0)
        .order_by("-review_count")
    )

    review_rank = None
    total_reviewers = all_reviewers.count()
    for i, reviewer in enumerate(all_reviewers, 1):
        if reviewer.id == user_profile.id:
            review_rank = f"#{i} out of {total_reviewers}"
            break

    return {
        "overall_stats": {
            "merged_count": merged_count,
            "open_count": open_count,
            "closed_count": closed_count,
            "reviewed_count": reviewed_count,
            "user_rank": f"#{user_profile.contribution_rank} out of {contributor_count}",
            "review_rank": review_rank,
        },
        "repos_with_prs": repos_with_prs,
    }


class UserProfileDetailView(DetailView):
    model = get_user_model()
    slug_field = "username"
    template_name = "profile.html"

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Http404:
            messages.error(self.request, "That user was not found.")
            return redirect("/")

        # Update the view count and save the model
        self.object.userprofile.visit_count = len(IP.objects.filter(path=request.path))
        self.object.userprofile.save()

        return super(UserProfileDetailView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        # if userprofile does not exist, create it
        if not UserProfile.objects.filter(user=self.object).exists():
            UserProfile.objects.create(user=self.object)

        user = self.object
        context = super(UserProfileDetailView, self).get_context_data(**kwargs)
        # Add bacon earning data
        bacon_earning = BaconEarning.objects.filter(user=user).first()
        logger.debug(f"Bacon earning for {user.username}: {bacon_earning}")
        context["bacon_earned"] = bacon_earning.tokens_earned if bacon_earning else 0

        # Get bacon submission stats
        context["bacon_submissions"] = {
            "pending": BaconSubmission.objects.filter(user=user, transaction_status="pending").count(),
            "completed": BaconSubmission.objects.filter(user=user, transaction_status="completed").count(),
        }

        milestones = [7, 15, 30, 100, 180, 365]
        base_milestone = 0
        next_milestone = 0
        for milestone in milestones:
            if user.userprofile.current_streak >= milestone:
                base_milestone = milestone
            elif user.userprofile.current_streak < milestone:
                next_milestone = milestone
                break
        context["base_milestone"] = base_milestone
        context["next_milestone"] = next_milestone
        # Fetch badges
        user_badges = UserBadge.objects.filter(user=user).select_related("badge")
        context["user_badges"] = user_badges  # Add badges to context
        context["is_mentor"] = UserBadge.objects.filter(user=user, badge__title="Mentor").exists()
        context["available_badges"] = Badge.objects.all()

        user_points = Points.objects.filter(user=self.object).order_by("id")
        context["user_points"] = user_points
        context["my_score"] = list(user_points.aggregate(total_score=Sum("score")).values())[0]
        context["websites"] = (
            Domain.objects.filter(issue__user=self.object).annotate(total=Count("issue")).order_by("-total")
        )
        context["activities"] = Issue.objects.filter(user=self.object, hunt=None).exclude(
            Q(is_hidden=True) & ~Q(user_id=self.request.user.id)
        )[0:3]
        context["activity_screenshots"] = {}
        screenshots = IssueScreenshot.objects.filter(issue__in=context["activities"]).select_related("issue")
        context["activity_screenshots"] = {s.issue: s for s in screenshots}
        context["profile_form"] = UserProfileForm()
        context["total_open"] = Issue.objects.filter(user=self.object, status="open").count()
        context["total_closed"] = Issue.objects.filter(user=self.object, status="closed").count()
        context["current_month"] = timezone.now().month
        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.filter(user=self.request.user).first()
        six_months_ago = timezone.now() - relativedelta(months=6)
        context["graph"] = (
            Issue.objects.filter(user=self.object)
            .filter(
                created__gte=six_months_ago,
                created__lte=timezone.now(),
            )
            .annotate(month=ExtractMonth("created"))
            .values("month")
            .annotate(c=Count("id"))
            .order_by()
        )
        context["total_bugs"] = Issue.objects.filter(user=self.object, hunt=None).count()
        bug_counts = Issue.objects.filter(user=self.object, hunt=None).values("label").annotate(count=Count("id"))
        bug_count_map = {item["label"]: item["count"] for item in bug_counts}
        for i in range(7):
            context[f"bug_type_{i}_count"] = bug_count_map.get(str(i), 0)
        bug_qs = Issue.objects.filter(user=self.object, hunt=None)
        for i in range(7):
            context[f"bug_type_{i}"] = bug_qs.filter(label=str(i))

        arr = []
        allFollowers = user.userprofile.follower.select_related("user").all()
        context["followers"] = [up.user for up in allFollowers]

        arr = []
        allFollowing = user.userprofile.follows.select_related("user").all()
        context["following"] = [up.user for up in allFollowing]

        context["followers_list"] = [up.user.email for up in allFollowers]
        context["bookmarks"] = user.userprofile.issue_saved.all()
        # tags
        context["user_related_tags"] = user.userprofile.tags.all()
        context["issues_hidden"] = "checked" if user.userprofile.issues_hidden else "!checked"
        # pull request info
        stats = get_github_stats(user.userprofile)
        context.update(
            {
                "overall_stats": stats["overall_stats"],
                "repos_with_prs": stats["repos_with_prs"],
            }
        )

        return context

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
        if request.FILES.get("user_avatar") and form.is_valid():
            form.save()
        else:
            hide = True if request.POST.get("issues_hidden") == "on" else False
            user_issues = Issue.objects.filter(user=request.user)
            user_issues.update(is_hidden=hide)
            request.user.userprofile.issues_hidden = hide
            request.user.userprofile.save()
        return redirect(reverse("profile", kwargs={"slug": kwargs.get("slug")}))


class LeaderboardBase:
    def get_leaderboard(self, month=None, year=None, api=False):
        data = User.objects

        if year and not month:
            data = data.filter(points__created__year=year)

        if year and month:
            data = data.filter(Q(points__created__year=year) & Q(points__created__month=month))

        # Bot identifiers to exclude from leaderboard
        bots = ["copilot", "[bot]", "dependabot", "github-actions", "renovate"]

        # Create dynamic bot exclusion query
        bot_exclusions = Q()
        for bot in bots:
            bot_exclusions |= Q(username__icontains=bot)

        data = (
            data.annotate(total_score=Sum("points__score"))
            .order_by("-total_score")
            .filter(
                total_score__gt=0,
                username__isnull=False,
            )
            .exclude(username="")
            .exclude(bot_exclusions)  # Exclude bot users
        )
        if api:
            return data.values("id", "username", "total_score")
        return data

    def current_month_leaderboard(self, api=False):
        """
        leaderboard which includes current month users scores
        """
        return self.get_leaderboard(month=int(timezone.now().month), year=int(timezone.now().year), api=api)

    def monthly_year_leaderboard(self, year, api=False):
        """
        leaderboard which includes current year top user from each month
        """

        monthly_winner = []

        # iterating over months 1-12
        for month in range(1, 13):
            month_winner = self.get_leaderboard(month, year, api).first()
            monthly_winner.append(month_winner)

        return monthly_winner


class GlobalLeaderboardView(LeaderboardBase, ListView):
    """
    Returns: All users:score data in descending order,
    including pull requests, code reviews, top visitors, and top streakers
    """

    model = User
    template_name = "leaderboard_global.html"

    def get_context_data(self, *args, **kwargs):
        """
        Assembles template context for the global leaderboard page, adding leaderboards and related data.

        The context includes:
        - `user_related_tags`: tags associated with user profiles.
        - `wallet`: the requesting user's Wallet if authenticated.
        - `leaderboard`: top users by total score (limited to 10).
        - `pr_leaderboard`: top repositories/users by merged pull request count (top 10).
        - `code_review_leaderboard`: top reviewers by review count (top 10).
        - `top_visitors`: user profiles ordered by daily visit count (top 10).

        Returns:
            dict: Context mapping names (as listed above) to their querysets or values.
        """
        context = super(GlobalLeaderboardView, self).get_context_data(*args, **kwargs)

        user_related_tags = Tag.objects.filter(userprofile__isnull=False).distinct()
        context["user_related_tags"] = user_related_tags

        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.filter(user=self.request.user).first()

        context["leaderboard"] = self.get_leaderboard()[:10]  # Limit to 10 entries

        # Pull Request Leaderboard - Use Contributor model
        # Dynamically filters for OWASP-BLT repos (will include any new BLT repos added to database)
        # Filter for PRs merged in the last 6 months
        from dateutil.relativedelta import relativedelta

        bots = ["copilot", "[bot]", "dependabot", "github-actions", "renovate"]
        since_date = timezone.now() - relativedelta(months=6)

        # Create dynamic bot exclusion query
        bot_exclusions = Q()
        for bot in bots:
            bot_exclusions |= Q(contributor__name__icontains=bot)

        pr_leaderboard = (
            GitHubIssue.objects.filter(
                type="pull_request",
                is_merged=True,
                contributor__isnull=False,
                merged_at__gte=since_date,
            )
            .filter(
                Q(repo__repo_url__startswith="https://github.com/OWASP-BLT/")
                | Q(repo__repo_url__startswith="https://github.com/owasp-blt/")
            )
            .exclude(bot_exclusions)  # Exclude bot contributors
            .select_related("contributor", "user_profile__user")
            .values(
                "contributor__name",
                "contributor__github_url",
                "contributor__avatar_url",
                "user_profile__user__username",
            )
            .annotate(total_prs=Count("id"))
            .order_by("-total_prs")[:10]
        )
        context["pr_leaderboard"] = pr_leaderboard

        # Code Review Leaderboard - Use reviewer_contributor
        # Dynamically filters for OWASP-BLT repos (will include any new BLT repos added to database)
        # Filter for reviews on PRs merged in the last 6 months
        # Create bot exclusion query for reviewers
        reviewer_bot_exclusions = Q()
        for bot in bots:
            reviewer_bot_exclusions |= Q(reviewer_contributor__name__icontains=bot)

        reviewed_pr_leaderboard = (
            GitHubReview.objects.filter(
                reviewer_contributor__isnull=False,
                pull_request__merged_at__gte=since_date,
            )
            .filter(
                Q(pull_request__repo__repo_url__startswith="https://github.com/OWASP-BLT/")
                | Q(pull_request__repo__repo_url__startswith="https://github.com/owasp-blt/")
            )
            .exclude(reviewer_bot_exclusions)  # Exclude bot reviewers
            .select_related("reviewer_contributor", "reviewer__user")
            .values(
                "reviewer_contributor__name",
                "reviewer_contributor__github_url",
                "reviewer_contributor__avatar_url",
                "reviewer__user__username",
            )
            .annotate(total_reviews=Count("id"))
            .order_by("-total_reviews")[:10]
        )
        context["code_review_leaderboard"] = reviewed_pr_leaderboard

        # Comment Leaderboard - Use commenter_contributor
        # Dynamically filters for OWASP-BLT repos (will include any new BLT repos added to database)
        # Filter for comments created in the last 6 months
        # Create bot exclusion query for commenters
        commenter_bot_exclusions = Q()
        for bot in bots:
            commenter_bot_exclusions |= Q(commenter_contributor__name__icontains=bot)

        from website.models import GitHubComment

        comment_leaderboard = (
            GitHubComment.objects.filter(
                commenter_contributor__isnull=False,
                created_at__gte=since_date,
            )
            .filter(
                Q(issue__repo__repo_url__startswith="https://github.com/OWASP-BLT/")
                | Q(issue__repo__repo_url__startswith="https://github.com/owasp-blt/")
            )
            .exclude(commenter_bot_exclusions)  # Exclude bot commenters
            .select_related("commenter_contributor", "commenter__user")
            .values(
                "commenter_contributor__name",
                "commenter_contributor__github_url",
                "commenter_contributor__avatar_url",
                "commenter__user__username",
            )
            .annotate(total_comments=Count("id"))
            .order_by("-total_comments")[:10]
        )
        context["comment_leaderboard"] = comment_leaderboard

        # Top visitors leaderboard
        top_visitors = (
            UserProfile.objects.select_related("user")
            .filter(daily_visit_count__gt=0)
            .order_by("-daily_visit_count")[:10]
        )

        context["top_visitors"] = top_visitors

        return context


class EachmonthLeaderboardView(LeaderboardBase, ListView):
    """
    Returns: Grouped user:score data in months for current year
    """

    model = User
    template_name = "leaderboard_eachmonth.html"

    def get_context_data(self, *args, **kwargs):
        context = super(EachmonthLeaderboardView, self).get_context_data(*args, **kwargs)

        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.filter(user=self.request.user).first()

        year = self.request.GET.get("year")

        if not year:
            year = timezone.now().year

        if isinstance(year, str) and not year.isdigit():
            raise Http404(f"Invalid query passed | Year:{year}")

        year = int(year)

        leaderboard = self.monthly_year_leaderboard(year)
        month_winners = []

        months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]

        for month_indx, usr in enumerate(leaderboard):
            month_winner = {"user": usr, "month": months[month_indx]}
            month_winners.append(month_winner)

        context["leaderboard"] = month_winners

        return context


class SpecificMonthLeaderboardView(LeaderboardBase, ListView):
    """
    Returns: leaderboard for filtered month and year requested in the query
    """

    model = User
    template_name = "leaderboard_specific_month.html"

    def get_context_data(self, *args, **kwargs):
        context = super(SpecificMonthLeaderboardView, self).get_context_data(*args, **kwargs)

        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.filter(user=self.request.user).first()

        month = self.request.GET.get("month")
        year = self.request.GET.get("year")

        if not month:
            month = timezone.now().month
        if not year:
            year = timezone.now().year

        if isinstance(month, str) and not month.isdigit():
            raise Http404(f"Invalid query passed | Month:{month}")
        if isinstance(year, str) and not year.isdigit():
            raise Http404(f"Invalid query passed | Year:{year}")

        month = int(month)
        year = int(year)

        if not (month >= 1 and month <= 12):
            raise Http404(f"Invalid query passed | Month:{month}")

        context["leaderboard"] = self.get_leaderboard(month, year, api=False)
        return context


class CustomObtainAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        response = super(CustomObtainAuthToken, self).post(request, *args, **kwargs)
        token = Token.objects.get(key=response.data["token"])
        return Response({"key": token.key, "id": token.user_id})


def invite_friend(request):
    if not request.user.is_authenticated:
        return redirect("account_login")
    current_site = get_current_site(request)
    referral_code, created = InviteFriend.objects.get_or_create(sender=request.user)
    referral_link = f"https://{current_site.domain}/referral/?ref={referral_code.referral_code}"
    context = {
        "referral_link": referral_link,
    }
    return render(request, "invite_friend.html", context)


def referral_signup(request):
    referral_token = request.GET.get("ref")
    if referral_token:
        try:
            invite = InviteFriend.objects.get(referral_code=referral_token)
            request.session["ref"] = referral_token
        except InviteFriend.DoesNotExist:
            messages.error(request, "Invalid referral token")
            return redirect("account_signup")
    return redirect("account_signup")


def contributors_view(request, *args, **kwargs):
    contributors_file_path = os.path.join(settings.BASE_DIR, "contributors.json")

    with open(contributors_file_path, "r", encoding="utf-8") as file:
        content = file.read()

    contributors = json.loads(content)

    contributor_id = request.GET.get("contributor", None)

    if contributor_id:
        contributor = None
        for i in contributors:
            if str(i["id"]) == contributor_id:
                contributor = i

        if contributor is None:
            return HttpResponseNotFound("Contributor not found")

        return render(request, "contributors_detail.html", context={"contributor": contributor})

    context = {"contributors": contributors}

    return render(request, "contributors.html", context=context)


def users_view(request, *args, **kwargs):
    context = {}

    # Get total count of users with GitHub profiles
    context["users_with_github_count"] = (
        UserProfile.objects.exclude(github_url="").exclude(github_url__isnull=True).count()
    )

    # Get contributors from database
    context["contributors"] = Contributor.objects.all().order_by("-contributions")
    context["contributors_count"] = context["contributors"].count()

    context["tags_with_counts"] = (
        Tag.objects.filter(userprofile__isnull=False).annotate(user_count=Count("userprofile")).order_by("-user_count")
    )

    tag_name = request.GET.get("tag")
    show_githubbers = request.GET.get("githubbers") == "true"
    show_contributors = request.GET.get("contributors") == "true"

    if show_contributors:
        context["show_contributors"] = True
        context["users"] = []
    elif show_githubbers:
        context["githubbers"] = True
        context["users"] = UserProfile.objects.exclude(github_url="").exclude(github_url__isnull=True)
        context["user_count"] = context["users"].count()
    elif tag_name:
        if context["tags_with_counts"].filter(name=tag_name).exists():
            context["tag"] = tag_name
            context["users"] = UserProfile.objects.filter(tags__name=tag_name)
            context["user_count"] = context["users"].count()
        else:
            context["users"] = UserProfile.objects.none()
            context["user_count"] = 0
    else:
        context["tag"] = "BLT Contributors"
        context["users"] = UserProfile.objects.filter(tags__name="BLT Contributors")
        context["user_count"] = context["users"].count()

    return render(request, "users.html", context=context)


def contributors(request):
    contributors_file_path = os.path.join(settings.BASE_DIR, "contributors.json")

    with open(contributors_file_path, "r", encoding="utf-8", errors="replace") as file:
        content = file.read()

    contributors_data = json.loads(content)
    return JsonResponse({"contributors": contributors_data})


def contributor_stats_view(request):
    """
    Weekly Activity view that highlights streak and challenge completions.
    This view displays contributor statistics with enhanced highlights for user achievements.
    """
    from datetime import timedelta

    from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

    # Calculate the date range for the current week
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=7)

    # Get time period from request (defaulting to current week)
    time_period = request.GET.get("period", "current_week")
    page_number = request.GET.get("page", 1)

    # Define time periods
    if time_period == "today":
        start_date = end_date
    elif time_period == "current_week":
        start_date = end_date - timedelta(days=7)
    elif time_period == "current_month":
        start_date = end_date.replace(day=1)
    elif time_period == "last_month":
        if end_date.month == 1:
            start_date = end_date.replace(year=end_date.year - 1, month=12, day=1)
        else:
            start_date = end_date.replace(month=end_date.month - 1, day=1)

    # Get user profiles with recent activity and streak/challenge data
    user_profiles = (
        UserProfile.objects.select_related("user")
        .filter(user__is_active=True)
        .prefetch_related("user__user_challenges", "user__points_set")
    )

    # Get recent streak achievements (users who reached milestone streaks this week)
    streak_highlights = []
    for profile in user_profiles:
        if profile.current_streak > 0:
            # Check if they reached a milestone streak recently
            milestone_achieved = None
            if profile.current_streak == 7:
                milestone_achieved = "7-day streak achieved!"
            elif profile.current_streak == 15:
                milestone_achieved = "15-day streak achieved!"
            elif profile.current_streak == 30:
                milestone_achieved = "30-day streak achieved!"
            elif profile.current_streak == 100:
                milestone_achieved = "100-day streak achieved!"
            elif profile.current_streak == 180:
                milestone_achieved = "180-day streak achieved!"
            elif profile.current_streak == 365:
                milestone_achieved = "365-day streak achieved!"

            if milestone_achieved:
                streak_highlights.append(
                    {
                        "user": profile.user,
                        "current_streak": profile.current_streak,
                        "longest_streak": profile.longest_streak,
                        "milestone": milestone_achieved,
                        "user_profile": profile,
                    }
                )

    # Get recent challenge completions from the past week
    completed_challenges = (
        Challenge.objects.filter(completed=True, completed_at__gte=start_date, completed_at__lte=end_date)
        .select_related()
        .prefetch_related("participants")
    )

    challenge_highlights = []
    for challenge in completed_challenges:
        for participant in challenge.participants.all():
            challenge_highlights.append(
                {
                    "user": participant,
                    "challenge": challenge,
                    "completed_at": challenge.completed_at,
                    "points_earned": challenge.points,
                }
            )

    # Get contributor stats for the time period
    contributor_stats = []
    try:
        # Get aggregated stats for the time period
        stats_query = (
            ContributorStats.objects.filter(date__gte=start_date, date__lte=end_date)
            .values("contributor")
            .annotate(
                total_commits=Sum("commits"),
                total_issues_opened=Sum("issues_opened"),
                total_issues_closed=Sum("issues_closed"),
                total_prs=Sum("pull_requests"),
                total_comments=Sum("comments"),
            )
            .order_by("-total_commits")
        )
        contributor_ids = [s["contributor"] for s in stats_query]

        contributors = Contributor.objects.in_bulk(contributor_ids)

        for stat in stats_query:
            contributor = contributors.get(stat["contributor"])
            if not contributor:
                continue

            # Calculate impact score
            impact_score = (
                stat["total_commits"] * 5
                + stat["total_prs"] * 3
                + stat["total_issues_opened"] * 2
                + stat["total_issues_closed"] * 2
                + stat["total_comments"]
            )

            # Determine impact level
            if impact_score > 200:
                impact_level = {"class": "bg-green-100 text-green-800", "text": "High Impact"}
            elif impact_score > 100:
                impact_level = {"class": "bg-yellow-100 text-yellow-800", "text": "Medium Impact"}
            else:
                impact_level = {"class": "bg-blue-100 text-blue-800", "text": "Growing Impact"}

            contributor_stats.append(
                {
                    "contributor": contributor,
                    "commits": stat["total_commits"] or 0,
                    "issues_opened": stat["total_issues_opened"] or 0,
                    "issues_closed": stat["total_issues_closed"] or 0,
                    "pull_requests": stat["total_prs"] or 0,
                    "comments": stat["total_comments"] or 0,
                    "impact_score": impact_score,
                    "impact_level": impact_level,
                }
            )
    except Exception as e:
        logger.error(f"Error fetching contributor stats: {e}")

    # Sort by impact score
    contributor_stats.sort(key=lambda x: x["impact_score"], reverse=True)

    # Paginate contributor stats
    paginator = Paginator(contributor_stats, 10)
    try:
        paginated_stats = paginator.page(page_number)
    except PageNotAnInteger:
        paginated_stats = paginator.page(1)
    except EmptyPage:
        paginated_stats = paginator.page(paginator.num_pages)

    # Get weekly leaderboard - top users by points earned in the time period
    leaderboard = []

    try:
        leaderboard_query = (
            Points.objects.filter(created__gte=start_date, created__lte=end_date)
            .values("user")
            .annotate(total_points=Sum("score"))
            .order_by("-total_points")[:10]
        )

        user_ids = [entry["user"] for entry in leaderboard_query]

        users = User.objects.in_bulk(user_ids)
        profiles = {p.user_id: p for p in UserProfile.objects.filter(user_id__in=user_ids)}

        for entry in leaderboard_query:
            user_id = entry["user"]

            user = users.get(user_id)
            user_profile = profiles.get(user_id)

            if not user or not user_profile:
                continue

            leaderboard.append(
                {
                    "user": user,
                    "user_profile": user_profile,
                    "total_points": entry["total_points"],
                }
            )

    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")

    # Prepare time period options
    time_period_options = [
        ("today", "Today's Data"),
        ("current_week", "Current Week"),
        ("current_month", "Current Month"),
        ("last_month", "Last Month"),
    ]

    context = {
        "contributor_stats": paginated_stats,
        "page_obj": paginated_stats,
        "paginator": paginator,
        "is_paginated": paginator.num_pages > 1,
        "time_period": time_period,
        "time_period_options": time_period_options,
        "start_date": start_date,
        "end_date": end_date,
        "streak_highlights": streak_highlights,
        "challenge_highlights": challenge_highlights,
        "total_streak_achievements": len(streak_highlights),
        "total_challenge_completions": len(challenge_highlights),
        "leaderboard": leaderboard,
    }

    return render(request, "weekly_activity.html", context)


@login_required
def create_wallet(request):
    if not request.user.is_staff:
        return JsonResponse({"error": "Unauthorized"}, status=403)
    existing_wallet_user_ids = Wallet.objects.values_list("user_id", flat=True)
    users_without_wallets = User.objects.exclude(id__in=existing_wallet_user_ids)
    wallets_to_create = [Wallet(user=user) for user in users_without_wallets]
    Wallet.objects.bulk_create(wallets_to_create)
    return JsonResponse(f"Created {len(wallets_to_create)} wallets", safe=False)


def create_tokens(request):
    for user in User.objects.all():
        Token.objects.get_or_create(user=user)
    return JsonResponse("Created", safe=False)


def get_score(request):
    # Annotate scores and evaluate queryset eagerly for batch profile fetch
    temp_users = list(
        User.objects.annotate(total_score=Sum("points__score")).filter(total_score__gt=0).order_by("-total_score")
    )
    # Batch-fetch profiles without triggering AutoOneToOneField auto-creation
    profiles_map = {p.user_id: p for p in UserProfile.objects.filter(user__in=temp_users)}

    users = []
    for rank, user in enumerate(temp_users, start=1):
        profile = profiles_map.get(user.id)
        users.append(
            {
                "rank": rank,
                "id": user.id,
                "User": user.username,
                "score": {"total_score": user.total_score},
                "image": {"user_avatar": profile.user_avatar if profile else ""},
                "title_type": {"title": profile.title if profile else 0},
                "follows": {"follows": profile.follows.count() if profile else 0},
                "savedissue": {"issue_saved": profile.issue_saved.count() if profile else 0},
            }
        )
    return JsonResponse(users, safe=False)


@login_required(login_url="/accounts/login")
def follow_user(request, user):
    if request.method != "GET":
        return HttpResponse(status=405)

    userx = get_object_or_404(User, username=user)

    profile = request.user.userprofile
    target_profile = userx.userprofile

    # Toggle follow / unfollow
    if profile.follows.filter(id=target_profile.id).exists():
        profile.follows.remove(target_profile)
    else:
        profile.follows.add(target_profile)

        context = {
            "follower": request.user,
            "followed": userx,
        }

        msg_plain = render_to_string("email/follow_user.html", context)
        msg_html = render_to_string("email/follow_user.html", context)

        send_mail(
            "You got a new follower!!",
            msg_plain,
            settings.EMAIL_TO_STRING,
            [userx.email],
            html_message=msg_html,
        )

    return HttpResponse("Success")


# get issue and comment id from url
def monitor_create_view(request):
    if request.method == "POST":
        form = MonitorForm(request.POST)
        if form.is_valid():
            monitor = form.save(commit=False)
            monitor.user = request.user
            monitor.save()
    else:
        form = MonitorForm()
    return render(request, "Moniter.html", {"form": form})


def reward_sender_with_points(sender):
    points, created = Points.objects.get_or_create(user=sender, defaults={"score": 0})
    points.score += 2
    points.save()


@login_required
def deletions(request):
    if request.method == "POST":
        form = MonitorForm(request.POST)
        if form.is_valid():
            monitor = form.save(commit=False)
            monitor.user = request.user
            monitor.save()
            messages.success(request, "Form submitted successfully!")
        else:
            messages.error(request, "Form submission failed. Please correct the errors.")
    else:
        form = MonitorForm()

    return render(
        request,
        "monitor.html",
        {"form": form, "monitors": Monitor.objects.filter(user=request.user)},
    )


def profile(request):
    try:
        return redirect("/profile/" + request.user.username)
    except Exception:
        return redirect("/")


@login_required
def assign_badge(request, username):
    if not UserBadge.objects.filter(user=request.user, badge__title="Mentor").exists():
        messages.error(request, "You don't have permission to assign badges.")
        return redirect("profile", slug=username)

    user = get_object_or_404(get_user_model(), username=username)
    badge_id = request.POST.get("badge")
    reason = request.POST.get("reason", "")
    badge = get_object_or_404(Badge, id=badge_id)

    # Check if the user already has this badge
    if UserBadge.objects.filter(user=user, badge=badge).exists():
        messages.warning(request, "This user already has this badge.")
        return redirect("profile", slug=username)

    # Assign the badge to user
    UserBadge.objects.create(user=user, badge=badge, awarded_by=request.user, reason=reason)
    messages.success(request, f"{badge.title} badge assigned to {user.username}.")
    return redirect("profile", slug=username)


def badge_user_list(request, badge_id):
    badge = get_object_or_404(Badge, id=badge_id)

    profiles = (
        UserProfile.objects.filter(user__userbadge__badge=badge)
        .select_related("user")
        .distinct()
        .annotate(awarded_at=F("user__userbadge__awarded_at"))
        .order_by("-awarded_at")
    )

    return render(
        request,
        "badge_user_list.html",
        {
            "badge": badge,
            "profiles": profiles,
        },
    )


def validate_github_signature(payload_body: bytes, signature_header: str | None) -> bool:
    """
    Validate GitHub webhook signature using HMAC-SHA256.

    - payload_body: raw request.body (bytes)
    - signature_header: value of X-Hub-Signature-256 from GitHub
      e.g. "sha256=abc123..."
    """
    if not signature_header:
        logger.warning("Missing X-Hub-Signature-256 header")
        return False

    secret = settings.GITHUB_WEBHOOK_SECRET
    if not secret:
        logger.warning("GITHUB_WEBHOOK_SECRET is not set")
        return False

    expected = (
        "sha256="
        + hmac.new(
            secret.encode("utf-8"),
            payload_body,
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(expected, signature_header)


def safe_parse_github_datetime(value, *, default=None, field_name=""):
    """
    Safely parse a GitHub timestamp string into a datetime.

    Returns `default` if the value is empty or malformed, and logs a warning
    instead of letting ParserError crash the webhook handler.
    """
    if not value:
        return default
    try:
        return dateutil_parser.parse(value)
    except (ParserError, ValueError, TypeError, OverflowError) as exc:
        logger.warning(
            "Failed to parse GitHub datetime for %s: %r (%s)",
            field_name,
            value,
            exc,
        )
        return default


@csrf_exempt
def github_webhook(request):
    """
    Entry point for GitHub webhooks.

    Validates the HMAC signature (X-Hub-Signature-256), parses the JSON payload,
    routes the event to the appropriate handler based on X-GitHub-Event,
    and returns a JSON response indicating success or error.
    """
    if request.method == "POST":
        # Fail closed if secret is not configured
        if not getattr(settings, "GITHUB_WEBHOOK_SECRET", None):
            logger.error("GITHUB_WEBHOOK_SECRET is not configured; refusing webhook request.")
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Webhook secret not configured",
                },
                status=503,
            )

        signature = request.headers.get("X-Hub-Signature-256")

        if not validate_github_signature(request.body, signature):
            return JsonResponse(
                {"status": "error", "message": "Unauthorized request"},
                status=403,
            )

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"status": "error", "message": "Invalid JSON payload"},
                status=400,
            )

        event_type = request.headers.get("X-GitHub-Event", "")

        event_handlers = {
            "pull_request": handle_pull_request_event,
            "push": handle_push_event,
            "pull_request_review": handle_review_event,
            "issues": handle_issue_event,
            "issue_comment": handle_comment_event,
            "pull_request_review_comment": handle_comment_event,
            "status": handle_status_event,
            "fork": handle_fork_event,
            "create": handle_create_event,
        }

        handler = event_handlers.get(event_type)
        if handler:
            return handler(payload)
        else:
            return JsonResponse(
                {"status": "error", "message": "Unhandled event type"},
                status=400,
            )
    else:
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=400)


def handle_pull_request_event(payload):
    """
    Handle GitHub pull_request events.

    Persists pull request lifecycle data into GitHubIssue for repositories
    tracked in the BLT database. Supports key actions such as opened, closed,
    reopened, edited, and synchronize, updating fields like state, merged flag,
    merged_at/closed_at timestamps, linked repo, user_profile and contributor.
    Also preserves existing badge assignment behaviour for merged PRs.
    """
    action = payload.get("action")
    pr_data = payload.get("pull_request") or {}
    repo_data = payload.get("repository") or {}

    logger.debug(f"GitHub pull_request event: {action}")

    # Only care about main lifecycle actions; ignore label/assigned/etc.
    if action not in {"opened", "closed", "reopened", "edited", "synchronize"}:
        return JsonResponse({"status": "ignored", "action": action}, status=200)

    # --- PR basic fields ---
    # Use GitHub's global PR ID for GitHubIssue.issue_id (avoids clash with issues)
    pr_global_id = pr_data.get("id")  # big integer, globally unique per PR
    pr_number = pr_data.get("number")  # visible PR number (#123)
    pr_state = pr_data.get("state") or "open"  # "open" / "closed"
    pr_html_url = pr_data.get("html_url") or ""
    pr_title = pr_data.get("title") or ""
    pr_body = pr_data.get("body") or ""
    is_merged = bool(pr_data.get("merged", False))

    # --- PR author / user mapping ---
    pr_user = pr_data.get("user") or {}
    pr_user_html_url = pr_user.get("html_url")
    pr_user_profile = None
    if pr_user_html_url:
        # Same pattern as other handlers (push, review, status, etc.)
        pr_user_profile = UserProfile.objects.filter(github_url=pr_user_html_url).first()

    # contributor mapping for PR leaderboard
    contributor = None
    gh_login = pr_user.get("login")
    gh_avatar = pr_user.get("avatar_url")
    gh_github_url = pr_user_html_url
    gh_id = pr_user.get("id")  # GitHub user ID (preferred unique key)

    try:
        if gh_id is not None:
            # Primary: use github_id as the unique identifier
            contributor, _ = Contributor.objects.get_or_create(
                github_id=gh_id,
                defaults={
                    "github_url": gh_github_url or "",
                    "name": gh_login or extract_github_username(gh_github_url) or "",
                    "avatar_url": gh_avatar or "",
                    "contributor_type": "User",
                    "contributions": 0,
                },
            )
        elif gh_github_url:
            # Fallback: try to find existing contributor by URL, but don't create
            # without github_id, since it's a required unique field
            contributor = Contributor.objects.filter(github_url=gh_github_url).first()

    except Exception as e:
        logger.error(f"Error getting/creating Contributor for PR: {e}")
        contributor = None

    # --- Timestamps (using same style as handle_issue_event) ---
    created_at = safe_parse_github_datetime(
        pr_data.get("created_at"),
        default=timezone.now(),
        field_name="pull_request.created_at",
    )
    updated_at = safe_parse_github_datetime(
        pr_data.get("updated_at"),
        default=timezone.now(),
        field_name="pull_request.updated_at",
    )
    closed_at = safe_parse_github_datetime(
        pr_data.get("closed_at"),
        default=None,
        field_name="pull_request.closed_at",
    )
    merged_at = safe_parse_github_datetime(
        pr_data.get("merged_at"),
        default=None,
        field_name="pull_request.merged_at",
    )

    # --- Repo mapping (same style as handle_issue_event) ---
    repo_html_url = repo_data.get("html_url")
    repo_full_name = repo_data.get("full_name")  # "owner/repo" (for logging only)

    if not pr_global_id or not repo_html_url:
        logger.warning("Pull request event missing required data (id or repo_html_url)")
        return JsonResponse({"status": "error", "message": "Missing required data"}, status=400)

    repo = None
    try:
        repo = Repo.objects.get(repo_url=repo_html_url)
    except Repo.DoesNotExist:
        logger.info(f"Repository not found in BLT for PR: {repo_html_url}")
        # Not an error: we only track PRs for repos that exist in our DB
    except Exception as e:
        logger.error(f"Error finding repository for PR: {e}")

    if repo:
        # --- Upsert GitHubIssue row for this PR ---
        try:
            github_issue, created = GitHubIssue.objects.update_or_create(
                issue_id=pr_global_id,  # unique per PR (avoids clash with issues)
                repo=repo,
                defaults={
                    "type": "pull_request",
                    "title": pr_title,
                    "body": pr_body,
                    "state": pr_state,
                    "url": pr_html_url,
                    "is_merged": is_merged,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "closed_at": closed_at,
                    "merged_at": merged_at if is_merged else None,
                    "user_profile": pr_user_profile,
                    "contributor": contributor,
                    # has_dollar_tag, sponsors_tx_id, p2p_* left untouched
                },
            )

            logger.info(
                f"{'Created' if created else 'Updated'} GitHubIssue PR #{pr_number} "
                f"(id={pr_global_id}) in repo {repo_full_name} | "
                f"state={pr_state} merged={is_merged}"
            )
        except Exception as e:
            logger.error(f"Error creating/updating GitHubIssue for PR #{pr_number}: {e}")

    # --- Badge logic (preserve existing behaviour) ---
    if action == "closed" and is_merged and pr_user_profile:
        pr_user_instance = pr_user_profile.user
        assign_github_badge(pr_user_instance, "First PR Merged")

    return JsonResponse({"status": "success"}, status=200)


def handle_push_event(payload):
    pusher_profile = UserProfile.objects.filter(github_url=payload["sender"]["html_url"]).first()
    if pusher_profile:
        pusher_user = pusher_profile.user
        if payload.get("commits"):
            assign_github_badge(pusher_user, "First Commit")
    return JsonResponse({"status": "success"}, status=200)


def handle_review_event(payload):
    reviewer_profile = UserProfile.objects.filter(github_url=payload["sender"]["html_url"]).first()
    if reviewer_profile:
        reviewer_user = reviewer_profile.user
        assign_github_badge(reviewer_user, "First Code Review")
    return JsonResponse({"status": "success"}, status=200)


def handle_issue_event(payload):
    """
    Handle GitHub issue events (opened, closed, etc.)
    Updates GitHubIssue records in BLT to match GitHub issue state
    """
    action = payload.get("action")
    issue_data = payload.get("issue", {})
    repo_data = payload.get("repository", {})

    logger.debug(f"GitHub issue event: {action}")

    # Extract issue details
    issue_id = issue_data.get("number")
    issue_state = issue_data.get("state")
    issue_html_url = issue_data.get("html_url")

    # Extract repository details
    repo_full_name = repo_data.get("full_name")  # e.g., "owner/repo"
    repo_html_url = repo_data.get("html_url")

    if not issue_id or not repo_html_url:
        logger.warning("Issue event missing required data")
        return JsonResponse({"status": "error", "message": "Missing required data"}, status=400)

    # Find the Repo in BLT database
    try:
        repo = Repo.objects.get(repo_url=repo_html_url)
    except Repo.DoesNotExist:
        logger.info(f"Repository not found in BLT: {repo_html_url}")
        # Not an error - we only track issues for repos we have in our database
        # Continue to badge assignment
    except Exception as e:
        logger.error(f"Error finding repository: {e}")
        # Continue to badge assignment
    else:
        # Find and update the GitHubIssue record
        try:
            github_issue = GitHubIssue.objects.get(issue_id=issue_id, repo=repo, type="issue")

            # Update the issue state
            github_issue.state = issue_state

            # Update closed_at timestamp if the issue was closed
            if action == "closed" and issue_data.get("closed_at"):
                github_issue.closed_at = dateutil_parser.parse(issue_data["closed_at"])

            # Update updated_at timestamp
            if issue_data.get("updated_at"):
                github_issue.updated_at = dateutil_parser.parse(issue_data["updated_at"])

            github_issue.save()
            logger.info(f"Updated GitHubIssue {issue_id} in repo {repo_full_name} to state: {issue_state}")
        except GitHubIssue.DoesNotExist:
            logger.info(f"GitHubIssue {issue_id} not found in BLT for repo {repo_full_name}")
            # Not an error - we may not have all issues in our database
        except Exception as e:
            logger.error(f"Error updating GitHubIssue: {e}")

    # Assign badge for first issue closed (existing functionality)
    if action == "closed":
        closer_profile = UserProfile.objects.filter(github_url=payload["sender"]["html_url"]).first()
        if closer_profile:
            closer_user = closer_profile.user
            assign_github_badge(closer_user, "First Issue Closed")

    return JsonResponse({"status": "success"}, status=200)


def handle_comment_event(payload):
    """
    Handle GitHub issue_comment and pull_request_review_comment events.

    Tracks comments made on issues and pull requests for the comment leaderboard.
    Filters out bot comments and stores comment data in GitHubComment model.
    """
    from website.models import GitHubComment

    action = payload.get("action")
    comment_data = payload.get("comment", {})
    issue_data = payload.get("issue") or payload.get("pull_request") or {}
    repo_data = payload.get("repository", {})

    logger.debug(f"GitHub comment event: {action}")

    # Only track created comments (not edited or deleted)
    if action != "created":
        return JsonResponse({"status": "ignored", "action": action}, status=200)

    # Extract comment details
    comment_id = comment_data.get("id")
    comment_body = comment_data.get("body", "")
    comment_url = comment_data.get("html_url", "")
    comment_created_at = safe_parse_github_datetime(
        comment_data.get("created_at"),
        default=timezone.now(),
        field_name="comment.created_at",
    )
    comment_updated_at = safe_parse_github_datetime(
        comment_data.get("updated_at"),
        default=timezone.now(),
        field_name="comment.updated_at",
    )

    # Extract commenter details
    commenter_data = comment_data.get("user", {})
    commenter_login = commenter_data.get("login", "")
    commenter_github_url = commenter_data.get("html_url", "")
    commenter_avatar_url = commenter_data.get("avatar_url", "")
    commenter_type = commenter_data.get("type", "User")
    commenter_github_id = commenter_data.get("id")

    # Filter out bot comments
    if (
        commenter_type == "Bot"
        or commenter_login.endswith("[bot]")
        or any(bot in commenter_login.lower() for bot in ["copilot", "dependabot", "github-actions", "renovate"])
    ):
        logger.debug(f"Ignoring bot comment from {commenter_login}")
        return JsonResponse({"status": "ignored", "reason": "bot comment"}, status=200)

    # Extract issue/PR details
    issue_number = issue_data.get("number")
    issue_global_id = issue_data.get("id")
    repo_html_url = repo_data.get("html_url")
    repo_full_name = repo_data.get("full_name")

    if not all([comment_id, issue_global_id, repo_html_url]):
        logger.warning("Comment event missing required data")
        return JsonResponse({"status": "error", "message": "Missing required data"}, status=400)

    # Find the Repo in BLT database
    try:
        repo = Repo.objects.get(repo_url=repo_html_url)
    except Repo.DoesNotExist:
        logger.info(f"Repository not found in BLT for comment: {repo_html_url}")
        # Not an error: we only track comments for repos that exist in our DB
        return JsonResponse({"status": "success", "message": "Repository not tracked"}, status=200)
    except Exception as e:
        logger.error(f"Error finding repository for comment: {e}")
        return JsonResponse({"status": "error", "message": "Database error"}, status=500)

    # Find the GitHubIssue in BLT database
    try:
        github_issue = GitHubIssue.objects.get(issue_id=issue_global_id, repo=repo)
    except GitHubIssue.DoesNotExist:
        logger.info(f"GitHub issue/PR {issue_number} not found in BLT for repo {repo_full_name}")
        # Not an error: we may not have all issues/PRs in our database
        return JsonResponse({"status": "success", "message": "Issue/PR not tracked"}, status=200)
    except Exception as e:
        logger.error(f"Error finding GitHub issue for comment: {e}")
        return JsonResponse({"status": "error", "message": "Database error"}, status=500)

    # Map commenter to UserProfile
    commenter_user_profile = None
    if commenter_github_url:
        commenter_user_profile = UserProfile.objects.filter(github_url=commenter_github_url).first()

    # Map commenter to Contributor
    commenter_contributor = None
    if commenter_github_id:
        try:
            commenter_contributor, created = Contributor.objects.get_or_create(
                github_id=commenter_github_id,
                defaults={
                    "name": commenter_login,
                    "github_url": commenter_github_url,
                    "avatar_url": commenter_avatar_url,
                    "contributor_type": commenter_type,
                    "contributions": 1,
                },
            )
            if not created:
                # Update existing contributor data
                commenter_contributor.name = commenter_login
                commenter_contributor.github_url = commenter_github_url
                commenter_contributor.avatar_url = commenter_avatar_url
                commenter_contributor.contributions += 1
                commenter_contributor.save()
        except Exception as e:
            logger.error(f"Error creating/updating contributor for comment: {e}")

    # Create or update the GitHubComment record
    try:
        github_comment, created = GitHubComment.objects.update_or_create(
            comment_id=comment_id,
            defaults={
                "issue": github_issue,
                "commenter": commenter_user_profile,
                "commenter_contributor": commenter_contributor,
                "body": comment_body,
                "created_at": comment_created_at,
                "updated_at": comment_updated_at,
                "url": comment_url,
            },
        )

        action_taken = "Created" if created else "Updated"
        logger.info(
            f"{action_taken} GitHubComment {comment_id} by {commenter_login} "
            f"on {github_issue.type} #{issue_number} in repo {repo_full_name}"
        )

    except Exception as e:
        logger.error(f"Error creating/updating GitHubComment: {e}")
        return JsonResponse({"status": "error", "message": "Failed to save comment"}, status=500)

    return JsonResponse({"status": "success"}, status=200)


def handle_status_event(payload):
    user_profile = UserProfile.objects.filter(github_url=payload["sender"]["html_url"]).first()
    if user_profile:
        user = user_profile.user
        build_status = payload["state"]
        if build_status == "success":
            assign_github_badge(user, "First CI Build Passed")
        elif build_status == "failure":
            assign_github_badge(user, "First CI Build Failed")
    return JsonResponse({"status": "success"}, status=200)


def handle_fork_event(payload):
    user_profile = UserProfile.objects.filter(github_url=payload["sender"]["html_url"]).first()
    if user_profile:
        user = user_profile.user
        assign_github_badge(user, "First Fork Created")
    return JsonResponse({"status": "success"}, status=200)


def handle_create_event(payload):
    if payload["ref_type"] == "branch":
        user_profile = UserProfile.objects.filter(github_url=payload["sender"]["html_url"]).first()
        if user_profile:
            user = user_profile.user
            assign_github_badge(user, "First Branch Created")
    return JsonResponse({"status": "success"}, status=200)


def assign_github_badge(user, action_title):
    try:
        badge, created = Badge.objects.get_or_create(title=action_title, type="automatic")
        if not UserBadge.objects.filter(user=user, badge=badge).exists():
            UserBadge.objects.create(user=user, badge=badge)

    except Badge.DoesNotExist:
        logger.warning(f"Badge '{action_title}' does not exist.")


@method_decorator(login_required, name="dispatch")
class UserChallengeListView(View):
    """View to display all challenges and handle updates inline."""

    def get(self, request):
        challenges = Challenge.objects.filter(challenge_type="single")  # All single-user challenges
        user_challenges = challenges.filter(participants=request.user)  # Challenges the user is participating in

        for challenge in challenges:
            if challenge in user_challenges:
                # If the user is participating, show their progress
                challenge.progress = challenge.progress
            else:
                # If the user is not participating, set progress to 0
                challenge.progress = 0

            # Calculate the progress circle offset (same as team challenges)
            circumference = 125.6
            challenge.stroke_dasharray = circumference
            challenge.stroke_dashoffset = circumference - (circumference * challenge.progress / 100)

        return render(
            request,
            "user_challenges.html",
            {"challenges": challenges, "user_challenges": user_challenges},
        )

    def post(self, request):
        """Handle manual challenge progress updates"""
        import json

        from django.http import JsonResponse

        try:
            data = json.loads(request.body)
            challenge_id = data.get("challenge_id")
            action = data.get("action")  # 'join', 'update_progress', 'complete'
            progress_value = data.get("progress", 0)

            challenge = get_object_or_404(Challenge, id=challenge_id, challenge_type="single")

            if action == "join":
                # Add user to challenge participants
                if request.user not in challenge.participants.all():
                    challenge.participants.add(request.user)
                return JsonResponse({"success": True, "message": "Joined challenge successfully!"})

            elif action == "update_progress":
                # Update progress manually
                if request.user not in challenge.participants.all():
                    challenge.participants.add(request.user)

                # Ensure progress is between 0 and 100
                progress_value = max(0, min(100, int(progress_value)))
                challenge.progress = progress_value
                challenge.save()

                # Check if challenge is now completed
                if progress_value == 100 and not challenge.completed:
                    challenge.completed = True
                    challenge.completed_at = timezone.now()
                    challenge.save()

                    # Award points and BACON
                    Points.objects.create(
                        user=request.user, score=challenge.points, reason=f"Completed '{challenge.title}' challenge"
                    )

                    from website.feed_signals import giveBacon

                    giveBacon(request.user, amt=challenge.bacon_reward)

                    # Handle staking pool completion
                    from website.challenge_signals import handle_staking_pool_completion

                    handle_staking_pool_completion(request.user, challenge)

                    return JsonResponse(
                        {
                            "success": True,
                            "message": f"Challenge completed! Earned {challenge.points} points and {challenge.bacon_reward} BACON tokens!",
                            "completed": True,
                        }
                    )

                return JsonResponse({"success": True, "message": "Progress updated successfully!"})

            elif action == "complete":
                # Mark challenge as 100% complete
                if request.user not in challenge.participants.all():
                    challenge.participants.add(request.user)

                if not challenge.completed:
                    challenge.progress = 100
                    challenge.completed = True
                    challenge.completed_at = timezone.now()
                    challenge.save()

                    # Award points and BACON
                    Points.objects.create(
                        user=request.user, score=challenge.points, reason=f"Completed '{challenge.title}' challenge"
                    )

                    from website.feed_signals import giveBacon

                    giveBacon(request.user, amt=challenge.bacon_reward)

                    # Handle staking pool completion
                    from website.challenge_signals import handle_staking_pool_completion

                    handle_staking_pool_completion(request.user, challenge)

                    return JsonResponse(
                        {
                            "success": True,
                            "message": f"Challenge completed! Earned {challenge.points} points and {challenge.bacon_reward} BACON tokens!",
                            "completed": True,
                        }
                    )
                else:
                    return JsonResponse({"success": False, "message": "Challenge already completed!"})

            return JsonResponse({"success": False, "message": "Invalid action"})

        except Exception as e:
            return JsonResponse({"success": False, "message": "An error occurred while updating the challenge"})


@login_required
def messaging_home(request):
    threads = Thread.objects.filter(participants=request.user).order_by("-updated_at")
    return render(request, "messaging.html", {"threads": threads})


def start_thread(request, user_id):
    if request.method == "POST":
        other_user = get_object_or_404(User, id=user_id)

        # Check if a thread already exists between the two users
        thread = Thread.objects.filter(participants=request.user).filter(participants=other_user).first()

        # Flag if this is a new thread (for sending email)
        is_new_thread = not thread

        if not thread:
            # Create a new thread
            thread = Thread.objects.create()
            thread.participants.set([request.user, other_user])  # Use set() for ManyToManyField

            # Send email notification to the recipient for new thread
            if other_user.email:
                subject = f"New encrypted chat from {request.user.username} on OWASP BLT"
                chat_url = request.build_absolute_uri(reverse("messaging"))

                # Create context for the email template
                context = {
                    "sender_username": request.user.username,
                    "recipient_username": other_user.username,
                    "chat_url": chat_url,
                }

                # Render the email content
                msg_plain = render_to_string("email/new_chat.html", context)
                msg_html = render_to_string("email/new_chat.html", context)

                # Send the email
                send_mail(
                    subject,
                    msg_plain,
                    settings.EMAIL_TO_STRING,
                    [other_user.email],
                    html_message=msg_html,
                )

        return JsonResponse({"success": True, "thread_id": thread.id})

    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)


@login_required
def view_thread(request, thread_id):
    thread = get_object_or_404(Thread, id=thread_id)
    messages = thread.messages.all().order_by("timestamp")
    # Convert the QuerySet to a list of dictionaries using values()
    data = list(messages.values("username", "content", "timestamp"))
    return JsonResponse(data, safe=False)


@login_required
def delete_thread(request, thread_id):
    if request.method == "POST":
        try:
            thread = Thread.objects.get(id=thread_id)
            # Check if user is a participant
            if request.user in thread.participants.all():
                thread.delete()
                return JsonResponse({"status": "success"})
            return JsonResponse({"status": "error", "message": "Unauthorized"}, status=403)
        except Thread.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Thread not found"}, status=404)
    return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)


@login_required
@require_http_methods(["GET"])
def get_public_key(request, thread_id):
    # Get the thread
    thread = get_object_or_404(Thread, id=thread_id)

    # Get the other participant in the thread (exclude the logged-in user)
    other_participants = thread.participants.exclude(id=request.user.id)
    if not other_participants.exists():
        return JsonResponse({"error": "No other participant found"}, status=404)

    other_user = other_participants.first()
    # Access the public_key from the UserProfile
    try:
        public_key = other_user.userprofile.public_key
    except Exception:
        return JsonResponse({"error": "User profile not found"}, status=404)

    if not public_key:
        return JsonResponse({"error": "User has not provided a public key"}, status=404)

    return JsonResponse({"public_key": public_key})


@login_required
@require_http_methods(["POST"])
def set_public_key(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    public_key = data.get("public_key")
    if not public_key:
        return JsonResponse({"error": "Public key is required"}, status=400)

    # Update the public_key on the user's profile
    profile = request.user.userprofile
    profile.public_key = public_key
    profile.save()

    return JsonResponse({"success": True, "public_key": profile.public_key})


@login_required
def fetch_notifications(request):
    notifications = Notification.objects.filter(user=request.user, is_deleted=False).order_by("is_read", "-created_at")

    notifications_data = [
        {
            "id": notification.id,
            "message": notification.message,
            "created_at": notification.created_at,
            "is_read": notification.is_read,
            "notification_type": notification.notification_type,
            "link": notification.link,
        }
        for notification in notifications
    ]

    return JsonResponse({"notifications": notifications_data}, safe=False)


@login_required
def mark_as_read(request):
    if request.method == "PATCH":
        try:
            if request.body and request.content_type == "application/json":
                try:
                    json.loads(request.body)
                except json.JSONDecodeError:
                    return JsonResponse({"status": "error", "message": "Invalid JSON in request body"}, status=400)

            notifications = Notification.objects.filter(user=request.user, is_read=False)
            notifications.update(is_read=True)
            return JsonResponse({"status": "success"})
        except Exception as e:
            logger.error(f"Error marking notifications as read: {e}")
            return JsonResponse(
                {"status": "error", "message": "An error occurred while marking notifications as read"}, status=400
            )


@login_required
def delete_notification(request, notification_id):
    if request.method == "DELETE":
        try:
            notification = get_object_or_404(Notification, id=notification_id, user=request.user)

            notification.is_deleted = True
            notification.save()

            return JsonResponse({"status": "success", "message": "Notification deleted successfully"})
        except Exception as e:
            logger.error(f"Error deleting notification: {e}")
            return JsonResponse(
                {"status": "error", "message": "An error occurred while deleting notification, please try again."},
                status=400,
            )
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)


@ratelimit(key="user", rate="10/m", method="POST")
@login_required
@require_POST
def toggle_follow(request, username):
    """Toggle follow/unfollow for a user (HTMX + non-HTMX safe)"""

    target_user = get_object_or_404(User, username=username)

    if request.user == target_user:
        if request.headers.get("HX-Request"):
            return JsonResponse({"error": "Cannot follow yourself"}, status=400)
        messages.error(request, "You cannot follow yourself")
        return redirect("profile", slug=username)

    follower_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    target_profile, _ = UserProfile.objects.get_or_create(user=target_user)

    if follower_profile.follows.filter(pk=target_profile.pk).exists():
        follower_profile.follows.remove(target_profile)
        is_following = False
        action = "unfollowed"
    else:
        follower_profile.follows.add(target_profile)
        is_following = True
        action = "followed"

        if target_user.email:
            context = {"follower": request.user, "followed": target_user}
            msg_plain = render_to_string("email/follow_user.html", context)
            msg_html = render_to_string("email/follow_user.html", context)
            send_mail(
                "You got a new follower!!",
                msg_plain,
                settings.EMAIL_TO_STRING,
                [target_user.email],
                html_message=msg_html,
                fail_silently=True,
            )

    follower_count = target_profile.follower.count()

    # HTMX response
    if request.headers.get("HX-Request"):
        html = render_to_string(
            "includes/_follow_button.html",
            {
                "user": target_user,
                "is_following": is_following,
                "follower_count": follower_count,
            },
            request=request,
        )
        return HttpResponse(html)

    # Normal request fallback
    messages.success(request, f"You {action} {target_user.username}")
    return redirect("profile", slug=username)
