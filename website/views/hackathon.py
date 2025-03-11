from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from website.forms import HackathonForm, HackathonPrizeForm, HackathonSponsorForm
from website.models import GitHubIssue, Hackathon, HackathonPrize, HackathonSponsor, Organization


class HackathonListView(ListView):
    """View for listing all hackathons."""

    model = Hackathon
    template_name = "hackathons/list.html"
    context_object_name = "hackathons"
    paginate_by = 10

    def get_queryset(self):
        queryset = Hackathon.objects.all()

        # Filter by active status
        status = self.request.GET.get("status")
        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "inactive":
            queryset = queryset.filter(is_active=False)

        # Filter by time (upcoming, ongoing, past)
        time_filter = self.request.GET.get("time")
        now = timezone.now()
        if time_filter == "upcoming":
            queryset = queryset.filter(start_time__gt=now)
        elif time_filter == "ongoing":
            queryset = queryset.filter(start_time__lte=now, end_time__gte=now)
        elif time_filter == "past":
            queryset = queryset.filter(end_time__lt=now)

        # Filter by organization
        org_id = self.request.GET.get("organization")
        if org_id and org_id.isdigit():
            queryset = queryset.filter(organization_id=int(org_id))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        # Add counts for quick stats
        context["upcoming_count"] = Hackathon.objects.filter(start_time__gt=now).count()
        context["ongoing_count"] = Hackathon.objects.filter(start_time__lte=now, end_time__gte=now).count()
        context["past_count"] = Hackathon.objects.filter(end_time__lt=now).count()

        # Add organizations for filter
        context["organizations"] = Organization.objects.all()

        # Add current filter values
        context["current_status"] = self.request.GET.get("status", "")
        context["current_time"] = self.request.GET.get("time", "")
        context["current_org"] = self.request.GET.get("organization", "")

        return context


class HackathonDetailView(DetailView):
    """View for displaying a single hackathon."""

    model = Hackathon
    template_name = "hackathons/detail.html"
    context_object_name = "hackathon"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hackathon = self.get_object()

        # Get the leaderboard
        context["leaderboard"] = hackathon.get_leaderboard()

        # Get sponsors by level
        sponsors = hackathon.sponsors.all()
        sponsors_by_level = {"platinum": [], "gold": [], "silver": [], "bronze": [], "partner": []}
        for sponsor in sponsors:
            sponsors_by_level[sponsor.sponsor_level].append(sponsor)
        context["sponsors_by_level"] = sponsors_by_level

        # Get prizes
        context["prizes"] = hackathon.prizes.all()

        # Check if user can manage this hackathon
        user = self.request.user
        can_manage = False
        if user.is_authenticated:
            if user.is_superuser:
                can_manage = True
            else:
                # Check if user is admin or manager of the organization
                org = hackathon.organization
                can_manage = org.is_admin(user) or org.is_manager(user)
        context["can_manage"] = can_manage

        # Get participant count (users who have contributed to the repositories)
        repo_ids = hackathon.repositories.values_list("id", flat=True)

        # Count unique users who have created pull requests to the hackathon repositories
        # during the hackathon period
        participant_count = (
            GitHubIssue.objects.filter(
                repo__in=repo_ids,
                created_at__gte=hackathon.start_time,
                created_at__lte=hackathon.end_time,
                type="pull_request",
            )
            .values("user_profile")
            .distinct()
            .count()
        )

        context["participant_count"] = participant_count

        # Count pull requests
        pr_count = GitHubIssue.objects.filter(
            repo__in=repo_ids,
            created_at__gte=hackathon.start_time,
            created_at__lte=hackathon.end_time,
            type="pull_request",
        ).count()

        context["pr_count"] = pr_count

        # Count merged pull requests
        merged_pr_count = GitHubIssue.objects.filter(
            repo__in=repo_ids,
            created_at__gte=hackathon.start_time,
            created_at__lte=hackathon.end_time,
            type="pull_request",
            is_merged=True,
        ).count()

        context["merged_pr_count"] = merged_pr_count

        # Get view data for sparkline chart
        import json
        from datetime import timedelta

        from django.db.models import Sum
        from django.db.models.functions import TruncDate
        from django.utils import timezone

        from website.models import IP

        # Get the path for this hackathon
        hackathon_path = f"/hackathons/{hackathon.slug}/"

        # Get the last 14 days of view data
        today = timezone.now().date()
        fourteen_days_ago = today - timedelta(days=14)

        # Query IP table for view counts by date
        view_data = (
            IP.objects.filter(path=hackathon_path, created__date__gte=fourteen_days_ago)
            .annotate(date=TruncDate("created"))
            .values("date")
            .annotate(count=Sum("count"))
            .order_by("date")
        )

        # Prepare data for the sparkline chart
        dates = []
        counts = []

        # Fill in missing dates with zero counts
        current_date = fourteen_days_ago
        date_counts = {item["date"]: item["count"] for item in view_data}

        while current_date <= today:
            dates.append(current_date.strftime("%Y-%m-%d"))
            counts.append(date_counts.get(current_date, 0))
            current_date += timedelta(days=1)

        context["view_dates"] = json.dumps(dates)
        context["view_counts"] = json.dumps(counts)
        context["total_views"] = sum(counts)

        return context


class HackathonCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new hackathon."""

    model = Hackathon
    form_class = HackathonForm
    template_name = "hackathons/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Hackathon"
        context["submit_text"] = "Create Hackathon"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Hackathon created successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("hackathon_detail", kwargs={"slug": self.object.slug})


class HackathonUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """View for updating an existing hackathon."""

    model = Hackathon
    form_class = HackathonForm
    template_name = "hackathons/form.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def test_func(self):
        hackathon = self.get_object()
        user = self.request.user
        if user.is_superuser:
            return True
        org = hackathon.organization
        return org.is_admin(user) or org.is_manager(user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit Hackathon: {self.object.name}"
        context["submit_text"] = "Update Hackathon"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Hackathon updated successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("hackathon_detail", kwargs={"slug": self.object.slug})


class HackathonSponsorCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """View for adding a sponsor to a hackathon."""

    model = HackathonSponsor
    form_class = HackathonSponsorForm
    template_name = "hackathons/sponsor_form.html"

    def test_func(self):
        hackathon = get_object_or_404(Hackathon, slug=self.kwargs["slug"])
        user = self.request.user
        if user.is_superuser:
            return True
        org = hackathon.organization
        return org.is_admin(user) or org.is_manager(user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hackathon = get_object_or_404(Hackathon, slug=self.kwargs["slug"])
        context["hackathon"] = hackathon
        context["title"] = f"Add Sponsor to {hackathon.name}"
        context["submit_text"] = "Add Sponsor"
        return context

    def form_valid(self, form):
        form.instance.hackathon = get_object_or_404(Hackathon, slug=self.kwargs["slug"])
        messages.success(self.request, "Sponsor added successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("hackathon_detail", kwargs={"slug": self.kwargs["slug"]})


class HackathonPrizeCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """View for adding a prize to a hackathon."""

    model = HackathonPrize
    form_class = HackathonPrizeForm
    template_name = "hackathons/prize_form.html"

    def test_func(self):
        hackathon = get_object_or_404(Hackathon, slug=self.kwargs["slug"])
        user = self.request.user
        if user.is_superuser:
            return True
        org = hackathon.organization
        return org.is_admin(user) or org.is_manager(user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["hackathon"] = get_object_or_404(Hackathon, slug=self.kwargs["slug"])
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hackathon = get_object_or_404(Hackathon, slug=self.kwargs["slug"])
        context["hackathon"] = hackathon
        context["title"] = f"Add Prize to {hackathon.name}"
        context["submit_text"] = "Add Prize"
        return context

    def form_valid(self, form):
        form.instance.hackathon = get_object_or_404(Hackathon, slug=self.kwargs["slug"])
        messages.success(self.request, "Prize added successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("hackathon_detail", kwargs={"slug": self.kwargs["slug"]})
