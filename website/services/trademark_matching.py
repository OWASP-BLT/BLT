"""
Trademark matching service for BLT.
Matches company names against known trademarks using fuzzy string matching.
"""

from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class TrademarkCandidate:
    """Represents a potential trademark match."""

    name: str
    score: float


class TrademarkMatcher:
    """Core trademark matching engine using fuzzy matching."""

    def __init__(self, threshold: float = 85.0) -> None:
        """
        Initialize the matcher.

        Args:
            threshold: Minimum match score (0-100) to consider as a match.
                      Default 85 is conservative to avoid false positives.
        """
        self.threshold = threshold

    def normalize(self, text: str) -> str:
        """
        Normalize text for comparison by removing non-alphanumeric chars
        and lowercasing.

        Args:
            text: Input text to normalize.

        Returns:
            Normalized string with only alphanumeric characters, lowercase.
        """
        return "".join(ch for ch in text.lower() if ch.isalnum())

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance between two strings.
        This is a pure Python implementation (no external dependency).

        Args:
            s1: First string.
            s2: Second string.

        Returns:
            Levenshtein distance (integer).
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # j+1 instead of j since previous_row and current_row are one character longer
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _similarity_score(self, s1: str, s2: str) -> float:
        """
        Calculate similarity score as percentage (0-100).
        Based on Levenshtein distance.

        Args:
            s1: First string.
            s2: Second string.

        Returns:
            Similarity score from 0 to 100.
        """
        distance = self._levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))

        if max_len == 0:
            return 100.0

        return ((max_len - distance) / max_len) * 100

    def match(self, company: str, trademarks: Iterable[str], limit: int = 10) -> List[TrademarkCandidate]:
        """
        Find potential trademark matches for a company name.

        Args:
            company: Company/website name to search for.
            trademarks: Iterable of known trademark names to search against.
            limit: Maximum number of results to return. Default 10.

        Returns:
            List of TrademarkCandidate objects sorted by score (highest first),
            filtered by the threshold. Maximum `limit` results.
        """
        norm_company = self.normalize(company)

        if not norm_company:
            return []

        results = []
        for trademark in trademarks:
            norm_trademark = self.normalize(trademark)
            if not norm_trademark:
                continue

            score = self._similarity_score(norm_company, norm_trademark)
            if score >= self.threshold:
                results.append(TrademarkCandidate(name=trademark, score=round(score, 2)))

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:limit]


# Sample trademark database (stub; would be replaced by USPTO API or DB query)
SAMPLE_TRADEMARKS = [
    "BugHeist",
    "Bug Hunt",
    "BugBounty",
    "Security Bugs",
    "VulnerabilityScan",
    "PenTest Pro",
    "Exploit Kit",
    "Security Audit",
    "Threat Intelligence",
    "Malware Analyzer",
]


def get_trademark_matches(company_name: str) -> List[TrademarkCandidate]:
    """
    Convenience function to get trademark matches using defaults.

    Args:
        company_name: Company name to search for.

    Returns:
        List of matching trademarks.
    """
    matcher = TrademarkMatcher(threshold=85.0)
    return matcher.match(company_name, SAMPLE_TRADEMARKS)
