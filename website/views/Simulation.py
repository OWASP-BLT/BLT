# website/views/Simulation.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# from website.models import Lab, UserProgress


@login_required
def dashboard(request):
    labs_data = [
        {
            "id": "sql-injection",
            "title": "SQL Injection",
            "description": "Learn about SQL injection vulnerabilities and how to exploit them",
            "icon": "database",  # For heroicons
            "total_tasks": 10,
            "color": "#e74c3c",
            "progress": 0,  # We'll calculate this
        },
        {
            "id": "xss",
            "title": "Cross-Site Scripting (XSS)",
            "description": "Master the art of identifying and exploiting XSS vulnerabilities",
            "icon": "code",
            "total_tasks": 8,
            "color": "#e74c3c",
            "progress": 0,
        },
        {
            "id": "csrf",
            "title": "Cross-Site Request Forgery",
            "description": "Understand CSRF attacks and prevention techniques",
            "icon": "shield-check",
            "total_tasks": 6,
            "color": "#e74c3c",
            "progress": 0,
        },
        {
            "id": "command-injection",
            "title": "Command Injection",
            "description": "Learn about command injection vulnerabilities and exploitation",
            "icon": "terminal",
            "total_tasks": 7,
            "color": "#e74c3c",
            "progress": 0,
        },
    ]

    return render(request, "Simulation.html", {"labs": labs_data})
