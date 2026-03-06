"""Signals for invalidating organization cyber dashboard cache on domain changes."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from website.models import Domain
from website.services.cyber_cache import invalidate_org_cyber_cache


@receiver(post_save, sender=Domain)
def invalidate_cyber_cache_on_domain_save(sender, instance, **kwargs):  # noqa: ARG001
    """Invalidate organization cyber cache when a domain is created or updated."""
    invalidate_org_cyber_cache(instance.organization_id)


@receiver(post_delete, sender=Domain)
def invalidate_cyber_cache_on_domain_delete(sender, instance, **kwargs):  # noqa: ARG001
    """Invalidate organization cyber cache when a domain is deleted."""
    invalidate_org_cyber_cache(instance.organization_id)
