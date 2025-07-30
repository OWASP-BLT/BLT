# website/views/Simulation.py

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from website.models import Labs, TaskContent, Tasks


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

        labs_data.append(
            {
                "id": lab.id,
                "title": lab.name,
                "description": lab.description,
                "icon": icon,
                "total_tasks": lab.total_tasks,
                "color": "#e74c3c",
                "progress": 0,  # in next PR progress schema
                "estimated_time": lab.estimated_time,
            }
        )

    return render(request, "Simulation.html", {"labs": labs_data})


@login_required
def lab_detail(request, lab_id):
    """Display detailed view of a specific lab with its tasks"""
    lab = get_object_or_404(Labs, id=lab_id, is_active=True)
    tasks = Tasks.objects.filter(lab=lab, is_active=True).order_by("order")

    context = {
        "lab": lab,
        "tasks": tasks,
    }
    return render(request, "lab_detail.html", context)


@login_required
def task_detail(request, lab_id, task_id):
    """Display individual task content"""
    lab = get_object_or_404(Labs, id=lab_id, is_active=True)
    task = get_object_or_404(Tasks, id=task_id, lab=lab, is_active=True)

    try:
        content = task.content
    except TaskContent.DoesNotExist:
        content = None

    context = {
        "lab": lab,
        "task": task,
        "content": content,
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

        return JsonResponse(
            {
                "correct": is_correct,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "message": "Correct!" if is_correct else f"Incorrect. The correct answer is {correct_answer}.",
            }
        )

    elif task.task_type == "simulation":
        user_payload = request.POST.get("payload", "").strip()

        simulation_config = content.simulation_config
        print(simulation_config)

        if "success_payload" in simulation_config:
            expected_payload = simulation_config["success_payload"]
            is_correct = user_payload.strip().lower() == expected_payload.strip().lower()
        else:
            is_correct = False

        return JsonResponse(
            {
                "correct": is_correct,
                "user_payload": user_payload,
                "expected_payload": expected_payload if "success_payload" in simulation_config else "Not defined",
                "user_cleaned": user_payload.strip().lower() if "success_payload" in simulation_config else "N/A",
                "expected_cleaned": expected_payload.strip().lower()
                if "success_payload" in simulation_config
                else "N/A",
                "message": "Great job! You successfully completed the simulation."
                if is_correct
                else "Try a different approach. Check the hints for guidance.",
            }
        )

    return JsonResponse({"error": "Invalid task type"}, status=400)
