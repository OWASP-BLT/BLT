from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from website.models import (
    Adventure,
    AdventureTask,
    UserAdventureProgress,
    UserTaskSubmission,
)


class AdventureListView(ListView):
    """Display all available adventures."""

    model = Adventure
    template_name = "adventures/adventure_list.html"
    context_object_name = "adventures"
    paginate_by = 12

    def get_queryset(self):
        queryset = Adventure.objects.filter(is_active=True).prefetch_related("tasks")

        # Filter by category
        category = self.request.GET.get("category")
        if category:
            queryset = queryset.filter(category=category)

        # Filter by difficulty
        difficulty = self.request.GET.get("difficulty")
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Adventure.CATEGORY_CHOICES
        context["difficulties"] = Adventure.DIFFICULTY_CHOICES
        context["selected_category"] = self.request.GET.get("category", "")
        context["selected_difficulty"] = self.request.GET.get("difficulty", "")

        # Add user progress for each adventure if user is authenticated
        if self.request.user.is_authenticated:
            user_progress = UserAdventureProgress.objects.filter(
                user=self.request.user, adventure__in=context["adventures"]
            ).select_related("adventure")

            progress_dict = {progress.adventure_id: progress for progress in user_progress}
            for adventure in context["adventures"]:
                adventure.user_progress = progress_dict.get(adventure.id)

        return context


class AdventureDetailView(DetailView):
    """Display a single adventure with its tasks and user progress."""

    model = Adventure
    template_name = "adventures/adventure_detail.html"
    context_object_name = "adventure"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        adventure = self.object

        # Get tasks
        context["tasks"] = adventure.tasks.all().order_by("order")

        # Get user progress if authenticated
        if self.request.user.is_authenticated:
            progress, created = UserAdventureProgress.objects.get_or_create(
                user=self.request.user, adventure=adventure
            )
            context["progress"] = progress

            # Get task submissions
            submissions = UserTaskSubmission.objects.filter(progress=progress).select_related("task")
            submissions_dict = {submission.task_id: submission for submission in submissions}

            # Add submission info to each task
            for task in context["tasks"]:
                task.submission = submissions_dict.get(task.id)

        return context


@login_required
@require_POST
def submit_task(request, slug, task_id):
    """Submit proof for completing a task."""
    adventure = get_object_or_404(Adventure, slug=slug, is_active=True)
    task = get_object_or_404(AdventureTask, id=task_id, adventure=adventure)

    # Get or create progress
    progress, created = UserAdventureProgress.objects.get_or_create(user=request.user, adventure=adventure)

    proof_url = request.POST.get("proof_url", "").strip()
    notes = request.POST.get("notes", "").strip()

    if not proof_url and not notes:
        messages.error(request, "Please provide a proof URL or notes for your submission.")
        return redirect("adventure_detail", slug=slug)

    # Create or update submission
    with transaction.atomic():
        submission, created = UserTaskSubmission.objects.update_or_create(
            progress=progress,
            task=task,
            defaults={
                "proof_url": proof_url,
                "notes": notes,
                "status": "pending",
                "approved": False,
            },
        )

    if created:
        messages.success(request, f"Task '{task.title}' submitted for review!")
    else:
        messages.info(request, f"Task '{task.title}' resubmitted successfully.")

    return redirect("adventure_detail", slug=slug)


@login_required
def start_adventure(request, slug):
    """Start tracking an adventure."""
    adventure = get_object_or_404(Adventure, slug=slug, is_active=True)

    progress, created = UserAdventureProgress.objects.get_or_create(user=request.user, adventure=adventure)

    if created:
        messages.success(request, f"Started adventure: {adventure.title}")
    else:
        messages.info(request, f"You've already started this adventure.")

    return redirect("adventure_detail", slug=slug)
