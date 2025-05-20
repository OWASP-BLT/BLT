# services/github_service.py
import logging
import requests
from django.conf import settings
from website.models import GitHubIssue, Repo, Contributor, UserProfile

logger = logging.getLogger(__name__)

class GitHubService:
    """
    Service for interacting with GitHub's API.
    """
    def __init__(self, token=None):
        """
        Initialize the GitHub service with a token.
        
        Args:
            token (str, optional): GitHub OAuth token. If None, uses the GITHUB_TOKEN from settings.
        """
        self.token = token or settings.GITHUB_TOKEN
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def fetch_assigned_issues(self, user_profile, store=True):
        """
        Fetch all issues assigned to the authenticated user from GitHub.
        
        Args:
            user_profile (UserProfile): The user profile to fetch issues for
            store (bool, optional): Whether to store the issues in the database. Defaults to True.
            
        Returns:
            list: List of fetched issues
        """
        if not user_profile:
            return {"error": "User profile is required"}
        
        # Check if the user has a GitHub account connected
        social_accounts = user_profile.user.socialaccount_set.filter(provider='github')
        if not social_accounts.exists():
            return {"error": "No GitHub account connected to this user"}
        
        # Get the user's GitHub username
        github_account = social_accounts.first()
        github_username = github_account.extra_data.get('login')
        
        if not github_username:
            return {"error": "Could not determine GitHub username"}
        
        # If we have an access token from the social account, use it instead of the global token
        if github_account.socialtoken_set.exists():
            token = github_account.socialtoken_set.first().token
            self.headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
        
        # Fetch assigned issues
        endpoint = f"{self.base_url}/issues"
        params = {
            "filter": "assigned",
            "state": "all",
            "per_page": 100,  # Max allowed by GitHub
            "page": 1
        }
        
        all_issues = []
        while True:
            try:
                response = requests.get(endpoint, headers=self.headers, params=params)
                response.raise_for_status()
                
                issues = response.json()
                if not issues:
                    break
                    
                all_issues.extend(issues)
                
                # Check if there are more pages
                if 'next' not in response.links:
                    break
                    
                # Move to the next page
                params['page'] += 1
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching assigned issues: {str(e)}")
                return {"error": f"Error fetching issues: {str(e)}"}
        
        # Store issues in the database if requested
        if store:
            self._store_issues(all_issues, user_profile)
        
        return all_issues
    
    def _store_issues(self, issues, user_profile):
        """
        Store GitHub issues in the database.
        
        Args:
            issues (list): List of issue data from GitHub API
            user_profile (UserProfile): User profile to associate with the issues
        """
        try:
            for issue_data in issues:
                # Skip pull requests if they're included in the response
                is_pull_request = 'pull_request' in issue_data
                issue_type = 'pull_request' if is_pull_request else 'issue'
                
                # Parse repository information from the repository URL
                repo_url = issue_data.get('repository_url', '')
                if not repo_url:
                    continue
                    
                repo_parts = repo_url.split('/')
                if len(repo_parts) < 2:
                    continue
                    
                owner, repo_name = repo_parts[-2], repo_parts[-1]
                
                # Get or create the repository
                repo, created = Repo.objects.get_or_create(
                    name=repo_name,
                    defaults={'github_id': repo_name, 'url': issue_data.get('html_url', '').split('/issues/')[0]}
                )
                
                # Get or create contributor information
                contributor = None
                if issue_data.get('user'):
                    contributor, created = Contributor.objects.get_or_create(
                        github_id=issue_data['user']['login'],
                        defaults={'name': issue_data['user']['login']}
                    )
                
                # Get or create the GitHub issue record
                issue, created = GitHubIssue.objects.update_or_create(
                    issue_id=issue_data['id'],
                    repo=repo,
                    defaults={
                        'title': issue_data['title'],
                        'body': issue_data.get('body', ''),
                        'state': issue_data['state'],
                        'type': issue_type,
                        'created_at': issue_data['created_at'],
                        'updated_at': issue_data['updated_at'],
                        'closed_at': issue_data.get('closed_at'),
                        'url': issue_data['html_url'],
                        'user_profile': user_profile,
                        'contributor': contributor,
                        'assignee': contributor if contributor and contributor.github_id == issue_data.get('assignee', {}).get('login') else None
                    }
                )
                
                # If this is a pull request, check if it's merged
                if is_pull_request and issue_data.get('merged_at'):
                    issue.is_merged = True
                    issue.merged_at = issue_data['merged_at']
                    issue.save()
                    
        except Exception as e:
            logger.error(f"Error storing GitHub issues: {str(e)}")
            return {"error": f"Error storing issues: {str(e)}"}