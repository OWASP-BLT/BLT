"""
Utilities for verifying GitHub profile linkbacks to BLT.
"""

import base64
import logging
import re
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.db import transaction
from django.db.models import F
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

    if not isinstance(github_url, str):
        logger.error(f"GitHub URL must be a string, got {type(github_url)}")
        return None

    parsed = urlparse(github_url)
    if parsed.netloc not in ["github.com", "www.github.com"]:
        return None

    # Extract username from path (e.g., /username or /username/)
    path_parts = [p for p in parsed.path.split("/") if p]
    if not path_parts:
        return None

    username = path_parts[0]
    # Validate GitHub username format: alphanumeric and hyphens, 1-39 characters
    if not re.match(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$", username):
        logger.warning(f"Invalid GitHub username format: {username}")
        return None

    return username


def check_blt_link_in_text(text):
    """
    Check if text contains a link to BLT website.

    Accepts the following formats (case-insensitive):
    - blt.owasp.org
    - owaspblt.org
    - github.com/OWASP-BLT/BLT

    Args:
        text: Text content to check

    Returns:
        True if BLT link found, False otherwise

    Examples:
        >>> check_blt_link_in_text("Check out blt.owasp.org!")
        True
        >>> check_blt_link_in_text("Visit https://blt.owasp.org")
        True
        >>> check_blt_link_in_text("See owaspblt.org for details")
        True
        >>> check_blt_link_in_text("Project: github.com/OWASP-BLT/BLT")
        True
        >>> check_blt_link_in_text("No BLT link here")
        False
    """
    if not text:
        return False

    # Look for various forms of BLT links with word boundaries for accuracy
    blt_patterns = [
        r"\bblt\.owasp\.org\b",
        r"\bowaspblt\.org\b",
        r"github\.com/OWASP-BLT/BLT\b",
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
    if not github_token or github_token in ("", "blank", "YOUR_TOKEN_HERE"):
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
            if response.status_code == 403 and "X-RateLimit-Remaining" in response.headers:
                logger.warning(
                    f"GitHub API rate limit exceeded for {github_username}. "
                    f"Resets at: {response.headers.get('X-RateLimit-Reset')}"
                )
            else:
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
            try:
                readme_content = base64.b64decode(readme_data.get("content", "")).decode("utf-8", errors="replace")
                if check_blt_link_in_text(readme_content):
                    return {"verified": True, "found_in": "profile_readme"}
            except (ValueError, UnicodeDecodeError) as e:
                logger.warning(f"Failed to decode README for {github_username}: {e}")

        # No BLT link found
        return {"verified": False, "found_in": None}

    except requests.RequestException as e:
        logger.error(f"GitHub API error for {github_username}: {e}")
        return {"verified": False, "found_in": None}
    except (ValueError, KeyError) as e:
        logger.error(f"Invalid response data for {github_username}: {e}")
        return {"verified": False, "found_in": None}


def award_github_linking_tokens(user, github_username=None):
    """
    Award bacon tokens to user for linking their GitHub profile.

    Uses database-level locking to prevent race conditions where multiple
    concurrent requests could award duplicate tokens.

    Args:
        user: Django User object
        github_username: GitHub username (optional, extracted from profile if not provided)

    Returns:
        bool: True if tokens were awarded, False otherwise
    """
    from website.models import BaconEarning, BaconToken, Contribution, UserProfile

    try:
        with transaction.atomic():
            # Lock the user profile row to prevent race conditions
            user_profile = UserProfile.objects.select_for_update().get(user=user)

            # Check if user already received the reward
            if user_profile.github_linking_reward_given:
                logger.info(f"User {user.username} already received GitHub linking reward")
                return False

            # Extract GitHub username if not provided
            if not github_username:
                github_username = extract_github_username(user_profile.github_url)

            # Create a contribution record for this action
            contribution = Contribution.objects.create(
                user=user,
                title="Linked BLT Profile from GitHub",
                description=f"User {user.username} added a link to BLT on their GitHub profile, increasing platform visibility.",
                contribution_type="github_link",
                repository=None,
                github_username=github_username,
                created=timezone.now(),
                status="closed",
            )

            # Award tokens (5 BACON tokens for linking)
            token_amount = 5

            # Create BaconToken record
            BaconToken.objects.create(user=user, amount=token_amount, contribution=contribution)

            # Update or create BaconEarning record atomically using F() expression
            bacon_earning, created = BaconEarning.objects.get_or_create(
                user=user, defaults={"tokens_earned": token_amount}
            )
            if not created:
                # Use F() expression for atomic update to prevent lost updates
                BaconEarning.objects.filter(pk=bacon_earning.pk).update(tokens_earned=F("tokens_earned") + token_amount)

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

    except UserProfile.DoesNotExist as e:
        logger.error(f"User profile not found for {user.username}: {e}")
        return False
    except Exception as e:
        # Log with full traceback for unexpected errors
        logger.exception(f"Unexpected error awarding GitHub linking tokens to {user.username}: {e}")
        # Re-raise to alert about programming errors during development
        if settings.DEBUG:
            raise
        return False
