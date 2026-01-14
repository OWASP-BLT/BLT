"""
Integration module for trademark matching with BLT models.
This provides Django-aware wrapper functions for the core matching service.
"""

from typing import List

from website.services.trademark_matching import TrademarkCandidate, TrademarkMatcher


def get_matches_for_website(
    website_name: str,
    threshold: float = 85.0,
) -> List[TrademarkCandidate]:
    """
    Get trademark matches for a website/company.

    This is the primary API for integration with BLT models.

    Args:
        website_name: Name of the website or company to check.
        threshold: Match threshold (0-100). Default 85.0.

    Returns:
        List of TrademarkCandidate objects representing potential matches.
    """
    matcher = TrademarkMatcher(threshold=threshold)

    # TODO: In production, fetch trademarks from USPTO API or database
    # For now, using sample data
    from website.services.trademark_matching import SAMPLE_TRADEMARKS

    return matcher.match(website_name, SAMPLE_TRADEMARKS)


def check_trademark_conflict(
    website_name: str,
    similarity_threshold: float = 90.0,
) -> bool:
    """
    Check if a website name has a high-confidence trademark conflict.

    Args:
        website_name: Name to check.
        similarity_threshold: Score threshold for flagging conflict. Default 90.0.

    Returns:
        True if a high-confidence match is found, False otherwise.
    """
    matches = get_matches_for_website(website_name, threshold=similarity_threshold)
    return len(matches) > 0


def get_trademark_report(website_name: str) -> dict:
    """
    Generate a detailed trademark analysis report for a website.

    Args:
        website_name: Name to analyze.

    Returns:
        Dictionary with analysis results.
    """
    matches = get_matches_for_website(website_name)

    has_risk = len(matches) > 0
    highest_score = matches[0].score if matches else 0.0

    return {
        "website_name": website_name,
        "has_trademark_risk": has_risk,
        "highest_match_score": highest_score,
        "total_matches": len(matches),
        "matches": [
            {
                "name": m.name,
                "score": m.score,
            }
            for m in matches
        ],
        "recommendation": (
            "INVESTIGATE: Potential trademark conflict detected"
            if has_risk
            else "CLEAR: No trademark conflicts detected"
        ),
    }
