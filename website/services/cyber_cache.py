"""Helpers for organization cyber dashboard cache management."""

from django.core.cache import cache


def get_org_cyber_cache_key(organization_id):
    """Return the cache key used for an organization's cyber dashboard metrics."""
    return f"org_cyber_dns:{organization_id}"


def invalidate_org_cyber_cache(organization_id):
    """Invalidate cached cyber dashboard metrics for a specific organization."""
    if organization_id:
        cache.delete(get_org_cyber_cache_key(organization_id))
