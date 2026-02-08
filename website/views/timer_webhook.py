"""
Webhook endpoint for GitHub integration to automatically start timers
when issues are assigned or moved to "In Progress"
"""
import json
import logging
from datetime import timedelta

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from website.models import TimeLog

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def github_timer_webhook(request):
    """
    Webhook endpoint to handle GitHub events and automatically start/stop timers
    
    Supported events:
    - issues.assigned: Start timer when issue is assigned to a user
    - project_v2_item.edited: Start timer when issue moved to "In Progress"
    - issues.closed: Stop active timer for the issue
    - issues.unassigned: Pause timer when issue is unassigned
    """
    try:
        payload = json.loads(request.body)
        event_type = request.headers.get('X-GitHub-Event', '')
        
        logger.info(f"Received GitHub webhook event: {event_type}")
        
        if event_type == 'issues':
            return handle_issue_event(payload)
        elif event_type == 'project_v2_item':
            return handle_project_event(payload)
        else:
            return JsonResponse({
                'status': 'ignored',
                'message': f'Event type {event_type} not handled'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


def handle_issue_event(payload):
    """Handle GitHub issue events"""
    action = payload.get('action')
    issue = payload.get('issue', {})
    assignee = payload.get('assignee', {})
    
    issue_number = issue.get('number')
    issue_url = issue.get('html_url')
    repo_full_name = payload.get('repository', {}).get('full_name')
    
    if not issue_number or not issue_url or not repo_full_name:
        return JsonResponse({'error': 'Missing required issue data'}, status=400)
    
    if action == 'assigned' and assignee:
        # Start timer when issue is assigned
        github_username = assignee.get('login')
        return start_timer_for_user(
            github_username=github_username,
            issue_number=issue_number,
            issue_url=issue_url,
            repo_full_name=repo_full_name
        )
    
    elif action == 'closed':
        # Stop active timer for this issue
        return stop_timer_for_issue(issue_number, repo_full_name)
    
    elif action == 'unassigned':
        # Pause timer when issue is unassigned
        return pause_timer_for_issue(issue_number, repo_full_name)
    
    return JsonResponse({
        'status': 'ignored',
        'message': f'Issue action {action} not handled'
    })


def handle_project_event(payload):
    """Handle GitHub Project V2 events"""
    action = payload.get('action')
    
    if action not in ['edited', 'converted']:
        return JsonResponse({
            'status': 'ignored',
            'message': f'Project action {action} not handled'
        })
    
    project_item = payload.get('project_v2_item', {})
    content_node_id = project_item.get('content_node_id')
    
    # Extract issue information from the project item
    # This would require additional GraphQL query in production
    # For now, we'll return a success response
    
    return JsonResponse({
        'status': 'success',
        'message': 'Project event received',
        'note': 'Implement GraphQL query to fetch issue details and start timer'
    })


def start_timer_for_user(github_username, issue_number, issue_url, repo_full_name):
    """Start a timer for a user when assigned to an issue"""
    try:
        # Try to find user by username match
        user = User.objects.filter(username__iexact=github_username).first()
        
        if not user:
            return JsonResponse({
                'status': 'warning',
                'message': f'User not found for GitHub username: {github_username}. Please create a user with username "{github_username}" in BLT.'
            })
        
        # Check if there's already an active timer for this issue
        existing_timer = TimeLog.objects.filter(
            user=user,
            github_issue_number=issue_number,
            github_repo=repo_full_name,
            end_time__isnull=True
        ).first()
        
        if existing_timer:
            return JsonResponse({
                'status': 'info',
                'message': 'Timer already running for this issue',
                'timer_id': existing_timer.id
            })
        
        # Create new timer
        timer = TimeLog.objects.create(
            user=user,
            start_time=timezone.now(),
            github_issue_url=issue_url,
            github_issue_number=issue_number,
            github_repo=repo_full_name
        )
        
        logger.info(f"Started timer {timer.id} for user {user.username} on issue #{issue_number}")
        
        return JsonResponse({
            'status': 'success',
            'message': 'Timer started successfully',
            'timer_id': timer.id,
            'user': user.username,
            'issue': f"{repo_full_name}#{issue_number}"
        })
        
    except Exception as e:
        logger.error(f"Error starting timer: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def stop_timer_for_issue(issue_number, repo_full_name):
    """Stop active timer for an issue"""
    try:
        active_timers = TimeLog.objects.filter(
            github_issue_number=issue_number,
            github_repo=repo_full_name,
            end_time__isnull=True
        )
        
        stopped_count = 0
        for timer in active_timers:
            timer.end_time = timezone.now()
            timer.save()
            stopped_count += 1
            logger.info(f"Stopped timer {timer.id} for issue #{issue_number}")
        
        if stopped_count == 0:
            return JsonResponse({
                'status': 'info',
                'message': 'No active timers found for this issue'
            })
        
        return JsonResponse({
            'status': 'success',
            'message': f'Stopped {stopped_count} timer(s)',
            'issue': f"{repo_full_name}#{issue_number}"
        })
        
    except Exception as e:
        logger.error(f"Error stopping timer: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def pause_timer_for_issue(issue_number, repo_full_name):
    """Pause active timer for an issue"""
    try:
        active_timers = TimeLog.objects.filter(
            github_issue_number=issue_number,
            github_repo=repo_full_name,
            end_time__isnull=True,
            is_paused=False
        )
        
        paused_count = 0
        for timer in active_timers:
            timer.pause()
            paused_count += 1
            logger.info(f"Paused timer {timer.id} for issue #{issue_number}")
        
        if paused_count == 0:
            return JsonResponse({
                'status': 'info',
                'message': 'No active timers found to pause'
            })
        
        return JsonResponse({
            'status': 'success',
            'message': f'Paused {paused_count} timer(s)',
            'issue': f"{repo_full_name}#{issue_number}"
        })
        
    except Exception as e:
        logger.error(f"Error pausing timer: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
