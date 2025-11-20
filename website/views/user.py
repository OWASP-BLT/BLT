# stdlib
import base64
import hashlib
import hmac
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

# 3rd-party
import requests
from allauth.account.signals import user_signed_up
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
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
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView, TemplateView, View
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response

from website.bitcoin_utils import send_bch_payment
from website.forms import MonitorForm, UserDeleteForm, UserProfileForm
from website.models import (
    IP,
    BaconEarning,
    BaconSubmission,
    Badge,
    Challenge,
    Contributor,
    Domain,
    GitHubIssue,
    GitHubReview,
    GlobalConfig,
    Hunt,
    InviteFriend,
    Issue,
    IssueScreenshot,
    Monitor,
    Notification,
    PaymentReceipt,
    PaymentRecord,
    Points,
    Repo,
    SuspiciousEvent,
    Tag,
    Thread,
    UserBadge,
    UserProfile,
    Wallet,
    WebhookEvent,
)

logger = logging.getLogger(__name__)

# allowed currencies for autopay
ALLOWED_CURRENCIES = {"BCH"}

# For parsing "Fixes #123", "Closes #123", "Resolves #123"
FIXES_RE = re.compile(r"(?i)\b(?:fixes|closes|resolves)\s*#(\d+)\b")


def get_daily_total():
    today = timezone.now().date()
    total = PaymentRecord.objects.filter(status="completed", processed_at__date=today).aggregate(s=Sum("usd_amount"))[
        "s"
    ]
    return total or Decimal("0")


def get_monthly_total():
    now = timezone.now()
    total = PaymentRecord.objects.filter(
        status="completed", processed_at__year=now.year, processed_at__month=now.month
    ).aggregate(s=Sum("usd_amount"))["s"]
    return total or Decimal("0")


def get_daily_repo_total(repo):
    today = timezone.now().date()
    total = PaymentRecord.objects.filter(status="completed", repo=repo, processed_at__date=today).aggregate(
        s=Sum("usd_amount")
    )["s"]
    return total or Decimal("0")


def get_monthly_repo_total(repo):
    now = timezone.now()
    total = PaymentRecord.objects.filter(
        status="completed", repo=repo, processed_at__year=now.year, processed_at__month=now.month
    ).aggregate(s=Sum("usd_amount"))["s"]
    return total or Decimal("0")


def get_user_daily_total(user_profile):
    today = timezone.now().date()
    total = PaymentRecord.objects.filter(
        user_profile=user_profile, status="completed", processed_at__date=today
    ).aggregate(s=Sum("usd_amount"))["s"]
    return total or Decimal("0")


def get_user_monthly_total(user_profile):
    now = timezone.now()
    total = PaymentRecord.objects.filter(
        user_profile=user_profile, status="completed", processed_at__year=now.year, processed_at__month=now.month
    ).aggregate(s=Sum("usd_amount"))["s"]
    return total or Decimal("0")


def get_user_hourly_autopay_count(user_profile):
    one_hour_ago = timezone.now() - timedelta(hours=1)
    return PaymentRecord.objects.filter(
        user_profile=user_profile, status="completed", processed_at__gte=one_hour_ago
    ).count()


def alert_suspicious(event_type, message, user_profile=None, repo=None, pr_number=None):
    try:
        SuspiciousEvent.objects.create(
            user_profile=user_profile, repo=repo, pr_number=pr_number, event_type=event_type, message=message
        )
    except Exception:
        logger.exception("Failed to save suspicious event")

    # Email admin
    try:
        send_mail(
            subject=f"[ALERT] {event_type}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
        )
    except Exception:
        logger.warning("Could not send suspicious activity email")


def gc_increment(key, amount):
    """
    Atomically increment a numeric GlobalConfig value.
    Creates the row if missing.
    Ensures no lost updates.
    """
    with transaction.atomic():
        obj, created = GlobalConfig.objects.select_for_update().get_or_create(key=key, defaults={"value": amount})
        if not created:
            if isinstance(obj.value, (int, float)):
                obj.value = obj.value + amount
            else:
                obj.value = Decimal(str(obj.value)) + Decimal(str(amount))
        obj.save(update_fields=["value"])
        return obj.value


def gc_get(key, default=None):
    """
    Read a persistent GlobalConfig value. Returns python-native values when possible.
    Short-lived cooldowns should use cache instead of GlobalConfig.
    """
    try:
        obj = GlobalConfig.objects.filter(key=key).first()
        if not obj:
            return default
        # try to parse booleans/numbers that were stored as strings
        val = obj.value
        if val in ("True", "true", "1"):
            return True
        if val in ("False", "false", "0"):
            return False
        return val
    except Exception:
        logger.exception(f"gc_get failed for key {key}")
        return default


def gc_set_atomic(key, value):
    """
    Safe set for GlobalConfig, preventing race conditions.
    """
    with transaction.atomic():
        obj, _ = GlobalConfig.objects.select_for_update().get_or_create(key=key)
        obj.value = value
        obj.save(update_fields=["value"])
        return obj.value


def sign_payment_comment(repo_id, pr_number, bounty_issue_id=None, usd_amount=None, tx_id=None):
    secret = getattr(settings, "AUTOPAY_COMMENT_SIGNING_SECRET", "")
    if not secret:
        return ""  # can't sign; return empty string to avoid crashing

    msg = f"{repo_id}:{pr_number}:{bounty_issue_id or ''}:{usd_amount or ''}:{tx_id or ''}"
    sig = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).digest()
    return base64.b64encode(sig).decode()


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


@login_required
def update_bch_address(request):
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect(reverse("profile", args=[request.user.username]))

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
            messages.success(request, f"{selected_crypto} address updated successfully.")

        except Exception as e:
            logger.exception(f"Failed to update address for user {selected_crypto} {request.user.username}")
            messages.error(request, f"Failed to update {selected_crypto} address.")

    else:
        messages.error(request, f"Please provide a valid {selected_crypto or 'crypto'} address.")

    return redirect(reverse("profile", args=[request.user.username]))


@login_required
def profile_edit(request):
    from allauth.account.models import EmailAddress
    from allauth.account.utils import send_email_confirmation

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
                EmailAddress.objects.update_or_create(
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
                    send_email_confirmation(request, request.user, email=new_email)
                except Exception as e:
                    logger.exception(f"Failed to send email confirmation to {new_email}: {e}")
                    messages.error(request, "Failed to send verification email. Please try again later.")
                    return redirect("profile", slug=request.user.username)

                messages.info(
                    request,
                    "A verification link has been sent to your new email. " "Please verify to complete the update.",
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
        UserProfile.objects.annotate(review_count=Count("reviews_made"))
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
        for activity in context["activities"]:
            context["activity_screenshots"][activity] = IssueScreenshot.objects.filter(issue=activity.pk).first()
        context["profile_form"] = UserProfileForm()
        context["total_open"] = Issue.objects.filter(user=self.object, status="open").count()
        context["total_closed"] = Issue.objects.filter(user=self.object, status="closed").count()
        context["current_month"] = datetime.now().month
        if self.request.user.is_authenticated:
            context["wallet"] = Wallet.objects.get(user=self.request.user)
        context["graph"] = (
            Issue.objects.filter(user=self.object)
            .filter(
                created__month__gte=(datetime.now().month - 6),
                created__month__lte=datetime.now().month,
            )
            .annotate(month=ExtractMonth("created"))
            .values("month")
            .annotate(c=Count("id"))
            .order_by()
        )
        context["total_bugs"] = Issue.objects.filter(user=self.object, hunt=None).count()
        for i in range(0, 7):
            context["bug_type_" + str(i)] = Issue.objects.filter(user=self.object, hunt=None, label=str(i))

        arr = []
        allFollowers = user.userprofile.follower.all()
        for userprofile in allFollowers:
            arr.append(User.objects.get(username=str(userprofile.user)))
        context["followers"] = arr

        arr = []
        allFollowing = user.userprofile.follows.all()
        for userprofile in allFollowing:
            arr.append(User.objects.get(username=str(userprofile.user)))
        context["following"] = arr

        context["followers_list"] = [str(prof.user.email) for prof in user.userprofile.follower.all()]
        context["bookmarks"] = user.userprofile.issue_saved.all()
        # tags
        context["user_related_tags"] = UserProfile.objects.filter(user=self.object).first().tags.all()
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

        data = (
            data.annotate(total_score=Sum("points__score"))
            .order_by("-total_score")
            .filter(
                total_score__gt=0,
                username__isnull=False,
            )
            .exclude(username="")
        )
        if api:
            return data.values("id", "username", "total_score")
        return data

    def current_month_leaderboard(self, api=False):
        """
        leaderboard which includes current month users scores
        """
        return self.get_leaderboard(month=int(datetime.now().month), year=int(datetime.now().year), api=api)

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
            context["wallet"] = Wallet.objects.get(user=self.request.user)

        context["leaderboard"] = self.get_leaderboard()[:10]  # Limit to 10 entries

        # Pull Request Leaderboard - Only show PRs from tracked repositories
        pr_leaderboard = (
            GitHubIssue.objects.filter(
                type="pull_request",
                is_merged=True,
                repo__isnull=False,  # Only include PRs from tracked repositories
            )
            .exclude(user_profile__isnull=True)  # Exclude PRs without user profiles
            .select_related("user_profile__user", "repo")  # Optimize database queries
            .values(
                "user_profile__user__username",
                "user_profile__user__email",
                "user_profile__github_url",
            )
            .annotate(total_prs=Count("id"))
            .order_by("-total_prs")[:10]
        )
        # Extract GitHub username from URL for avatar
        for leader in pr_leaderboard:
            github_username = extract_github_username(leader.get("user_profile__github_url"))
            if github_username:
                leader["github_username"] = github_username
        context["pr_leaderboard"] = pr_leaderboard

        # Reviewed PR Leaderboard - Fixed query to properly count reviews
        reviewed_pr_leaderboard = (
            GitHubReview.objects.filter(reviewer__user__isnull=False)
            .values(
                "reviewer__user__username",
                "reviewer__user__email",
                "reviewer__github_url",
            )
            .annotate(total_reviews=Count("id"))
            .order_by("-total_reviews")[:10]
        )
        # Extract GitHub username from URL for avatar
        for leader in reviewed_pr_leaderboard:
            github_username = extract_github_username(leader.get("reviewer__github_url"))
            if github_username:
                leader["github_username"] = github_username
        context["code_review_leaderboard"] = reviewed_pr_leaderboard

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
            context["wallet"] = Wallet.objects.get(user=self.request.user)

        year = self.request.GET.get("year")

        if not year:
            year = datetime.now().year

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
            "Novermber",
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
            context["wallet"] = Wallet.objects.get(user=self.request.user)

        month = self.request.GET.get("month")
        year = self.request.GET.get("year")

        if not month:
            month = datetime.now().month
        if not year:
            year = datetime.now().year

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


def create_wallet(request):
    for user in User.objects.all():
        Wallet.objects.get_or_create(user=user)
    return JsonResponse("Created", safe=False)


def create_tokens(request):
    for user in User.objects.all():
        Token.objects.get_or_create(user=user)
    return JsonResponse("Created", safe=False)


def get_score(request):
    users = []
    temp_users = (
        User.objects.annotate(total_score=Sum("points__score")).order_by("-total_score").filter(total_score__gt=0)
    )
    rank_user = 1
    for each in temp_users.all():
        temp = {}
        temp["rank"] = rank_user
        temp["id"] = each.id
        temp["User"] = each.username
        temp["score"] = Points.objects.filter(user=each.id).aggregate(total_score=Sum("score"))
        temp["image"] = list(UserProfile.objects.filter(user=each.id).values("user_avatar"))[0]
        temp["title_type"] = list(UserProfile.objects.filter(user=each.id).values("title"))[0]
        temp["follows"] = list(UserProfile.objects.filter(user=each.id).values("follows"))[0]
        temp["savedissue"] = list(UserProfile.objects.filter(user=each.id).values("issue_saved"))[0]
        rank_user = rank_user + 1
        users.append(temp)
    return JsonResponse(users, safe=False)


@login_required(login_url="/accounts/login")
def follow_user(request, user):
    if request.method == "GET":
        try:
            userx = User.objects.get(username=user)
            flag = 0
            list_userfrof = request.user.userprofile.follows.all()
            for prof in list_userfrof:
                if str(prof) == (userx.email):
                    request.user.userprofile.follows.remove(userx.userprofile)
                    flag = 1
            if flag != 1:
                request.user.userprofile.follows.add(userx.userprofile)
                msg_plain = render_to_string("email/follow_user.html", {"follower": request.user, "followed": userx})
                msg_html = render_to_string("email/follow_user.html", {"follower": request.user, "followed": userx})

                send_mail(
                    "You got a new follower!!",
                    msg_plain,
                    settings.EMAIL_TO_STRING,
                    [userx.email],
                    html_message=msg_html,
                )
            return HttpResponse("Success")
        except User.DoesNotExist:
            return HttpResponse(f"User {user} not found", status=404)


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


def handle_pull_request_event(payload):
    pr = payload["pull_request"]
    action = payload.get("action")
    repo_full_name = pr["base"]["repo"]["full_name"]
    # Whitelist check
    if repo_full_name not in settings.ALLOWED_REPOS:
        logger.warning(f"Repo {repo_full_name} not allowed for autopay")
        return JsonResponse({"status": "skipped", "reason": "unapproved repo"}, status=200)

    # Enhanced to handle automatic payments for merged PRs with bounty labels
    action = payload.get("action")
    pr = payload["pull_request"]

    if action == "closed" and pr.get("merged"):
        pr_user_profile = UserProfile.objects.filter(github_url=pr["user"]["html_url"]).first()

        if not pr_user_profile:
            logger.warning("No UserProfile found for PR author %s", pr["user"]["html_url"])
            return JsonResponse({"status": "skipped", "reason": "no_user_profile"}, status=200)

        # Award badge
        assign_github_badge(pr_user_profile.user, "First PR Merged")

        # Extract bounty labels
        labels = pr.get("labels", [])
        usd_amount = extract_bounty_from_labels(labels)

        # No bounty → exit safely
        if not usd_amount or usd_amount <= 0:
            logger.info("Merged PR #%s has no bounty label; skipping autopay", pr["number"])
            return JsonResponse({"status": "success", "reason": "no_bounty_label"}, status=200)

        # Call full autopay pipeline
        process_bounty_payment(
            pr_user_profile=pr_user_profile,
            usd_amount=usd_amount,
            pr_data=pr,
        )

    return JsonResponse({"status": "success"}, status=200)


def _extract_linked_issue_number(pr_payload=None, pr_data=None, payload=None):
    """
    Best-effort extraction of linked issue number:
    1. payload.get("linked_issue_number") (explicit custom field)
    2. payload.get("issue", {}).get("number") (if present)
    3. parse PR body for "Fixes #123", "Closes #123", etc.
    Returns int or None.
    """
    # explicit custom field is highest priority
    if payload:
        val = payload.get("linked_issue_number") or (payload.get("issue") or {}).get("number")
        if val:
            try:
                return int(val)
            except Exception:
                pass

    body = None
    if pr_data and pr_data.get("body"):
        body = pr_data.get("body")
    elif pr_payload:
        body = (pr_payload or {}).get("body")

    if body:
        m = FIXES_RE.search(body)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass

    return None


def record_payment_atomic(
    repo,
    pr_number,
    pr_user_profile,
    pr_data,
    tx_id,
    usd_amount,
    currency,
    payload=None,
    bch_amount=None,
    usd_rate=None,
    address=None,
    user_daily=None,
    user_monthly=None,
    repo_daily=None,
    repo_monthly=None,
    daily_total=None,
):
    """
    Secure autopay flow ensuring:
      - Payment is made only when a bounty issue (with $) is identified.
      - Two DB rows are created/updated: PR GitHubIssue (type=pull_request) and Bounty GitHubIssue (type=issue).
      - Bounty_issue is the record where tx_id is stored and audited.
      - All writes occur inside transaction.atomic() with select_for_update() for locked rows.
      - Idempotent via PaymentRecord.status check.
    Returns: (True, "message") on success or (False, "reason") on abort/failure.
    """

    # 0. Basic validation
    if not tx_id:
        return False, "Missing tx_id"
    if currency not in ALLOWED_CURRENCIES:
        return False, f"Unsupported currency: {currency}"
    try:
        usd_amount_dec = Decimal(str(usd_amount))
    except (InvalidOperation, TypeError, ValueError):
        return False, "Invalid usd_amount"
    if usd_amount_dec <= 0:
        return False, "usd_amount must be > 0"

    try:
        pr_num = int(pr_number)
    except Exception:
        return False, "Invalid pr_number"

    # Best-effort extract the linked bounty issue number
    linked_issue_num = _extract_linked_issue_number(
        pr_payload=(payload or {}).get("pull_request") if payload else None, pr_data=pr_data, payload=payload
    )

    with transaction.atomic():
        # Hard guarantee: only one completed PaymentRecord per PR
        duplicate_records = PaymentRecord.objects.filter(repo=repo, pr_number=pr_num, currency=currency).exclude(
            status="pending"
        )

        # If more than one exists → highly abnormal → freeze system & alert
        if duplicate_records.count() > 1:
            logger.critical(
                "SECURITY ALERT: Duplicate completed PaymentRecord rows for PR #%s in repo=%s", pr_num, repo.id
            )
            return False, "Duplicate payment records detected — manual review required"

        # Lock the only PaymentRecord to enforce inline idempotency
        payment_row = PaymentRecord.objects.select_for_update().filter(repo=repo, pr_number=pr_num).first()

        # If this row is already completed → abort safely
        if payment_row and payment_row.status == "completed":
            logger.info("Idempotency gate: PR #%s already paid (tx=%s)", pr_num, payment_row.tx_id)
            gc_set_atomic("autopay_fail_count", 0)  # reset
            return True, "Already completed"

        # 1. Lock user profile (avoid concurrent winnings races)
        profile = UserProfile.objects.select_for_update().get(pk=pr_user_profile.pk)

        # 2. Find or create the PR GitHubIssue row (select_for_update to prevent duplicate creation)
        pr_issue = (
            GitHubIssue.objects.select_for_update().filter(repo=repo, issue_id=pr_num, type="pull_request").first()
        )
        if not pr_issue:
            pr_title = (
                (pr_data.get("title") if pr_data else None)
                or (payload and payload.get("pull_request", {}).get("title"))
                or f"PR #{pr_num}"
            )
            pr_body = (
                (pr_data.get("body") if pr_data else None)
                or (payload and payload.get("pull_request", {}).get("body"))
                or ""
            )
            pr_url = (
                (pr_data.get("html_url") if pr_data else None)
                or (payload and payload.get("pull_request", {}).get("html_url"))
                or ""
            )
            pr_created_at = None
            pr_updated_at = None
            try:
                pr_payload = payload.get("pull_request") if payload else {}
                pr_created_at = pr_payload.get("created_at")
                pr_updated_at = pr_payload.get("updated_at")
            except Exception:
                pass
            # required fields fallback
            if not pr_created_at:
                pr_created_at = timezone.now()
            if not pr_updated_at:
                pr_updated_at = timezone.now()

            pr_issue = GitHubIssue.objects.create(
                issue_id=pr_num,
                repo=repo,
                user_profile=pr_user_profile,
                contributor=getattr(pr_user_profile, "contributor", None),
                title=pr_title,
                body=pr_body,
                url=pr_url or "",
                type="pull_request",
                state=(pr_data.get("state") if pr_data else (payload and payload.get("pull_request", {}).get("state")))
                or "closed",
                created_at=pr_created_at,
                updated_at=pr_updated_at,
                is_merged=bool(
                    (payload and payload.get("pull_request", {}).get("merged")) or (pr_data and pr_data.get("merged"))
                ),
            )

        # 3. Locate the bounty issue (the thing we actually pay) — must have has_dollar_tag=True
        bounty_issue = None
        if linked_issue_num:
            bounty_issue = (
                GitHubIssue.objects.select_for_update()
                .filter(repo=repo, issue_id=linked_issue_num, type="issue", has_dollar_tag=True)
                .first()
            )

        # IMPORTANT: If we couldn't find a bounty issue via the extraction,
        # DO NOT attempt to pay. This is the secure behavior.
        if not bounty_issue:
            logger.warning(
                "Autopay aborted: no bounty issue found for PR #%s in repo=%s. linked_issue_num=%s",
                pr_num,
                getattr(repo, "id", str(repo)),
                linked_issue_num,
            )
            return False, "No bounty issue found (requires explicit linking or 'Fixes #NNN' in PR body)."
        #  Verify author match BEFORE processing payment
        if bounty_issue.user_profile_id != pr_user_profile.id:
            alert_suspicious(
                "mismatched_author",
                f"PR author ({pr_user_profile.user.username}) does not match bounty issue author",
                user_profile=pr_user_profile,
                repo=repo,
                pr_number=pr_num,
            )
            return False, "Author mismatch"

        # 4. Link PR -> bounty issue (M2M). Use add() to not replace existing links.
        try:
            # Add only if not already linked
            if not bounty_issue.linked_pull_requests.filter(pk=pr_issue.pk).exists():
                # add expects a model instance
                #  Safety guard before linking PR <-> bounty issue

                # Prevent cross-repo linking (critical)
                if bounty_issue.repo_id != pr_issue.repo_id:
                    logger.error(
                        "SECURITY ALERT: Attempted cross-repo linking: bounty #%s repo=%s, PR #%s repo=%s",
                        bounty_issue.issue_id,
                        bounty_issue.repo_id,
                        pr_issue.issue_id,
                        pr_issue.repo_id,
                    )
                    return False, "Cross-repo linking blocked"

                # Prevent issue→issue linking
                if pr_issue.type != "pull_request":
                    logger.error("SECURITY ALERT: Non-PR linked as pull_request: id=%s", pr_issue.issue_id)
                    return False, "Invalid link type — only PRs may be linked"

                # Prevent multiple bounty issues for same PR (business rule)
                existing_bounties = GitHubIssue.objects.filter(
                    linked_pull_requests=pr_issue,
                    type="issue",
                    has_dollar_tag=True,
                ).exclude(pk=bounty_issue.pk)

                if existing_bounties.exists():
                    logger.error(
                        "SECURITY ALERT: PR #%s trying to link to second bounty issue; existing=%s new=%s",
                        pr_issue.issue_id,
                        list(existing_bounties.values_list("issue_id", flat=True)),
                        bounty_issue.issue_id,
                    )
                    return False, "PR already linked to a different bounty"

                # Prevent adding link twice
                if bounty_issue.linked_pull_requests.filter(pk=pr_issue.pk).exists():
                    logger.info("PR #%s already linked to bounty #%s", pr_issue.issue_id, bounty_issue.issue_id)
                else:
                    bounty_issue.linked_pull_requests.add(pr_issue)
                    bounty_issue.updated_at = timezone.now()
                    bounty_issue.save(update_fields=["updated_at"])
        except Exception:
            logger.exception(f"Failed to add M2M link from bounty #{bounty_issue.issue_id} to PR #{pr_num} (non-fatal)")

            # don't abort payout for link failure; continue.

        # 5. Idempotency check: PaymentRecord exists & completed => do nothing (already paid)
        pr_record = PaymentRecord.objects.select_for_update().filter(repo=repo, pr_number=pr_num).first()
        if pr_record and pr_record.status == "completed":
            logger.info("Autopay skipped: PaymentRecord already completed for repo=%s pr=%s", getattr(repo, "id", repo))
            return True, "Already completed"

        # 6. Save transaction on the bounty_issue (this keeps audit on canonical bounty)
        if currency == "BCH":
            bounty_issue.bch_tx_id = tx_id
        else:
            bounty_issue.sponsors_tx_id = tx_id

        bounty_issue.updated_at = timezone.now()
        bounty_issue.save(update_fields=["bch_tx_id", "sponsors_tx_id", "updated_at"])
        #  ATOMIC DAILY LIMIT ENFORCEMENT
        daily_key = f"total_paid_{timezone.now().date()}"
        DAILY_LIMIT = getattr(settings, "MAX_DAILY_PAYOUT_USD", Decimal("1500"))

        current_total = Decimal(str(gc_get(daily_key, 0)))
        projected = current_total + usd_amount_dec

        if projected > DAILY_LIMIT:
            logger.warning(
                "Daily limit exceeded inside atomic block: current=%s add=%s > limit=%s",
                current_total,
                usd_amount_dec,
                DAILY_LIMIT,
            )
            return False, "Daily limit exceeded"

        # Safe update (atomic)
        gc_set_atomic(daily_key, str(projected))

        # 7. Mark/create PaymentRecord as completed
        if pr_record:
            pr_record.tx_id = tx_id
            pr_record.status = "completed"
            pr_record.processed_at = timezone.now()
            pr_record.save(update_fields=["tx_id", "status", "processed_at"])
        else:
            pr_record = PaymentRecord.objects.create(
                repo=repo,
                pr_number=pr_num,
                user_profile=pr_user_profile,
                currency=currency,
                usd_amount=usd_amount_dec,
                tx_id=tx_id,
                status="completed",
                processed_at=timezone.now(),
            )

        # 8. Update winnings on the user profile (locked)
        current_win = profile.winnings or Decimal("0")
        profile.winnings = current_win + usd_amount_dec
        profile.save(update_fields=["winnings"])

        # 9. Final audit log
        logger.info(
            "Autopay recorded: repo=%s bounty_issue=%s pr=%s user=%s amount=%s tx=%s currency=%s",
            getattr(repo, "id", str(repo)),
            bounty_issue.issue_id,
            pr_num,
            pr_user_profile.user.username,
            usd_amount_dec,
            tx_id,
            currency,
        )
        PaymentReceipt.objects.create(
            payment=pr_record,
            repo=repo,
            user_profile=pr_user_profile,
            pr_number=pr_num,
            bounty_issue_number=bounty_issue.issue_id,
            tx_id=tx_id,
            currency=currency,
            usd_amount=usd_amount_dec,
            bch_amount=bch_amount,
            usd_rate=usd_rate,
            pr_payload=pr_data,
            metadata={
                "address": address,
                "autopay_locked": gc_get("autopay_locked", False),
                "limits": {
                    "user_daily": float(user_daily),
                    "user_monthly": float(user_monthly),
                    "repo_daily": float(repo_daily),
                    "repo_monthly": float(repo_monthly),
                },
                "system_daily_total": float(daily_total),
            },
        )

    # transaction.atomic() block ended successfully
    return True, "Processed"


def verify_github_signature(request):
    secret = getattr(settings, "GITHUB_WEBHOOK_SECRET", None)
    if not secret:
        logger.error("Missing GITHUB_WEBHOOK_SECRET")
        return False

    signature = request.headers.get("X-Hub-Signature-256")
    if not signature or "=" not in signature:
        logger.warning("Missing or malformed  X-Hub-Signature-256 header")
        return False

    sha_name, received_sig = signature.split("=", 1)
    if sha_name != "sha256":
        logger.warning("Invalid signature format")
        return False

    mac = hmac.new(secret.encode(), msg=request.body, digestmod=hashlib.sha256)

    expected_sig = mac.hexdigest()
    validated = hmac.compare_digest(received_sig, expected_sig)
    if not validated:
        alert_suspicious(
            "signature_failure",
            f"Signature mismatch for webhook from (delivery={request.headers.get('X-GitHub-Delivery')})",
        )
        return False

    return validated


def repo_allowed(payload):
    """
    Ensure the webhook pertains to a tracked repo. Enforce the *base* repository when PR events are present.
    """
    # prefer base repo (for PRs) otherwise top-level repository
    base_repo_full = payload.get("pull_request", {}).get("base", {}).get("repo", {}).get("full_name")
    repo_full = base_repo_full or payload.get("repository", {}).get("full_name")
    if not repo_full:
        logger.warning("repo_allowed: could not find full_name in payload")
        return False

    allowed = repo_full in getattr(settings, "ALLOWED_REPOS", [])
    if not allowed:
        alert_suspicious("invalid_repo", f"Webhook from unapproved repo: {repo_full}")
    return allowed


@csrf_exempt
def github_webhook(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=400)

    # 1) Signature verification
    if not verify_github_signature(request):
        logger.warning("Invalid GitHub webhook signature")
        return JsonResponse({"status": "unauthorized"}, status=401)

    # 2) Delivery ID (Idempotency)
    delivery_id = request.headers.get("X-GitHub-Delivery")
    event_type = request.headers.get("X-GitHub-Event", "")

    if not delivery_id:
        logger.warning("Missing X-GitHub-Delivery header")
        return JsonResponse({"status": "error", "message": "Missing delivery id"}, status=400)

    # 3) Load JSON payload
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    repo_full = payload.get("repository", {}).get("full_name", "unknown")

    # 4) Rate limit per repo (simple)
    rate_key = f"webhook_rl:{repo_full}"
    if not cache.add(rate_key, 0, timeout=60):
        try:
            count = cache.incr(rate_key)
        except Exception:
            count = 9999
    else:
        cache.set(rate_key, 1, timeout=60)
        count = 1

    if count > 30:  # limit: 30 events per minute per repo
        logger.warning("Rate limit reached for repo %s", repo_full)
        return JsonResponse({"status": "rate_limited"}, status=429)

    # 5) Idempotency gate (DB)
    try:
        event_obj, created = WebhookEvent.objects.get_or_create(
            delivery_id=delivery_id, defaults={"event": event_type, "payload": payload}
        )
    except IntegrityError:
        event_obj = WebhookEvent.objects.filter(delivery_id=delivery_id).first()
        created = False

    if not created:
        if event_obj.processed:
            logger.info("Duplicate webhook delivery %s skipped", delivery_id)
            return JsonResponse({"status": "forbidden"}, status=403)
        else:
            # Another worker may be processing
            age = (timezone.now() - event_obj.created_at).total_seconds()
            if age < 300:
                return JsonResponse({"status": "accepted"}, status=202)

    # 6) Repo whitelist
    if not repo_allowed(payload):
        event_obj.processed = True
        event_obj.processed_at = timezone.now()
        event_obj.response_status = 200
        event_obj.save(update_fields=["processed", "processed_at", "response_status"])
        return JsonResponse({"status": "skipped", "reason": "unapproved repo"}, status=200)

    # 7) Dispatch handlers
    handlers = {
        "pull_request": handle_pull_request_event,
        "push": handle_push_event,
        "pull_request_review": handle_review_event,
        "issues": handle_issue_event,
        "status": handle_status_event,
        "fork": handle_fork_event,
        "create": handle_create_event,
    }

    handler = handlers.get(event_type)

    try:
        if handler:
            resp = handler(payload)
            event_obj.processed = True
            event_obj.processed_at = timezone.now()
            event_obj.response_status = getattr(resp, "status_code", 200)
            event_obj.save(update_fields=["processed", "processed_at", "response_status"])
            return resp
        else:
            event_obj.processed = True
            event_obj.processed_at = timezone.now()
            event_obj.response_status = 400
            event_obj.save(update_fields=["processed", "processed_at", "response_status"])
            return JsonResponse({"status": "error", "message": "Unhandled event type"}, status=400)

    except Exception:
        logger.exception("Error processing delivery {delivery_id}")
        event_obj.response_status = 500
        event_obj.save(update_fields=["response_status"])
        return JsonResponse({"status": "error", "message": "Internal error"}, status=500)


def extract_bounty_from_labels(labels):
    # Extract bounty amount from PR labels like $5, $10, etc.
    for label in labels:
        label_name = label.get("name", "") if isinstance(label, dict) else str(label)
        match = re.match(r"^\$(\d+(?:\.\d+)?)$", label_name.strip())
        if match:
            return Decimal(match.group(1))
    return None


def send_crypto_payment(address, amount, currency):
    if currency != "BCH":
        raise NotImplementedError(f"Payment method {currency} not implemented")

    try:
        tx_id = send_bch_payment(address, str(amount))
        if not tx_id:
            raise ValueError("Empty txid returned by BCH backend")
        return tx_id
    except Exception as e:
        logger.exception("send_crypto_payment failed")
        raise


def post_payment_comment(pr_data, tx_id, amount, currency):
    """
    Post an authenticated autopay comment to the PR.
    Includes cryptographic signature to prevent forgery.
    """

    # Normalize amount
    if isinstance(amount, dict):
        bch_amount = amount["bch"]
        usd_amount = amount["usd"]
    else:
        bch_amount = amount
        usd_amount = None

    repo_full_name = pr_data["base"]["repo"]["full_name"]
    pr_number = pr_data["number"]

    # Retrieve repo object (needed for signing)
    repo_name = repo_full_name.split("/")[-1]
    repo = Repo.objects.filter(name__iexact=repo_name).first()

    if not repo:
        logger.error("post_payment_comment: Repo not found (%s)", repo_full_name)
        return False

    # Generate cryptographic signature
    signature = sign_payment_comment(
        repo_id=repo.id,
        pr_number=pr_number,
        usd_amount=usd_amount,
        tx_id=tx_id,
    )

    # Build final comment body
    if getattr(settings, "AUTOPAY_DRY_RUN", False):
        comment_body = (
            f" **DRY RUN MODE** — No real BCH payment has been sent.\n\n"
            f"Autopay pipeline executed successfully but is in dry-run mode.\n"
            f"Simulated Transaction ID: `{tx_id}`\n\n"
            f"Please ignore this message."
        )
    else:
        if currency == "BCH":
            explorer_url = f"https://blockchair.com/bitcoin-cash/transaction/{tx_id}"
            comment_body = (
                f"**Payment Sent!**\n\n"
                f"${usd_amount} has been automatically sent via **Bitcoin Cash (BCH)**.\n\n"
                f"**BCH Amount:** `{bch_amount}`\n"
                f"**Transaction ID:** `{tx_id}`\n"
                f" **View Transaction:** {explorer_url}\n\n"
                f"---\n"
                f" **Autopay Signature:** `{signature}`\n"
                f"_This cryptographic signature verifies this payment was generated by the official OWASP BLT autopay system._\n"
                f"---\n"
                f"Thank you for your contribution! "
            )
        else:
            comment_body = (
                f"${usd_amount} USD ({bch_amount} BCH) has been automatically sent.\n\n" f"🔏 Signature: `{signature}`"
            )

    # Send comment to GitHub
    url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
    headers = {"Authorization": f"token {settings.GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    response = requests.post(url, json={"body": comment_body}, headers=headers, timeout=10)

    if response.status_code != 201:
        logger.error("Failed to post payment comment: %s", response.text)

    return response.status_code == 201


def notify_user_missing_address(user, pr_data):
    """Best-effort email to prompt user to add a BCH address; must never break the webhook."""
    try:
        send_mail(
            subject=f"Action Required: Add BCH Address for Payment (PR #{pr_data.get('number')})",
            message=(
                f"Your PR #{pr_data.get('number')} has been merged and is eligible for a bounty payment!\n\n"
                f"However, we don't have a cryptocurrency address on file for you.\n\n"
                f"Please add your BCH address (preferred) at: {settings.SITE_URL}/profile/edit/\n\n"
                f"Note: BCH addresses must start with 'bitcoincash:'"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )
    except Exception:
        logger.exception(f"Failed to send missing-address email for user={user.username} PR={pr_data.get('number')}")


def notify_admin_payment_failure(pr_data, error_message):
    try:
        send_mail(
            subject=f"Payment Failure for PR #{pr_data.get('number')}",
            message=f"Error processing payment:\n\n{error_message}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
        )
    except Exception:
        logger.exception("Failed to notify admin of payment failure")


def get_or_create_payment_record(repo, pr_number, usd_amount, currency, pr_user_profile):
    """
    Creates a pending PaymentRecord or returns an existing one.
    Ensures idempotency without requiring a DB uniqueness constraint.
    """

    with transaction.atomic():
        existing = PaymentRecord.objects.filter(repo=repo, pr_number=pr_number).first()

        if existing:
            # Completed -> idempotent success; do not create new
            if existing.status == "completed":
                return existing, False
            # Pending -> assume another worker; return to let caller decide handling
            if existing.status == "pending":
                return existing, False
            # Failed -> if old, allow recreation; else return existing
            if existing.status == "failed":
                age = (
                    (
                        timezone.now()
                        - (existing.updated_at if hasattr(existing, "updated_at") else existing.created_at)
                    ).total_seconds()
                    if existing.created_at
                    else None
                )
                # If it's older than a configurable grace window, create a new record
                grace_seconds = getattr(settings, "PAYMENT_FAILED_RETRY_GRACE_SECONDS", 3600)
                if age is None or age > grace_seconds:
                    new_rec = PaymentRecord.objects.create(
                        repo=repo,
                        pr_number=pr_number,
                        user_profile=pr_user_profile,
                        currency=currency,
                        usd_amount=usd_amount,
                        status="pending",
                    )
                    return new_rec, True
                return existing, False

        new_rec = PaymentRecord.objects.create(
            repo=repo,
            pr_number=pr_number,
            user_profile=pr_user_profile,
            currency=currency,
            usd_amount=usd_amount,
            status="pending",
        )
        return new_rec, True


def finalize_payment_record(repo, pr_number, tx_id):
    """
    Marks PaymentRecord as completed & sets tx_id.
    Safe & atomic.
    """
    with transaction.atomic():
        rec = PaymentRecord.objects.select_for_update().filter(repo=repo, pr_number=pr_number).first()

        if not rec:
            logger.error(
                "Missing PaymentRecord during finalize step repo=%s pr=%s", getattr(repo, "id", repo), pr_number
            )
            return None

        # If already completed → idempotent return
        if rec.status == "completed":
            return rec

        rec.tx_id = tx_id
        rec.status = "completed"
        rec.processed_at = timezone.now()
        rec.save()

        return rec


def is_untrusted_github_account(github_username):
    """
    Returns (True, reason) if account is too new / suspicious.
    Returns (False, None) if account looks OK.
    """

    try:
        resp = requests.get(
            f"https://api.github.com/users/{github_username}",
            headers={"Authorization": f"token {settings.GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return True, "GitHub profile lookup failed"

    created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
    age_days = (timezone.now() - created_at).days
    followers = data.get("followers", 0)
    public_repos = data.get("public_repos", 0)

    #  Account younger than 7 days → block autopay
    if age_days < 7:
        return True, f"Account too new: {age_days} days old"

    #  No followers AND less than 2 repos → likely bot
    if followers == 0 and public_repos < 2:
        return True, "Low-trust GitHub profile (0 followers, <2 repos)"

    # Optional stricter rule
    if public_repos == 0:
        return True, "Empty GitHub profile"

    return False, None


def pr_fails_sanity_checks(pr_payload):
    """
    Returns (True, reason) if PR unsafe to autopay.
    Returns (False, None) if PR is acceptable.
    """

    #  basic fields
    additions = pr_payload.get("additions", 0)
    deletions = pr_payload.get("deletions", 0)
    changed_files = pr_payload.get("changed_files", 0)
    title = pr_payload.get("title", "").lower()

    #  PR must have at least 3 lines added or removed
    if additions + deletions < 3:
        return True, "PR too small (<3 LOC)"

    #  at least 1 code file
    # GitHub includes summary but not detailed list unless fetched separately.
    # We fallback to changed_files.
    if changed_files == 0:
        return True, "PR contains no changed files"

    #  Block doc-only PRs
    if "documentation" in title or "docs" in title:
        if additions < 20:  # allow real doc contributions only
            return True, "Documentation-only PR too small"

    #  Block suspicious titles
    SUSPICIOUS_TITLES = [
        "small fix",
        "minor fix",
        "update readme",
        "typo",
        "test",
        "cleanup",
        "patch",
        "update",
        "quick fix",
    ]
    if any(x in title for x in SUSPICIOUS_TITLES):
        if additions < 15:
            return True, "Suspicious low-effort PR title"

    # # Block if PR deletes more than 3× it adds
    # if deletions > additions * 3:
    #     return True, "PR deletes too many lines relative to additions"

    # #  Block PRs with empty or extremely short bodies
    # if len(body.strip()) < 15:
    #     return True, "PR body is too short"

    # All good
    return False, None


def process_bounty_payment(pr_user_profile, usd_amount, pr_data):
    pr_number = pr_data.get("number")
    if pr_number is None:
        logger.error("process_bounty_payment called without PR number")
        return

    # Ensure PR is merged
    if not pr_data.get("merged"):
        logger.warning("process_bounty_payment called for non-merged PR #%s", pr_number)
        return

    repo_full_name = pr_data["base"]["repo"]["full_name"]
    repo_name = repo_full_name.split("/")[-1]
    repo = Repo.objects.filter(name__iexact=repo_name).first()

    if not repo:
        logger.warning("Repo not tracked: %s", repo_full_name)
        return

    try:
        usd_amount_dec = Decimal(str(usd_amount))
    except (InvalidOperation, TypeError, ValueError):
        logger.error("Invalid usd_amount passed to process_bounty_payment: %r", usd_amount)
        return

    if not repo.autopay_enabled:
        logger.warning("Autopay blocked: repo %s has autopay disabled", repo.name)
        return

    #  Short-Lived PR Cooldown Lock
    unique_key = f"autopay_lock_pr_{repo.id}_{pr_number}"
    if not cache.add(unique_key, True, timeout=60):
        return

    #  PR Sanity Checks
    bad, reason = pr_fails_sanity_checks(pr_data)
    if bad:
        alert_suspicious(
            "pr_sanity_failed",
            f"Autopay blocked for PR #{pr_number}: {reason}",
            user_profile=pr_user_profile,
            repo=repo,
            pr_number=pr_number,
        )
        logger.error("Blocked autopay: %s", reason)
        return

    # GitHub Trust Check
    github_username = extract_github_username(pr_user_profile.github_url)
    blocked, reason = is_untrusted_github_account(github_username)

    if blocked:
        alert_suspicious(
            "untrusted_github_account",
            f"Autopay blocked for PR #{pr_number}: {reason}",
            user_profile=pr_user_profile,
            repo=repo,
            pr_number=pr_number,
        )
        logger.error("Autopay blocked: %s", reason)
        return

    # Autopay Lock Gate
    lock_state = gc_get("autopay_locked", False)
    if lock_state:
        logger.error("AUTOPAY PIPELINE LOCKED — refusing to process payments")
        return

    # Alert if amount is unusually large
    MAX_PAYOUT = Decimal("50")  # <=== adjust
    if usd_amount_dec > MAX_PAYOUT:
        alert_suspicious(
            "large_payment",
            f"Large payout attempted: ${usd_amount} for PR #{pr_number}",
            user_profile=pr_user_profile,
            repo=repo,
            pr_number=pr_number,
        )

    # STEP 0 — System-wide and repo-wide safety caps
    daily_total = get_daily_total()
    if daily_total + usd_amount_dec > settings.MAX_DAILY_PAYOUT_USD:
        logger.error("Aborting autopay: daily USD cap exceeded.")
        return

    monthly_total = get_monthly_total()
    if monthly_total + usd_amount_dec > settings.MAX_MONTHLY_PAYOUT_USD:
        logger.error("Aborting autopay: monthly USD cap exceeded.")
        return

    repo_daily = get_daily_repo_total(repo)
    if repo_daily + usd_amount_dec > settings.MAX_DAILY_REPO_PAYOUT_USD:
        logger.error("Aborting autopay: repo daily cap exceeded. Repo: %s", repo.name)
        return

    repo_monthly = get_monthly_repo_total(repo)
    if repo_monthly + usd_amount_dec > settings.MAX_MONTHLY_REPO_PAYOUT_USD:
        logger.error("Aborting autopay: repo monthly cap exceeded. Repo: %s", repo.name)
        return

    #  Per-user safety limits
    user_daily = get_user_daily_total(pr_user_profile)
    if user_daily + usd_amount_dec > settings.MAX_USER_DAILY_PAYOUT_USD:
        logger.error("User daily payout cap exceeded for user %s", pr_user_profile.user.username)
        return

    user_monthly = get_user_monthly_total(pr_user_profile)
    if user_monthly + usd_amount_dec > settings.MAX_USER_MONTHLY_PAYOUT_USD:
        logger.error("User monthly payout cap exceeded for user %s", pr_user_profile.user.username)
        return

    hourly_count = get_user_hourly_autopay_count(pr_user_profile)
    if hourly_count >= settings.MAX_AUTOPAY_PER_USER_PER_HOUR:
        logger.error("User autopay rate limit exceeded for %s", pr_user_profile.user.username)
        return

    """
    Idempotent & safe autopay implementation matching your PaymentRecord model.
    """

    if not getattr(settings, "PAYMENT_ENABLED", False):
        logger.info("Autopay disabled")
        return

    currency = "BCH"

    #  Idempotent safe "claim"
    record, created = get_or_create_payment_record(
        repo=repo,
        pr_number=pr_number,
        usd_amount=usd_amount_dec,
        currency=currency,
        pr_user_profile=pr_user_profile,
    )

    if record.status == "completed":
        logger.info("Autopay already completed for PR #%s", pr_number)
        # update daily total(idempotent retry accounting)
        today_key = f"total_paid_{timezone.now().date()}"
        current_total = Decimal(str(gc_get(today_key, 0)))
        new_total = current_total + usd_amount_dec
        gc_set_atomic(today_key, str(new_total))
        gc_set_atomic("autopay_fail_count", 0)  # reset failure counter
        return

    if record.status == "pending" and not created:
        # pending record already exists → assume another worker or retry
        age_sec = (timezone.now() - record.created_at).total_seconds()
        if age_sec < getattr(settings, "PAYMENT_PENDING_GRACE_SECONDS", 300):
            logger.info("Payment already in-progress for PR #%s", pr_number)
            return

        logger.warning("Stale pending payment for PR #%s — retrying...", pr_number)

    #  Pick BCH address
    address = pr_user_profile.bch_address
    if not address:
        alert_suspicious(
            "missing_bch_address",
            f"User {pr_user_profile.user.username} has no BCH address for PR #{pr_number}",
            user_profile=pr_user_profile,
            repo=repo,
            pr_number=pr_number,
        )
        notify_user_missing_address(pr_user_profile.user, pr_data)
        record.status = "failed"
        record.save()
        return

    if not address.startswith("bitcoincash:"):
        notify_admin_payment_failure(pr_data, "Invalid BCH address format")
        record.status = "failed"
        record.save()
        return

    #  Get BCH/USD rate
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin-cash", "vs_currencies": "usd"},
            timeout=5,
        )
        resp.raise_for_status()
        usd_rate = Decimal(str(resp.json()["bitcoin-cash"]["usd"]))
        bch_amount = usd_amount_dec / usd_rate
        #  Rate sanity check: reject insane values
        if usd_rate < Decimal("50") or usd_rate > Decimal("1000"):
            alert_suspicious(
                "invalid_usd_rate",
                f"Coingecko returned abnormal USD rate: {usd_rate}",
                user_profile=pr_user_profile,
                repo=repo,
                pr_number=pr_number,
            )
            record.status = "failed"
            record.save()
            return

    except Exception:
        logger.exception("Rate lookup failed")
        record.status = "failed"
        record.save()
        fail_count = gc_increment("autopay_fail_count", 1)

        if fail_count >= 5:
            alert_suspicious(
                "autopay_locked",
                "Autopay disabled due to repeated failures (>=5). Manual intervention required.",
                user_profile=pr_user_profile,
                repo=repo,
                pr_number=pr_number,
            )
            gc_set_atomic("autopay_locked", True)

        notify_admin_payment_failure(pr_data, "Rate lookup failed")
        return

    #  External BCH payment call (supports dry-run mode)
    try:
        if getattr(settings, "AUTOPAY_DRY_RUN", False):
            # Simulated tx_id
            tx_id = f"DRYRUN-{timezone.now().timestamp()}"
            logger.warning("DRY RUN autopay: no real BCH payment sent. tx_id=%s", tx_id)
        else:
            # Real payment
            tx_id = send_crypto_payment(address, bch_amount, "BCH")

        # tx_id validation
        if not tx_id or len(str(tx_id)) < 10:
            alert_suspicious(
                "invalid_txid",
                f"Suspicious txid returned: {tx_id}",
                user_profile=pr_user_profile,
                repo=repo,
                pr_number=pr_number,
            )
            raise ValueError("Invalid payment txid returned")

    except Exception as e:
        logger.exception("BCH payment failed")
        record.status = "failed"
        record.save(update_fields=["status"])

        fail_count = gc_increment("autopay_fail_count", 1)

        if fail_count >= 5:
            alert_suspicious(
                "autopay_locked",
                "Autopay disabled due to repeated failures.",
                user_profile=pr_user_profile,
                repo=repo,
                pr_number=pr_number,
            )
            gc_set_atomic("autopay_locked", True)
            notify_admin_payment_failure(pr_data, str(e))
        return

    #  Finalize atomically
    with transaction.atomic():
        success, reason = record_payment_atomic(
            repo=repo,
            pr_number=pr_number,
            pr_user_profile=pr_user_profile,
            pr_data=pr_data,
            tx_id=tx_id,
            usd_amount=usd_amount_dec,
            currency="BCH",
            payload={"pull_request": pr_data},
            bch_amount=bch_amount,
            usd_rate=usd_rate,
            address=address,
            user_daily=user_daily,
            user_monthly=user_monthly,
            repo_daily=repo_daily,
            repo_monthly=repo_monthly,
            daily_total=daily_total,
        )
    if not success:
        logger.error("Payment rejected inside atomic layer: %s", reason)
        record.status = "failed"
        record.save(update_fields=["status"])
        notify_admin_payment_failure(pr_data, reason)
        return

    # reset failures
    gc_set_atomic("autopay_fail_count", 0)

    #  PR comment (non-fatal)
    try:
        post_payment_comment(pr_data, tx_id, {"bch": bch_amount, "usd": usd_amount_dec}, "BCH")
    except Exception:
        logger.exception("Failed to post payment comment")
        notify_admin_payment_failure(pr_data, "Failed to post payment comment")


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
    logger.debug("issue closed")
    if payload["action"] == "closed":
        closer_profile = UserProfile.objects.filter(github_url=payload["sender"]["html_url"]).first()
        if closer_profile:
            closer_user = closer_profile.user
            assign_github_badge(closer_user, "First Issue Closed")
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

        except Exception:
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
                {"status": "error", "message": "An error occured while marking notifications as read"}, status=400
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
                {"status": "error", "message": "An error occured while deleting notification, please try again."},
                status=400,
            )
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)
