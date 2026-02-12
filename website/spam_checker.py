import logging
import re
from datetime import timedelta

from django.utils import timezone

from website.models import Issue

logger = logging.getLogger(__name__)

# Common spam patterns (case-insensitive)
SPAM_KEYWORDS = [
    r"buy\s+now",
    r"click\s+here",
    r"free\s+money",
    r"earn\s+\$?\d+",
    r"100%\s+free",
    r"act\s+now",
    r"limited\s+time\s+offer",
    r"congratulations.*won",
    r"nigerian?\s+prince",
    r"make\s+money\s+fast",
    r"work\s+from\s+home",
    r"bitcoin\s+doubler",
    r"crypto\s+giveaway",
    r"send\s+btc",
    r"wallet\s+recovery",
]

# Pre-compile patterns for performance
COMPILED_SPAM_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in SPAM_KEYWORDS]

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", re.IGNORECASE)

# Thresholds
MAX_URL_DENSITY = 3  # Max URLs before flagging
NEW_ACCOUNT_DAYS = 7  # Days to consider account "new"
SHORT_DESCRIPTION_LENGTH = 20  # Minimum meaningful description length
RAPID_SUBMISSION_MINUTES = 5  # Time window for rapid submission check
RAPID_SUBMISSION_LIMIT = 3  # Max submissions in rapid window
SPAM_SCORE_THRESHOLD = 3  # Score at or above this is flagged as spam


def count_urls(text):
    """Count the number of URLs in the given text."""
    if not text:
        return 0
    return len(URL_PATTERN.findall(text))


def check_spam_keywords(text):
    """Check text against known spam keyword patterns.

    Returns the number of spam patterns matched.
    """
    if not text:
        return 0
    matches = 0
    for pattern in COMPILED_SPAM_PATTERNS:
        if pattern.search(text):
            matches += 1
    return matches


def is_new_account(user):
    """Check if the user account was created within the last NEW_ACCOUNT_DAYS days."""
    if not user or not user.is_authenticated:
        return True  # Anonymous users are treated as new
    try:
        return user.date_joined >= timezone.now() - timedelta(days=NEW_ACCOUNT_DAYS)
    except AttributeError:
        return True


def check_rapid_submissions(user, reporter_ip):
    """Check if the user/IP has submitted too many reports in a short time window."""
    time_threshold = timezone.now() - timedelta(minutes=RAPID_SUBMISSION_MINUTES)

    if user and user.is_authenticated:
        recent_count = Issue.objects.filter(
            user=user,
            created__gte=time_threshold,
        ).count()
    elif reporter_ip:
        recent_count = Issue.objects.filter(
            reporter_ip_address=reporter_ip,
            created__gte=time_threshold,
        ).count()
    else:
        return False

    return recent_count >= RAPID_SUBMISSION_LIMIT


def is_repetitive_content(text):
    """Check if the text contains excessive repetition."""
    if not text or len(text) < 50:
        return False
    words = text.lower().split()
    if not words:
        return False
    unique_words = set(words)
    unique_ratio = len(unique_words) / len(words)
    return unique_ratio < 0.3  # Less than 30% unique words


def calculate_spam_score(description, markdown_description, user, reporter_ip):
    """Calculate a spam score for a bug report submission.

    Returns a dict with:
        - score (int): Total spam score (higher = more likely spam)
        - is_spam (bool): Whether the score exceeds the threshold
        - reasons (list[str]): Human-readable reasons for the score
    """
    score = 0
    reasons = []

    combined_text = f"{description or ''} {markdown_description or ''}"

    # Check URL density
    url_count = count_urls(combined_text)
    if url_count > MAX_URL_DENSITY:
        score += 2
        reasons.append(f"High URL density ({url_count} URLs found)")

    # Check spam keywords
    keyword_matches = check_spam_keywords(combined_text)
    if keyword_matches > 0:
        score += keyword_matches
        reasons.append(f"Matched {keyword_matches} spam keyword pattern(s)")

    # Check description quality
    desc_text = (description or "").strip()
    if len(desc_text) < SHORT_DESCRIPTION_LENGTH:
        score += 1
        reasons.append("Very short description")

    # Check for excessive caps
    alpha_chars = [c for c in desc_text if c.isalpha()]
    if len(alpha_chars) > 20:
        caps_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
        if caps_ratio > 0.7:
            score += 1
            reasons.append("Excessive use of capital letters")

    # Check for repetitive content
    if is_repetitive_content(combined_text):
        score += 2
        reasons.append("Repetitive content detected")

    # Check account age
    if is_new_account(user):
        score += 1
        reasons.append("New or anonymous account")

    # Check rapid submissions
    try:
        if check_rapid_submissions(user, reporter_ip):
            score += 2
            reasons.append("Rapid successive submissions detected")
    except Exception:
        logger.warning("Failed to check rapid submissions", exc_info=True)

    is_spam = score >= SPAM_SCORE_THRESHOLD

    if is_spam:
        logger.info(
            "Spam detected (score=%d, threshold=%d): %s",
            score,
            SPAM_SCORE_THRESHOLD,
            "; ".join(reasons),
        )

    return {
        "score": score,
        "is_spam": is_spam,
        "reasons": reasons,
    }
