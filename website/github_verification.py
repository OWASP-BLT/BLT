"""
Utilities for verifying GitHub profile linkbacks to BLT.
"""
import logging
import re
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def extract_github_username(github_url):
    """
    Extract GitHub username from a GitHub profile URL.
    
    Args:
        github_url: Full GitHub profile URL (e.g., https://github.com/username)
    
    Returns:
        GitHub username or None if invalid URL
    """
    if not github_url:
        return None
    
    try:
        parsed = urlparse(github_url)
        if parsed.netloc not in ["github.com", "www.github.com"]:
            return None
        
        # Extract username from path (e.g., /username or /username/)
        path_parts = [p for p in parsed.path.split("/") if p]
        if path_parts:
            return path_parts[0]
    except Exception as e:
        logger.error(f"Error parsing GitHub URL {github_url}: {e}")
    
    return None


def check_blt_link_in_text(text):
    """
    Check if text contains a link to BLT website.
    
    Args:
        text: Text content to check
    
    Returns:
        True if BLT link found, False otherwise
    """
    if not text:
        return False
    
    # Look for various forms of BLT links
    blt_patterns = [
        r"blt\.owasp\.org",
        r"owaspblt\.org",
        r"github\.com/OWASP-BLT",
    ]
    
    for pattern in blt_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False


def verify_github_linkback(github_username):
    """
    Verify that a GitHub profile links back to BLT.
    
    Checks the following locations:
    1. User's bio
    2. User's website/blog field
    3. User's company field
    4. Profile README (username/username repository)
    
    Args:
        github_username: GitHub username to check
    
    Returns:
        dict with 'verified' (bool) and 'found_in' (str) keys
    """
    if not github_username:
        return {"verified": False, "found_in": None}
    
    github_token = getattr(settings, "GITHUB_TOKEN", None)
    if not github_token or github_token == "blank":
        logger.warning("GitHub token not configured, linkback verification may be limited")
        headers = {}
    else:
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
    
    try:
        # 1. Check user profile (bio, website, etc.)
        profile_url = f"https://api.github.com/users/{github_username}"
        response = requests.get(profile_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch GitHub profile for {github_username}: {response.status_code}")
            return {"verified": False, "found_in": None}
        
        profile_data = response.json()
        
        # Check bio
        if check_blt_link_in_text(profile_data.get("bio")):
            return {"verified": True, "found_in": "bio"}
        
        # Check website/blog field
        if check_blt_link_in_text(profile_data.get("blog")):
            return {"verified": True, "found_in": "website"}
        
        # Check company field (sometimes users put links here)
        if check_blt_link_in_text(profile_data.get("company")):
            return {"verified": True, "found_in": "company"}
        
        # 2. Check profile README (username/username repository)
        readme_url = f"https://api.github.com/repos/{github_username}/{github_username}/readme"
        readme_response = requests.get(readme_url, headers=headers, timeout=10)
        
        if readme_response.status_code == 200:
            readme_data = readme_response.json()
            # README content is base64 encoded
            import base64
            
            readme_content = base64.b64decode(readme_data.get("content", "")).decode("utf-8")
            
            if check_blt_link_in_text(readme_content):
                return {"verified": True, "found_in": "profile_readme"}
        
        # No BLT link found
        return {"verified": False, "found_in": None}
        
    except requests.RequestException as e:
        logger.error(f"Error verifying GitHub linkback for {github_username}: {e}")
        return {"verified": False, "found_in": None}
    except Exception as e:
        logger.error(f"Unexpected error in GitHub linkback verification: {e}")
        return {"verified": False, "found_in": None}


def award_github_linking_tokens(user):
    """
    Award bacon tokens to user for linking their GitHub profile.
    
    Args:
        user: Django User object
    
    Returns:
        bool: True if tokens were awarded, False otherwise
    """
    from website.models import BaconToken, BaconEarning, Contribution

    try:
        # Check if user already received the reward
        user_profile = user.userprofile
        if user_profile.github_linking_reward_given:
            logger.info(f"User {user.username} already received GitHub linking reward")
            return False
        
        # Create a contribution record for this action
        contribution = Contribution.objects.create(
            user=user,
            title="Linked BLT Profile from GitHub",
            description=f"User {user.username} linked their BLT profile from their GitHub account, increasing platform visibility.",
            contribution_type="github_link",
            repository=None,
            github_username=extract_github_username(user_profile.github_url),
            created=timezone.now(),
            status="closed",
        )
        
        # Award tokens (5 BACON tokens for linking)
        token_amount = 5
        
        # Create BaconToken record
        BaconToken.objects.create(user=user, amount=token_amount, contribution=contribution)
        
        # Update or create BaconEarning record
        bacon_earning, created = BaconEarning.objects.get_or_create(
            user=user,
            defaults={"tokens_earned": token_amount}
        )
        if not created:
            bacon_earning.tokens_earned += token_amount
            bacon_earning.save()
        
        # Mark reward as given
        user_profile.github_linking_reward_given = True
        user_profile.github_linkback_verified = True
        user_profile.github_linkback_verified_at = timezone.now()
        user_profile.save(
            update_fields=[
                "github_linking_reward_given",
                "github_linkback_verified",
                "github_linkback_verified_at",
            ]
        )
        
        logger.info(f"Awarded {token_amount} BACON tokens to {user.username} for GitHub linking")
        return True
        
    except Exception as e:
        logger.error(f"Error awarding GitHub linking tokens to {user.username}: {e}")
        return False
