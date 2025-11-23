# website/views/Simulation.py

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from website.models import Labs, TaskContent, Tasks, UserLabProgress, UserTaskProgress


@login_required
def dashboard(request):
    labs = Labs.objects.filter(is_active=True).order_by("order")

    labs_data = []
    for lab in labs:
        # Map lab icons based on lab name or add a default
        icon = "database"  # Default icon
        if "xss" in lab.name.lower():
            icon = "code"
        elif "csrf" in lab.name.lower():
            icon = "shield-check"
        elif "command" in lab.name.lower():
            icon = "terminal"

        # Get user progress for this lab
        try:
            user_lab_progress = UserLabProgress.objects.get(user=request.user, lab=lab)
            progress = user_lab_progress.calculate_progress_percentage()
        except UserLabProgress.DoesNotExist:
            progress = 0

        labs_data.append(
            {
                "id": lab.id,
                "title": lab.name,
                "description": lab.description,
                "icon": icon,
                "total_tasks": lab.total_tasks,
                "color": "#e74c3c",
                "progress": progress,
                "estimated_time": lab.estimated_time,
            }
        )

    # Calculate statistics
    total_labs = labs.count()
    total_questions = Tasks.objects.filter(lab__is_active=True, is_active=True).count()

    # Count unique users who have completed at least one lab
    completed_labs_count = UserLabProgress.objects.filter(lab__is_active=True, completed_at__isnull=False).count()

    # Calculate average completion percentage across all user lab progress
    user_lab_progresses = UserLabProgress.objects.filter(lab__is_active=True)
    if user_lab_progresses.exists():
        total_progress = sum(ulp.calculate_progress_percentage() for ulp in user_lab_progresses)
        avg_score = total_progress / user_lab_progresses.count()
    else:
        avg_score = 0

    # Calculate total estimated time for all labs
    total_estimated_time = labs.aggregate(total_time=Sum("estimated_time"))["total_time"] or 0

    # Count total task completions
    total_completions = UserTaskProgress.objects.filter(
        task__is_active=True, task__lab__is_active=True, completed=True
    ).count()

    # Count unique users who have started labs
    active_users = UserLabProgress.objects.filter(lab__is_active=True).values("user").distinct().count()

    stats = {
        "total_labs": total_labs,
        "total_questions": total_questions,
        "completed_labs_count": completed_labs_count,
        "avg_score": round(avg_score, 1),
        "total_estimated_time": total_estimated_time,
        "total_completions": total_completions,
        "active_users": active_users,
    }

    return render(request, "Simulation.html", {"labs": labs_data, "stats": stats})


@login_required
def lab_detail(request, lab_id):
    """Display detailed view of a specific lab with its tasks"""
    lab = get_object_or_404(Labs, id=lab_id, is_active=True)
    tasks = Tasks.objects.filter(lab=lab, is_active=True).order_by("order")
    completed_task_ids = set(
        UserTaskProgress.objects.filter(user=request.user, task__in=tasks, completed=True).values_list(
            "task_id", flat=True
        )
    )

    context = {
        "lab": lab,
        "tasks": tasks,
        "completed_task_ids": completed_task_ids,
    }
    return render(request, "lab_detail.html", context)


@login_required
def task_detail(request, lab_id, task_id):
    """Display individual task content"""
    lab = get_object_or_404(Labs, id=lab_id, is_active=True)
    task = get_object_or_404(Tasks, id=task_id, lab=lab, is_active=True)

    # Create or get user lab progress
    user_lab_progress, created = UserLabProgress.objects.get_or_create(user=request.user, lab=lab)

    # Get user task progress
    try:
        user_task_progress = UserTaskProgress.objects.get(user=request.user, task=task)
        task_completed = user_task_progress.completed
    except UserTaskProgress.DoesNotExist:
        task_completed = False

    try:
        content = task.content
    except TaskContent.DoesNotExist:
        content = None

    context = {
        "lab": lab,
        "task": task,
        "content": content,
        "task_completed": task_completed,
    }
    return render(request, "task_detail.html", context)


@login_required
def submit_answer(request, lab_id, task_id):
    """Handle task answer submission (MCQ or simulation results)"""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    lab = get_object_or_404(Labs, id=lab_id, is_active=True)
    task = get_object_or_404(Tasks, id=task_id, lab=lab, is_active=True)

    try:
        content = task.content
    except TaskContent.DoesNotExist:
        return JsonResponse({"error": "Task content not found"}, status=404)

    if task.task_type == "theory":
        user_answer = request.POST.get("answer", "").strip().upper()
        correct_answer = content.correct_answer.strip().upper()

        is_correct = user_answer == correct_answer

        # Update user task progress
        user_task_progress, created = UserTaskProgress.objects.get_or_create(user=request.user, task=task)
        user_task_progress.attempts += 1

        if is_correct and not user_task_progress.completed:
            user_task_progress.completed = True
            user_task_progress.completed_at = timezone.now()
            user_task_progress.user_answer = user_answer

        user_task_progress.save()

        # Create or update lab progress
        user_lab_progress, lab_created = UserLabProgress.objects.get_or_create(user=request.user, lab=lab)

        return JsonResponse(
            {
                "correct": is_correct,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "message": "Correct! Task completed!"
                if is_correct
                else f"Incorrect. The correct answer is {correct_answer}.",
                "task_completed": user_task_progress.completed,
            }
        )

    elif task.task_type == "simulation":
        user_payload = request.POST.get("payload", "").strip()

        simulation_config = content.simulation_config
        expected_payload = None
        if "success_payload" in simulation_config:
            expected_payload = simulation_config["success_payload"]
            is_correct = user_payload.strip().lower() == expected_payload.strip().lower()
        else:
            is_correct = False

        # Update user task progress
        user_task_progress, created = UserTaskProgress.objects.get_or_create(user=request.user, task=task)
        user_task_progress.attempts += 1

        if is_correct and not user_task_progress.completed:
            user_task_progress.completed = True
            user_task_progress.completed_at = timezone.now()
            user_task_progress.user_answer = user_payload

        user_task_progress.save()

        # Create or update lab progress
        user_lab_progress, lab_created = UserLabProgress.objects.get_or_create(user=request.user, lab=lab)

        return JsonResponse(
            {
                "correct": is_correct,
                "user_payload": user_payload,
                "expected_payload": expected_payload if expected_payload else "Not defined",
                "user_cleaned": user_payload.strip().lower() if expected_payload else "N/A",
                "expected_cleaned": expected_payload.strip().lower() if expected_payload else "N/A",
                "message": "Great job! You successfully completed the simulation!"
                if is_correct
                else "Try a different approach. Check the hints for guidance.",
                "task_completed": user_task_progress.completed,
            }
        )

    return JsonResponse({"error": "Invalid task type"}, status=400)
