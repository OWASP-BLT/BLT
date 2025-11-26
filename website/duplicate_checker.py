"""
Duplicate Bug Report Checker

This module provides functionality to detect potential duplicate bug reports
using simple text searching and similarity matching.
"""

import logging
import re
from difflib import SequenceMatcher
from urllib.parse import urlparse

from django.core.cache import cache
from django.db.models import Q

from website.models import Issue

logger = logging.getLogger(__name__)


def normalize_text(text):
    """
    Normalize text for comparison by:
    - Converting to lowercase
    - Removing extra whitespace
    - Removing special characters
    
    Args:
        text: Input text string
        
    Returns:
        Normalized text string
    """
    if not text or not isinstance(text, str):
        return ""
    
    try:
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    except Exception as e:
        logger.warning(f"Error normalizing text: {e}")
        return ""


def extract_domain_from_url(url):
    """
    Extract the domain name from a URL for comparison.
    
    Args:
        url: URL string
        
    Returns:
        Domain name string
    """
    if not url or not isinstance(url, str):
        return ""
    
    try:
        # Add scheme if missing
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
            
        parsed = urlparse(url)
        # Get the hostname and remove 'www.' if present
        domain = parsed.hostname or parsed.path
        if domain:
            domain = domain.replace('www.', '').lower()
        return domain or ""
    except Exception as e:
        logger.warning(f"Error extracting domain from URL '{url}': {e}")
        return url


def calculate_similarity(text1, text2):
    """
    Calculate similarity ratio between two texts using SequenceMatcher.
    
    Args:
        text1: First text string
        text2: Second text string
        
    Returns:
        Float between 0 and 1, where 1 is identical
    """
    if not text1 or not text2:
        return 0.0
    
    try:
        normalized1 = normalize_text(text1)
        normalized2 = normalize_text(text2)
        
        if not normalized1 or not normalized2:
            return 0.0
        
        return SequenceMatcher(None, normalized1, normalized2).ratio()
    except Exception as e:
        logger.warning(f"Error calculating similarity: {e}")
        return 0.0


def extract_keywords(text, min_length=3):
    """
    Extract meaningful keywords from text for searching.
    Filters out common words and keeps words longer than min_length.
    """
    if not text:
        return []
    
    # Common words to ignore
    stop_words = {
        'the', 'is', 'at', 'which', 'on', 'in', 'a', 'an', 'and', 'or', 'but',
        'for', 'with', 'to', 'from', 'by', 'of', 'as', 'this', 'that', 'it',
        'are', 'was', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does',
        'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'bug',
        'issue', 'error', 'problem', 'found', 'when', 'not', 'working'
    }
    
    normalized = normalize_text(text)
    words = normalized.split()
    
    # Filter keywords
    keywords = [
        word for word in words 
        if len(word) >= min_length and word not in stop_words
    ]
    
    return keywords


def find_similar_bugs(url, description, domain=None, similarity_threshold=0.6, limit=10):
    """
    Find similar bug reports based on URL and description.
    
    Args:
        url: The URL where the bug was found
        description: The bug description
        domain: Optional Domain object to narrow search
        similarity_threshold: Minimum similarity score (0-1) to consider a match
        limit: Maximum number of similar bugs to return
    
    Returns:
        List of dictionaries containing similar bugs with similarity scores
    """
    # Input validation
    if not url or not description:
        logger.warning("find_similar_bugs called with empty url or description")
        return []
    
    # Validate and clamp parameters
    similarity_threshold = max(0.0, min(1.0, float(similarity_threshold)))
    limit = max(1, min(100, int(limit)))
    
    similar_bugs = []
    
    try:
        # Extract domain from URL
        target_domain = extract_domain_from_url(url)
        
        if not target_domain:
            logger.warning(f"Could not extract domain from URL: {url}")
            return []
        
        # Build query to find bugs on the same domain
        query = Q(is_hidden=False)
        
        if domain:
            query &= Q(domain=domain)
        elif target_domain:
            # Try to match by URL domain
            query &= (
                Q(url__icontains=target_domain) |
                Q(domain__url__icontains=target_domain) |
                Q(domain__name__icontains=target_domain)
            )
        
        # Get potential duplicate issues
        potential_duplicates = Issue.objects.filter(query).exclude(
            status='closed'
        ).select_related('user', 'domain').order_by('-created')[:100]
        
        # Extract keywords from the description for better matching
        description_keywords = extract_keywords(description)
        
        # Calculate similarity for each potential duplicate
        for issue in potential_duplicates:
            try:
                # Skip if issue has no description
                if not issue.description:
                    continue
                
                # Calculate description similarity
                desc_similarity = calculate_similarity(description, issue.description)
                
                # Calculate URL similarity
                url_similarity = calculate_similarity(url, issue.url)
                
                # Weighted average (description is more important)
                overall_similarity = (desc_similarity * 0.7) + (url_similarity * 0.3)
                
                # Check if any keywords match
                issue_keywords = extract_keywords(issue.description)
                keyword_matches = len(set(description_keywords) & set(issue_keywords))
                
                # Boost similarity if there are keyword matches
                if keyword_matches > 0:
                    keyword_boost = min(0.1 * keyword_matches, 0.2)
                    overall_similarity = min(overall_similarity + keyword_boost, 1.0)
                
                # Only include if above threshold
                if overall_similarity >= similarity_threshold:
                    similar_bugs.append({
                        'issue': issue,
                        'similarity': round(overall_similarity, 2),
                        'description_similarity': round(desc_similarity, 2),
                        'url_similarity': round(url_similarity, 2),
                        'keyword_matches': keyword_matches
                    })
            except Exception as e:
                logger.warning(f"Error processing issue {issue.id}: {e}")
                continue
        
        # Sort by similarity score (highest first)
        similar_bugs.sort(key=lambda x: x['similarity'], reverse=True)
        
        return similar_bugs[:limit]
        
    except Exception as e:
        logger.error(f"Error in find_similar_bugs: {e}", exc_info=True)
        return []


def check_for_duplicates(url, description, domain=None, threshold=0.7):
    """
    Check if a bug report is likely a duplicate.
    
    Args:
        url: The URL where the bug was found
        description: The bug description
        domain: Optional Domain object
        threshold: Similarity threshold for considering something a duplicate
    
    Returns:
        Dictionary with:
        - is_duplicate: Boolean indicating if likely duplicate
        - similar_bugs: List of similar bugs found
        - confidence: Confidence level (high/medium/low)
    """
    similar_bugs = find_similar_bugs(url, description, domain, similarity_threshold=0.5)
    
    if not similar_bugs:
        return {
            'is_duplicate': False,
            'similar_bugs': [],
            'confidence': 'none'
        }
    
    # Check highest similarity
    highest_similarity = similar_bugs[0]['similarity']
    
    # Determine confidence level
    if highest_similarity >= threshold:
        confidence = 'high'
        is_duplicate = True
    elif highest_similarity >= 0.6:
        confidence = 'medium'
        is_duplicate = True
    else:
        confidence = 'low'
        is_duplicate = False
    
    return {
        'is_duplicate': is_duplicate,
        'similar_bugs': similar_bugs,
        'confidence': confidence,
        'highest_similarity': highest_similarity
    }
