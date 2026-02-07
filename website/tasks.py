import logging
import threading
from datetime import datetime
from urllib.parse import urlparse
import requests
from django.conf import settings
from django.db import transaction

from website.models import Repo, Project, Contributor, ContributorStats

logger = logging.getLogger(__name__)


def recalculate_repo_stats(repo_id):
    """
    Recalculate contributor statistics for a specific repository.
    """
    try:
        repo = Repo.objects.get(id=repo_id)
    except Repo.DoesNotExist:
        logger.error(f"Repo with id {repo_id} does not exist")
        return {'status': 'error', 'message': 'Repo not found'}
    
    if not repo.repo_url:
        logger.warning(f"Repo {repo_id} has no repo_url, skipping stats recalculation")
        return {'status': 'skipped', 'message': 'No repo_url configured'}
    
    # Parse owner and repo name from URL
    try:
        path_parts = urlparse(repo.repo_url).path.strip('/').split('/')
        if len(path_parts) < 2:
            logger.error(f"Invalid repo URL format: {repo.repo_url}")
            return {'status': 'error', 'message': 'Invalid repo URL format'}
        
        owner = path_parts[0]
        repo_name = path_parts[1]
    except Exception as e:
        logger.error(f"Error parsing repo URL {repo.repo_url}: {str(e)}")
        return {'status': 'error', 'message': f'Error parsing URL: {str(e)}'}
    
    # Get GitHub token from settings
    github_token = getattr(settings, 'GITHUB_TOKEN', None)
    if not github_token:
        logger.error("GITHUB_TOKEN not configured in settings")
        return {'status': 'error', 'message': 'GitHub token not configured'}
    
    # Calculate since date (start of current month)
    today = datetime.now()
    since_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Fetch commits from GitHub API
    url = f"https://api.github.com/repos/{owner}/{repo_name}/commits"
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    params = {
        'since': since_date.isoformat(),
        'per_page': 100
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        commits = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"GitHub API error for {owner}/{repo_name}: {str(e)}")
        return {'status': 'error', 'message': f'GitHub API error: {str(e)}'}
    
    # Aggregate stats by contributor
    contributor_data = {}
    for commit in commits:
        if not commit.get('author'):
            continue
        
        author = commit['author']
        github_id = author.get('id')
        login = author.get('login')
        
        if not github_id or not login:
            continue
        
        if github_id not in contributor_data:
            contributor_data[github_id] = {
                'login': login,
                'avatar_url': author.get('avatar_url', ''),
                'github_url': author.get('html_url', f'https://github.com/{login}'),
                'type': author.get('type', 'User'),  # User or Bot
                'commits': 0
            }
        
        contributor_data[github_id]['commits'] += 1
    
    # Update database in transaction
    try:
        with transaction.atomic():
            for github_id, data in contributor_data.items():
                # Create or update Contributor
                # FIXED: Now providing ALL required fields
                contributor, created = Contributor.objects.get_or_create(
                    github_id=github_id,
                    defaults={
                        'name': data['login'],
                        'avatar_url': data['avatar_url'],
                        'github_url': data['github_url'],  # ✓ ADDED
                        'contributor_type': data['type'],  # ✓ ADDED
                        'contributions': data['commits']   # ✓ ADDED (this was the error!)
                    }
                )
                
                # If contributor already exists, update contributions
                if not created:
                    contributor.contributions += data['commits']
                    contributor.save(update_fields=['contributions'])
                
                # Create or update ContributorStats for today
                ContributorStats.objects.update_or_create(
                    contributor=contributor,
                    repo=repo,
                    date=today.date(),
                    granularity='day',
                    defaults={
                        'commits': data['commits']
                    }
                )
        
        logger.info(f"Successfully updated stats for {len(contributor_data)} contributors in repo {repo_id}")
        return {
            'status': 'success',
            'message': f'Updated stats for {len(contributor_data)} contributors'
        }
    
    except Exception as e:
        logger.error(f"Database error updating stats for repo {repo_id}: {str(e)}")
        return {'status': 'error', 'message': f'Database error: {str(e)}'}


def trigger_project_stats_update(project_id):
    """
    Trigger stats recalculation for all repos in a project.
    Runs synchronously but can be called in a background thread.
    """
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        logger.error(f"Project with id {project_id} does not exist")
        return {'status': 'error', 'message': 'Project not found'}
    
    repos = project.repos.all()
    repo_count = repos.count()
    
    if repo_count == 0:
        logger.info(f"No repos found for project {project_id}")
        return {'status': 'skipped', 'message': 'No repos in project'}
    
    # Process each repo synchronously
    results = []
    for repo in repos:
        logger.info(f"Recalculating stats for repo {repo.id}")
        result = recalculate_repo_stats(repo.id)
        results.append(result)
    
    success_count = sum(1 for r in results if r.get('status') == 'success')
    logger.info(f"Completed stats recalculation for {success_count}/{repo_count} repos in project {project_id}")
    
    return {
        'status': 'success',
        'message': f'Processed {repo_count} repos, {success_count} successful',
        'results': results
    }


def trigger_project_stats_update_async(project_id):
    """
    Trigger stats recalculation in a background thread to avoid blocking the webhook handler.
    """
    def run_in_background():
        try:
            trigger_project_stats_update(project_id)
        except Exception as e:
            logger.error(f"Error in background stats update for project {project_id}: {str(e)}")
    
    # Start background thread
    thread = threading.Thread(target=run_in_background, daemon=True)
    thread.start()
    logger.info(f"Started background thread for project {project_id} stats update")