import streamlit as st
import requests
import time
from datetime import datetime, timedelta

@st.cache_data(ttl=3600)
def fetch_repositories(token, org_name):
    """
    Fetch all repositories for the specified organization.
    
    Args:
        token (str): GitHub API token
        org_name (str): Name of the GitHub organization
        
    Returns:
        list: List of repository names
    """
    try:
        headers = {'Authorization': f'token {token}'} if token else {}
        url = f"https://api.github.com/orgs/{org_name}/repos?per_page=100"
        
        repos = []
        while url:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 403 and 'X-RateLimit-Remaining' in response.headers and int(response.headers['X-RateLimit-Remaining']) == 0:
                st.error("GitHub API rate limit exceeded. Please wait a few minutes and try again.")
                return repos
                
            response.raise_for_status()
            
            repos_data = response.json()
            repos.extend([repo['name'] for repo in repos_data])
            
            # Check if there are more pages
            if 'next' in response.links:
                url = response.links['next']['url']
            else:
                url = None
                
        return repos
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching repositories: {str(e)}")
        return []

@st.cache_data(ttl=3600)
def fetch_pull_requests(token, org_name, repo_name, max_age_years=10):
    """
    Fetch pull requests for a specific repository.
    
    Args:
        token (str): GitHub API token
        org_name (str): Name of the GitHub organization
        repo_name (str): Name of the repository
        max_age_years (int): Maximum age of PRs to fetch in years
        
    Returns:
        list: List of pull request data dictionaries
    """
    try:
        headers = {'Authorization': f'token {token}'} if token else {}
        
        # Calculate date threshold (10 years ago)
        threshold_date = datetime.now() - timedelta(days=365 * max_age_years)
        threshold_date_str = threshold_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Get all pull requests
        pulls = []
        page = 1
        url = f"https://api.github.com/repos/{org_name}/{repo_name}/pulls?state=all&per_page=100&page={page}"
        
        while url:
            response = requests.get(url, headers=headers)
            
            # Check if rate limit is exceeded
            if response.status_code == 403 and 'X-RateLimit-Remaining' in response.headers and int(response.headers['X-RateLimit-Remaining']) == 0:
                reset_time = datetime.fromtimestamp(int(response.headers['X-RateLimit-Reset']))
                sleep_time = (reset_time - datetime.now()).total_seconds() + 10
                
                st.error(f"GitHub API rate limit exceeded while fetching PRs for {repo_name}. Waiting to continue...")
                time.sleep(max(1, min(sleep_time, 300)))  # Sleep at least 1 second, at most 5 minutes
                continue
                
            response.raise_for_status()
            
            prs_data = response.json()
            if not prs_data:
                break
                
            for pr in prs_data:
                # Parse dates
                created_at = datetime.strptime(pr['created_at'], "%Y-%m-%dT%H:%M:%SZ")
                
                # Check if PR is older than threshold
                if created_at < threshold_date:
                    continue
                    
                # Parse other dates
                closed_at = datetime.strptime(pr['closed_at'], "%Y-%m-%dT%H:%M:%SZ") if pr['closed_at'] else None
                merged_at = datetime.strptime(pr['merged_at'], "%Y-%m-%dT%H:%M:%SZ") if pr['merged_at'] else None
                
                pr_data = {
                    'id': pr['number'],
                    'title': pr['title'],
                    'state': pr['state'],
                    'created_at': created_at,
                    'closed_at': closed_at,
                    'merged_at': merged_at,
                    'user': pr['user']['login'] if pr['user'] else 'Unknown',
                    'repository': repo_name
                }
                pulls.append(pr_data)
            
            # Check if there are more pages
            if 'next' in response.links:
                url = response.links['next']['url']
            else:
                url = None
                
            # Respect rate limit by sleeping if we're approaching the limit
            if 'X-RateLimit-Remaining' in response.headers and int(response.headers['X-RateLimit-Remaining']) < 10:
                reset_time = datetime.fromtimestamp(int(response.headers['X-RateLimit-Reset']))
                sleep_time = (reset_time - datetime.now()).total_seconds() + 10
                time.sleep(max(1, min(sleep_time, 60)))  # Sleep at least 1 second, at most 60
        
        return pulls
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching pull requests for {repo_name}: {str(e)}")
        return []

def check_rate_limit(token):
    """
    Check the current GitHub API rate limit status.
    
    Args:
        token (str): GitHub API token
        
    Returns:
        dict: Rate limit information
    """
    try:
        headers = {'Authorization': f'token {token}'} if token else {}
        response = requests.get('https://api.github.com/rate_limit', headers=headers)
        response.raise_for_status()
        
        rate_data = response.json()
        core_rate = rate_data['resources']['core']
        
        return {
            'limit': core_rate['limit'],
            'remaining': core_rate['remaining'],
            'reset_time': datetime.fromtimestamp(core_rate['reset']).strftime('%Y-%m-%d %H:%M:%S UTC')
        }
    except Exception as e:
        return {'error': str(e)}
