"""
Django signals for automatic trademark checking when organizations/websites are created/updated.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from website.models import Organization, TrademarkMatch
from website.services.trademark_integration import get_matches_for_website


@receiver(post_save, sender=Organization)
def check_organization_trademarks(sender, instance, created, **kwargs):
    if not instance.name:
        return

    _perform_trademark_check(
        name=instance.name,
        organization=instance,
    )


def check_website_trademarks(sender, instance, created, **kwargs):
    """
    When a website is created or updated, automatically check for trademark conflicts.
    """
    if not instance.name:
        return

    # Skip if already checked very recently
    recent_check = (
        TrademarkMatch.objects.filter(
            website=instance,
        )
        .filter(checked_at__gte=timezone.now() - timezone.timedelta(days=1))
        .exists()
    )

    if recent_check and not created:
        return  # Skip if updated but recently checked

    # Run trademark check
    org = None
    if hasattr(instance, "organization"):
        org = instance.organization

    _perform_trademark_check(
        name=instance.name,
        organization=org,
        website=instance,
    )


def _perform_trademark_check(name, organization=None):
    """
    Core function to perform trademark matching and store results.
    """
    try:
        matches = get_matches_for_website(name, threshold=85.0)

        if organization:
            TrademarkMatch.objects.filter(organization=organization).delete()

        for match in matches:
            if match.score >= 90.0:
                risk_level = "high"
            elif match.score >= 80.0:
                risk_level = "medium"
            else:
                risk_level = "low"

            TrademarkMatch.objects.create(
                organization=organization,
                checked_name=name,
                matched_trademark_name=match.name,
                similarity_score=match.score,
                risk_level=risk_level,
                notes=f"Auto-detected on {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            )
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Trademark check failed for {name}: {str(e)}")
