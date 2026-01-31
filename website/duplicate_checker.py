"""
Duplicate Bug Report Checker

This module provides functionality to detect potential duplicate bug reports
using a Strategy pattern to support multiple detection algorithms (e.g., SequenceMatcher, Vector Search).
"""

import logging
import re
from abc import ABC, abstractmethod
from difflib import SequenceMatcher
from urllib.parse import urlparse

from django.db.models import Q

from website.models import Issue

logger = logging.getLogger(__name__)

# Common stop words for keyword extraction (module-level constant for performance)
STOP_WORDS = {
    "the",
    "is",
    "at",
    "which",
    "on",
    "in",
    "a",
    "an",
    "and",
    "or",
    "but",
    "for",
    "with",
    "to",
    "from",
    "by",
    "of",
    "as",
    "this",
    "that",
    "it",
    "are",
    "was",
    "were",
    "been",
    "be",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "can",
    "bug",
    "issue",
    "error",
    "problem",
    "found",
    "when",
    "not",
    "working",
}


class DuplicateDetectionStrategy(ABC):
    """
    Abstract Base Class for duplicate detection strategies.
    This allows us to easily swap between simple string matching and advanced AI/Vector search.
    """

    @abstractmethod
    def find_similar(self, url, description, domain=None, threshold=0.6, limit=10):
        """
        Find similar bug reports.

        Args:
            url: The URL where the bug was found
            description: The bug description
            domain: Optional Domain object
            threshold: Minimum similarity score (0-1)
            limit: Maximum results

        Returns:
            List of dictionaries containing similar bugs
        """
        pass


class SequenceMatcherStrategy(DuplicateDetectionStrategy):
    """
    Classic implementation using Python's difflib.SequenceMatcher.
    Good for exact or near-exact text matches but fails on semantic similarity.
    """

    def normalize_text(self, text):
        if not text or not isinstance(text, str):
            return ""
        try:
            text = text.lower()
            text = re.sub(r"[^\w\s]", " ", text)
            text = " ".join(text.split())
            return text
        except (TypeError, AttributeError, UnicodeError) as e:
            logger.warning("Error normalizing text: %s", e)
            return ""

    def extract_domain_from_url(self, url):
        if not url or not isinstance(url, str):
            return ""
        try:
            # Handle protocol-relative URLs (e.g. //example.com)
            if url.startswith("//"):
                url = f"https:{url}"
            # Add scheme if missing entirely (and not just a path)
            elif not url.startswith(("http://", "https://")) and "." in url:
                url = f"https://{url}"

            parsed = urlparse(url)
            domain = parsed.hostname or parsed.path
            if domain:
                domain = domain.replace("www.", "").lower()
            return domain or ""
        except Exception as e:
            logger.warning("Error extracting domain from URL '%s': %s", url, e)
            return ""

    def calculate_similarity(self, text1, text2):
        if not text1 or not text2:
            return 0.0
        try:
            normalized1 = self.normalize_text(text1)
            normalized2 = self.normalize_text(text2)
            if not normalized1 or not normalized2:
                return 0.0
            return SequenceMatcher(None, normalized1, normalized2).ratio()
        except Exception as e:
            logger.warning("Error calculating similarity: %s", e)
            return 0.0

    def extract_keywords(self, text, min_length=3):
        if not text:
            return []
        normalized = self.normalize_text(text)
        words = normalized.split()
        return [word for word in words if len(word) >= min_length and word not in STOP_WORDS]

    def find_similar(self, url, description, domain=None, threshold=0.6, limit=10):
        if not description:
            logger.warning("find_similar called with empty description")
            return []

        similar_bugs = []

        try:
            # Guard against invalid inputs for threshold/limit
            try:
                threshold = max(0.0, min(1.0, float(threshold)))
                limit = max(1, min(100, int(limit)))
            except (ValueError, TypeError):
                # Fallback to defaults to prevent crash
                threshold = 0.6
                limit = 10
                logger.warning("Invalid threshold or limit provided to duplicate checker. Using defaults.")

            target_domain = None
            if url:
                target_domain = self.extract_domain_from_url(url)

            query = Q(is_hidden=False)
            if domain:
                query &= Q(domain=domain)
            elif target_domain:
                query &= (
                    Q(url__icontains=target_domain)
                    | Q(domain__url__icontains=target_domain)
                    | Q(domain__name__icontains=target_domain)
                )

            potential_duplicates = (
                Issue.objects.filter(query)
                .exclude(status__in=["closed", "close"])
                .select_related("user", "domain")
                .order_by("-created")[:100]
            )

            description_keywords = self.extract_keywords(description)

            for issue in potential_duplicates:
                try:
                    if not issue.description:
                        continue

                    desc_similarity = self.calculate_similarity(description, issue.description)
                    url_similarity = 0.0
                    if url:
                        url_similarity = self.calculate_similarity(url, issue.url)

                    if url:
                        overall_similarity = (desc_similarity * 0.7) + (url_similarity * 0.3)
                    else:
                        overall_similarity = desc_similarity

                    issue_keywords = self.extract_keywords(issue.description)
                    keyword_matches = len(set(description_keywords) & set(issue_keywords))

                    if keyword_matches > 0:
                        keyword_boost = min(0.1 * keyword_matches, 0.2)
                        overall_similarity = min(overall_similarity + keyword_boost, 1.0)

                    if overall_similarity >= threshold:
                        similar_bugs.append(
                            {
                                "issue": issue,
                                "similarity": round(overall_similarity, 2),
                                "description_similarity": round(desc_similarity, 2),
                                "url_similarity": round(url_similarity, 2),
                                "keyword_matches": keyword_matches,
                            }
                        )
                except Exception as e:
                    logger.warning("Error processing issue %s: %s", issue.id, e)
                    continue

            similar_bugs.sort(key=lambda x: x["similarity"], reverse=True)
            return similar_bugs[:limit]

        except Exception as e:
            logger.error("Error in SequenceMatcherStrategy.find_similar: %s", e, exc_info=True)
            return []


class VectorSearchStrategy(DuplicateDetectionStrategy):
    """
    Placeholder for AI-Powered Semantic Search using Vector Embeddings.
    This will leverage FAISS or a Vector DB in future implementations.
    """

    def find_similar(self, url, description, domain=None, threshold=0.6, limit=10):
        # Prevent silent failure/confusion if accidentally enabled before implementation
        raise NotImplementedError(
            "VectorSearchStrategy is not yet implemented. "
            "Use SequenceMatcherStrategy or contribute to implement this feature."
        )


def get_duplicate_strategy() -> DuplicateDetectionStrategy:
    """
    Factory method to get the active strategy.
    Switches based on DUPLICATE_DETECTION_STRATEGY setting.
    Defaults to 'sequence_matcher' if not specified.
    """
    from django.conf import settings
    
    strategy_name = getattr(settings, "DUPLICATE_DETECTION_STRATEGY", "sequence_matcher")
    
    if strategy_name == "vector_search":
        return VectorSearchStrategy()
    
    # Default to legacy sequence matcher
    return SequenceMatcherStrategy()


# -----------------------------------------------------------------------------
# Public API Functions (Facades)
# These maintain backward compatibility with the rest of the app
# -----------------------------------------------------------------------------


def find_similar_bugs(url, description, domain=None, similarity_threshold=0.6, limit=10):
    """
    Facade for finding similar bugs using the active strategy.
    """
    strategy = get_duplicate_strategy()
    return strategy.find_similar(url, description, domain, similarity_threshold, limit)


def check_for_duplicates(url, description, domain=None, threshold=0.7):
    """
    Check if a bug report is likely a duplicate.
    Uses the active strategy via find_similar_bugs.
    """
    # Use a lower threshold (0.5) for initial search to catch medium confidence matches
    # The threshold parameter is used to determine "high" vs "medium" confidence
    similar_bugs = find_similar_bugs(url, description, domain, similarity_threshold=0.5)

    if not similar_bugs:
        return {"is_duplicate": False, "similar_bugs": [], "confidence": "none"}

    # Check highest similarity
    highest_similarity = similar_bugs[0]["similarity"]

    # Determine confidence level
    if highest_similarity >= threshold:
        confidence = "high"
        is_duplicate = True
    elif highest_similarity >= 0.6:
        confidence = "medium"
        is_duplicate = True
    else:
        confidence = "low"
        is_duplicate = False

    return {
        "is_duplicate": is_duplicate,
        "similar_bugs": similar_bugs,
        "confidence": confidence,
        "highest_similarity": highest_similarity,
    }


def format_similar_bug(bug_info, truncate_description=200):
    """
    Helper function to format similar bug data consistently.
    Used by both API views and form views.
    """
    issue = bug_info["issue"]
    description = issue.description
    if truncate_description > 0 and len(description) > truncate_description:
        description = description[:truncate_description] + "..."

    return {
        "id": issue.id,
        "url": issue.url,
        "description": description,
        "similarity": bug_info["similarity"],
        "similarity_percent": int(bug_info["similarity"] * 100),
        "description_similarity": bug_info.get("description_similarity", 0),
        "url_similarity": bug_info.get("url_similarity", 0),
        "keyword_matches": bug_info.get("keyword_matches", 0),
        "status": issue.status,
        "created": issue.created.isoformat() if hasattr(issue.created, "isoformat") else str(issue.created),
        "user": issue.user.username if issue.user else "Anonymous",
        "label": issue.get_label_display() if hasattr(issue, "get_label_display") else "",
        "verified": getattr(issue, "verified", False),
        "upvotes": issue.upvoted.count() if hasattr(issue, "upvoted") else 0,
    }
