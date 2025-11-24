import hashlib
import logging
import secrets
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from website.models import BaconEarning, EasterEgg, EasterEggDiscovery

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Get the client's IP address from the request"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def get_user_agent(request):
    """Get the user agent from the request"""
    return request.META.get("HTTP_USER_AGENT", "")[:255]


@login_required
@require_POST
def discover_easter_egg(request):
    """
    Handle Easter egg discovery by users.
    This endpoint requires authentication and uses CSRF protection.
    Rate limiting is applied to prevent abuse.
    """
    try:
        # Get the Easter egg code from request
        egg_code = request.POST.get("code")
        if not egg_code:
            return JsonResponse({"error": "No Easter egg code provided"}, status=400)

        # Rate limiting: Max 10 attempts per user per hour
        rate_limit_key = f"easter_egg_attempts:{request.user.id}"
        attempts = cache.get(rate_limit_key, 0)
        if attempts >= 10:
            return JsonResponse({"error": "Too many attempts. Please try again later."}, status=429)

        # Increment rate limit counter
        cache.set(rate_limit_key, attempts + 1, 3600)  # 1 hour timeout

        # Get the Easter egg
        try:
            easter_egg = EasterEgg.objects.get(code=egg_code, is_active=True)
        except EasterEgg.DoesNotExist:
            logger.warning(f"User {request.user.username} attempted to discover non-existent Easter egg: {egg_code}")
            return JsonResponse({"error": "Easter egg not found"}, status=404)

        # Check if user has already discovered this Easter egg
        existing_discovery = EasterEggDiscovery.objects.filter(user=request.user, easter_egg=easter_egg).first()

        if existing_discovery:
            if (
                easter_egg.max_claims_per_user > 0
                and EasterEggDiscovery.objects.filter(user=request.user, easter_egg=easter_egg).count()
                >= easter_egg.max_claims_per_user
            ):
                return JsonResponse(
                    {
                        "error": "You have already discovered this Easter egg",
                        "already_discovered": True,
                    },
                    status=400,
                )

        # Additional security check for bacon token Easter egg
        if easter_egg.reward_type == "bacon":
            # Verify the request has a valid verification token
            verification_token = request.POST.get("verification")
            if not verification_token:
                logger.warning(f"User {request.user.username} attempted bacon Easter egg without verification token")
                return JsonResponse({"error": "Invalid request"}, status=400)

            # Verify the token is valid
            expected_token = generate_verification_token(request.user.id, egg_code)
            if not secrets.compare_digest(verification_token, expected_token):
                logger.warning(f"User {request.user.username} provided invalid verification token for bacon Easter egg")
                return JsonResponse({"error": "Invalid verification"}, status=400)

            # Check daily bacon limit per user (max 1 bacon token Easter egg per day)
            today = timezone.now().date()
            bacon_discoveries_today = EasterEggDiscovery.objects.filter(
                user=request.user,
                easter_egg__reward_type="bacon",
                discovered_at__date=today,
            ).count()

            if bacon_discoveries_today >= 1:
                return JsonResponse(
                    {"error": "You have already earned bacon tokens today. Try again tomorrow!"},
                    status=400,
                )

        # Create the discovery record with atomic transaction
        with transaction.atomic():
            discovery = EasterEggDiscovery.objects.create(
                user=request.user,
                easter_egg=easter_egg,
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )

            # Award the reward based on type
            reward_message = ""
            if easter_egg.reward_type == "bacon" and easter_egg.reward_amount > 0:
                bacon_earning, created = BaconEarning.objects.get_or_create(user=request.user)
                bacon_earning.tokens_earned += Decimal(str(easter_egg.reward_amount))
                bacon_earning.save()
                reward_message = f"You earned {easter_egg.reward_amount} BACON tokens!"
                logger.info(
                    f"User {request.user.username} earned {easter_egg.reward_amount} BACON tokens from Easter egg"
                )

        return JsonResponse(
            {
                "success": True,
                "message": f"Congratulations! You discovered: {easter_egg.name}",
                "reward_type": easter_egg.reward_type,
                "reward_amount": easter_egg.reward_amount,
                "reward_message": reward_message,
                "description": easter_egg.description,
            }
        )

    except Exception as e:
        logger.error(f"Error discovering Easter egg: {str(e)}", exc_info=True)
        return JsonResponse({"error": "An error occurred. Please try again."}, status=500)


def generate_verification_token(user_id, egg_code):
    """
    Generate a secure verification token for bacon Easter egg.
    This uses a secret salt and HMAC to prevent token forgery.
    """
    # Use Django's SECRET_KEY as salt
    from django.conf import settings

    salt = settings.SECRET_KEY.encode()
    data = f"{user_id}:{egg_code}:{timezone.now().date()}".encode()
    return hashlib.pbkdf2_hmac("sha256", data, salt, 100000).hex()


@login_required
def get_verification_token(request):
    """
    Generate a verification token for the current user.
    This is called by the frontend before attempting to claim bacon Easter egg.
    """
    egg_code = request.GET.get("code")
    if not egg_code:
        return JsonResponse({"error": "No code provided"}, status=400)

    token = generate_verification_token(request.user.id, egg_code)
    return JsonResponse({"token": token})
