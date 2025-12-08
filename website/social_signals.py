"""
Signal handlers for social account connections.
Handles rewards and tracking when users connect their social accounts.

Security Features:
- Rate limiting: Prevents duplicate rewards for same provider (24h cooldown)
- Audit logging: All actions logged for security review
- Input validation: Validates user and provider before processing
- Error handling: Graceful failure without exposing internals
- Transaction safety: Atomic operations for reward + audit trail
"""

import logging

from allauth.socialaccount.signals import social_account_added
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from website.feed_signals import giveBacon
from website.models import Activity, SocialAccountReward

logger = logging.getLogger(__name__)

# BACON token rewards for social account connections
SOCIAL_CONNECTION_REWARDS = {
    "github": 10,
    "google": 0,  # Not rewarding Google connections yet
    "facebook": 0,  # Not rewarding Facebook connections yet
}

# Brand-accurate display names for providers
SOCIAL_PROVIDER_DISPLAY_NAMES = {
    "github": "GitHub",
    "google": "Google",
    "facebook": "Facebook",
}

# Rate limiting: Prevent duplicate rewards within this time window (seconds)
REWARD_COOLDOWN = 86400  # 24 hours cooldown to prevent disconnect/reconnect abuse


def award_bacon_for_social(user, provider, is_signup):
    """
    Award BACON tokens for social account connection.

    This helper function encapsulates the complete reward flow:
    - Validates user and provider
    - Enforces rate limiting
    - Awards tokens and creates activity in atomic transaction
    - Sets success message cache
    - Handles errors with proper cleanup

    Args:
        user: The User instance
        provider: Social provider name (e.g., 'github', 'google')
        is_signup: Boolean indicating if this is a new signup (True) or existing user connection (False)

    Returns:
        bool: True if reward was successfully granted, False otherwise
    """
    # Security: Validate user exists and has ID
    if not user or not user.id:
        logger.warning("Invalid user for %s connection: user=%s", provider, user)
        return False

    # Security: Validate provider is in allowed list
    reward_amount = SOCIAL_CONNECTION_REWARDS.get(provider, 0)
    if reward_amount <= 0:
        logger.info("No reward configured for provider: %s", provider)
        return False

    # Security: Database-backed one-time reward check (permanent, survives cache clears)
    # This is checked inside the transaction to ensure atomicity
    cache_key = f"bacon_reward_{user.id}_{provider}"

    # Fast path: Check cache first to avoid database hit for recent attempts
    if not cache.add(cache_key, True, REWARD_COOLDOWN):
        logger.warning(
            "Rate limit: User %s already received reward for %s within cooldown period",
            user.username,
            provider,
        )
        return False

    logger.info("Attempting to award %s BACON to user: %s", reward_amount, user.username)

    # Get brand-accurate display name
    display_name = SOCIAL_PROVIDER_DISPLAY_NAMES.get(provider, provider.capitalize())

    # Award BACON tokens and create activity in atomic transaction
    try:
        with transaction.atomic():
            try:
                # Database guard: Create reward record (unique constraint prevents duplicates)
                try:
                    SocialAccountReward.objects.create(user=user, provider=provider)
                except IntegrityError:
                    logger.warning(
                        "User %s already rewarded for %s (database guard)",
                        user.username,
                        provider,
                    )
                    # Don't delete cache key - this is a permanent block
                    return False
                except Exception as e:  # noqa: BLE001
                    # Catch any other database errors to prevent breaking outer transactions
                    logger.error(
                        "Database error creating reward record for %s/%s: %s",
                        user.username,
                        provider,
                        e,
                        exc_info=True,
                    )
                    cache.delete(cache_key)
                    return False

                awarded = giveBacon(user, amt=reward_amount)
                logger.info("Successfully awarded %s BACON tokens to user: %s", awarded, user.username)

                # Create activity for audit trail within same transaction
                Activity.objects.create(
                    user=user,
                    action_type="connected",
                    title=f"Connected {display_name} Account",
                    description=f"Earned {awarded} BACON tokens for connecting {display_name} account",
                    content_type=ContentType.objects.get_for_model(user),
                    object_id=user.id,
                )
                logger.info("Created activity log for user %s - %s connection", user.username, provider)

            except Exception as e:  # noqa: BLE001
                # Catch exceptions inside atomic block to prevent breaking outer transactions
                logger.error(
                    "Failed to award BACON tokens to user %s: %s",
                    user.username,
                    e,
                    exc_info=True,
                )
                # Delete cache key on failure to allow retry
                cache.delete(cache_key)
                return False

        # Set cache flag for middleware to show success message (only after successful transaction)
        message_cache_key = f"show_bacon_message_{user.id}"
        cache.set(message_cache_key, {"provider": provider, "is_signup": is_signup}, 300)

        return True

    except Exception as e:  # noqa: BLE001
        # Outer catch for transaction.atomic() failures
        cache.delete(cache_key)
        logger.error(
            "Transaction error awarding BACON to user %s: %s",
            user.username,
            e,
            exc_info=True,
        )
        return False


@receiver(social_account_added)
def reward_social_account_connection(_request, sociallogin, **_kwargs):
    """
    Award BACON tokens when a social account is connected.

    This signal fires for both new user signups and existing users connecting accounts.
    The sociallogin.is_existing attribute distinguishes between the two cases.
    Note: The post_save handler on SocialAccount may also fire for the same event,
    but rate limiting prevents duplicate rewards.

    Security measures:
    - Validates user exists and has ID
    - Checks provider is in allowed list
    - Rate limiting prevents duplicate rewards
    - Logs all actions for audit trail
    - Handles errors gracefully without exposing internals
    """
    try:  # noqa: BLE001
        provider = sociallogin.account.provider
        user = sociallogin.user

        logger.info(
            "Social account connection: user=%s, provider=%s, is_existing=%s",
            user.username if user else "None",
            provider,
            sociallogin.is_existing,
        )

        # Delegate to shared reward logic
        award_bacon_for_social(user, provider, is_signup=not sociallogin.is_existing)

    except Exception as e:  # noqa: BLE001
        logger.error("Unexpected error in reward_social_account_connection: %s", e, exc_info=True)


@receiver(post_save, sender="socialaccount.SocialAccount")
def social_account_post_save(sender, instance, created, **_kwargs):  # noqa: ARG001
    """
    Award BACON tokens when a new social account record is created.

    This signal fires whenever a SocialAccount is created, which includes both
    new user signups and existing users connecting accounts. The rate limiting
    and database guard prevent duplicate rewards if both this signal and
    social_account_added fire for the same connection.

    Security measures:
    - Database guard prevents duplicate rewards permanently
    - Cache-based rate limiting for fast duplicate detection
    - Input validation ensures user and provider are valid
    - Audit trail via Activity model
    """
    if not created:
        return

    try:  # noqa: BLE001
        provider = instance.provider
        user = instance.user

        logger.info("New social account created: user=%s, provider=%s", user.username if user else "None", provider)

        # Delegate to shared reward logic
        award_bacon_for_social(user, provider, is_signup=True)

    except Exception as e:  # noqa: BLE001
        logger.error("Error in social_account_post_save: %s", e, exc_info=True)
