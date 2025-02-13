from django.shortcuts import render

def slack_integration(request):
    """Render the Slack integration page with available commands."""
    slack_commands = [
        {"command": "/report", "description": "Report a new bug."},
        {"command": "/status", "description": "Check the status of a reported bug."},
        {"command": "/help", "description": "List all available commands."},
    ]
    
    return render(request, 'slack_integration.html', {"commands": slack_commands})
