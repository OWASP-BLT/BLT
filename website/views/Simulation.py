# website/views/Simulation.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from website.models import Labs


@login_required
def dashboard(request):
    # Get all active labs ordered by their order field
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
                "progress": 0,  # We'll implement progress tracking in the next PR_forward
                "estimated_time": lab.estimated_time,
            }
        )

    return render(request, "Simulation.html", {"labs": labs_data})
