"""
Signal handlers for social account connections.
Handles rewards and tracking when users connect their social accounts.

Security Features:
- Rate limiting: Prevents duplicate rewards for same provider
- Audit logging: All actions logged for security review
- Input validation: Validates user and provider before processing
- Error handling: Graceful failure without exposing internals
"""

import logging

from allauth.socialaccount.signals import social_account_added
from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver

from website.feed_signals import giveBacon
from website.models import Activity

logger = logging.getLogger(__name__)

# BACON token rewards for social account connections
SOCIAL_CONNECTION_REWARDS = {
    "github": 10,
    "google": 0,  # Not rewarding Google connections yet
    "facebook": 0,  # Not rewarding Facebook connections yet
}

# Rate limiting: Prevent duplicate rewards within this time window (seconds)
REWARD_COOLDOWN = 60  # 1 minute cooldown between rewards for same user/provider


@receiver(social_account_added)
def reward_social_account_connection(request, sociallogin, **kwargs):
    """
    Award BACON tokens when an existing user connects a social account.

    This signal only fires for existing users connecting accounts, not new signups.
    New signups are handled by the post_save signal on SocialAccount.

    Security measures:
    - Validates user exists and has ID
    - Checks provider is in allowed list
    - Rate limiting prevents duplicate rewards
    - Logs all actions for audit trail
    - Handles errors gracefully without exposing internals
    """
    try:
        provider = sociallogin.account.provider
        user = sociallogin.user

        logger.info(
            f"Social account connection: user={user.username if user else 'None'}, "
            f"provider={provider}, is_existing={sociallogin.is_existing}"
        )

        # Set cache flag for middleware to show success message
        message_cache_key = f"show_bacon_message_{user.id}"
        cache.set(message_cache_key, {"provider": provider, "is_signup": not sociallogin.is_existing}, 60)

        # Security: Validate provider is in allowed list
        reward_amount = SOCIAL_CONNECTION_REWARDS.get(provider, 0)
        if reward_amount <= 0:
            logger.info(f"No reward configured for provider: {provider}")
            return

        # Security: Validate user exists
        if not user:
            logger.warning(f"No user found in sociallogin for provider: {provider}")
            return

        # Security: Validate user has been saved to database
        if not user.id:
            logger.warning(f"User {user.username} has no ID yet, skipping reward")
            return

        # Security: Rate limiting - prevent duplicate rewards
        cache_key = f"bacon_reward_{user.id}_{provider}"
        if cache.get(cache_key):
            logger.warning(
                f"Rate limit: User {user.username} already received reward for {provider} " f"within cooldown period"
            )
            return

        # Set rate limit cache
        cache.set(cache_key, True, REWARD_COOLDOWN)

        logger.info(f"Attempting to award {reward_amount} BACON to user: {user.username}")

        # Award BACON tokens
        try:
            awarded = giveBacon(user, amt=reward_amount)
            logger.info(f"Successfully awarded {awarded} BACON tokens to user: {user.username}")
        except Exception as e:
            logger.error(f"Failed to award BACON tokens to user {user.username}: {str(e)}", exc_info=True)
            return

        # Create activity for audit trail (non-critical)
        try:
            from django.contrib.contenttypes.models import ContentType

            Activity.objects.create(
                user=user,
                action_type="connected",
                title=f"Connected {provider.capitalize()} Account",
                description=f"Earned {reward_amount} BACON tokens for connecting {provider.capitalize()} account",
                content_type=ContentType.objects.get_for_model(user),
                object_id=user.id,
            )
            logger.info(f"Created activity log for user {user.username} - {provider} connection")
        except Exception as e:
            logger.warning(f"Failed to create activity log (non-critical): {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error in reward_social_account_connection: {str(e)}", exc_info=True)


@receiver(post_save, sender="socialaccount.SocialAccount")
def social_account_post_save(sender, instance, created, **kwargs):
    """
    Award BACON tokens when a new social account is created (new user signup).

    This signal fires for new user signups via OAuth. The social_account_added
    signal handles existing users connecting accounts.

    Security measures:
    - Rate limiting prevents duplicate rewards
    - Input validation ensures user and provider are valid
    - Audit trail via Activity model
    """
    if not created:
        return

    try:
        provider = instance.provider
        user = instance.user

        # Validate user
        if not user or not user.id:
            logger.warning(f"Social account created but user not ready: provider={provider}")
            return

        logger.info(f"New social account created: user={user.username}, provider={provider}")

        # Check if reward is configured for this provider
        reward_amount = SOCIAL_CONNECTION_REWARDS.get(provider, 0)
        if reward_amount <= 0:
            return

        # Rate limiting: prevent duplicate rewards
        cache_key = f"bacon_reward_{user.id}_{provider}"
        if cache.get(cache_key):
            logger.info(f"Rate limit: Skipping duplicate reward for {user.username}/{provider}")
            return
        cache.set(cache_key, True, REWARD_COOLDOWN)

        # Award BACON tokens
        try:
            awarded = giveBacon(user, amt=reward_amount)
            logger.info(f"Awarded {awarded} BACON to {user.username} for {provider} signup")
        except Exception as e:
            logger.error(f"Failed to award BACON to {user.username}: {e}", exc_info=True)
            return

        # Set cache flag for middleware to show success message
        message_cache_key = f"show_bacon_message_{user.id}"
        cache.set(message_cache_key, {"provider": provider, "is_signup": True}, 60)

        # Create activity for audit trail
        try:
            from django.contrib.contenttypes.models import ContentType

            Activity.objects.create(
                user=user,
                action_type="connected",
                title=f"Connected {provider.capitalize()} Account",
                description=f"Earned {reward_amount} BACON tokens for connecting {provider.capitalize()} account",
                content_type=ContentType.objects.get_for_model(user),
                object_id=user.id,
            )
        except Exception as e:
            logger.warning(f"Failed to create activity for {user.username}: {e}")

    except Exception as e:
        logger.error(f"Error in social_account_post_save: {e}", exc_info=True)
