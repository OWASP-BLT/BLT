#!/usr/bin/env python
"""
Quick test script to verify BACON token system is working.
Run with: docker-compose exec app python test_bacon_system.py
"""

import os
import sys


def main():
    """Main function to run BACON system tests"""
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blt.settings")
    django.setup()

    from allauth.socialaccount.models import SocialAccount
    from django.contrib.auth.models import User

    from website.feed_signals import giveBacon
    from website.models import Activity, BaconEarning

    sys.stdout.write("=" * 60 + "\n")
    sys.stdout.write("BACON TOKEN SYSTEM TEST\n")
    sys.stdout.write("=" * 60 + "\n")

    # Test 1: Check if signal module is loaded
    sys.stdout.write("\n1. Checking signal module...\n")
    try:
        from website import social_signals

        sys.stdout.write("   [OK] Signal module loaded\n")
        sys.stdout.write(f"   [OK] Function exists: {hasattr(social_signals, 'reward_social_account_connection')}\n")
    except Exception as e:
        sys.stderr.write(f"   [ERROR] Error: {e}\n")

    # Test 2: Check giveBacon function
    sys.stdout.write("\n2. Testing giveBacon function...\n")
    try:
        # Get or create test user
        user, created = User.objects.get_or_create(username="bacon_test_user", defaults={"email": "test@bacon.com"})
        if created:
            # Set a secure random password for test user
            import secrets

            user.set_password(secrets.token_urlsafe(32))
            user.save()
            sys.stdout.write(f"   [OK] Created test user: {user.username}\n")
        else:
            sys.stdout.write(f"   [OK] Using existing user: {user.username}\n")

        # Get current BACON
        bacon, _ = BaconEarning.objects.get_or_create(user=user)
        before = bacon.tokens_earned
        sys.stdout.write(f"   [INFO] BACON before: {before}\n")

        # Award 5 BACON
        result = giveBacon(user, amt=5)
        sys.stdout.write(f"   [INFO] giveBacon returned: {result}\n")

        # Check after
        bacon.refresh_from_db()
        after = bacon.tokens_earned
        sys.stdout.write(f"   [INFO] BACON after: {after}\n")

        if after > before:
            sys.stdout.write(f"   [OK] giveBacon works! (+{after - before})\n")
        else:
            sys.stderr.write("   [ERROR] giveBacon didn't work!\n")

    except Exception as e:
        sys.stderr.write(f"   [ERROR] Error: {e}\n")
        import traceback

        traceback.print_exc()

    # Test 3: Check all users with GitHub
    sys.stdout.write("\n3. Checking users with GitHub connected...\n")
    try:
        github_accounts = SocialAccount.objects.filter(provider="github")
        sys.stdout.write(f"   [INFO] Found {github_accounts.count()} users with GitHub\n")

        for account in github_accounts:
            user = account.user
            bacon = BaconEarning.objects.filter(user=user).first()
            bacon_amount = bacon.tokens_earned if bacon else 0
            sys.stdout.write(f"   - {user.username}: {bacon_amount} BACON\n")

    except Exception as e:
        sys.stderr.write(f"   [ERROR] Error: {e}\n")

    # Test 4: Check activities
    sys.stdout.write("\n4. Checking connection activities...\n")
    try:
        activities = Activity.objects.filter(action_type="connected")
        sys.stdout.write(f"   [INFO] Found {activities.count()} connection activities\n")

        for activity in activities[:5]:
            sys.stdout.write(f"   - {activity.user.username}: {activity.title}\n")

    except Exception as e:
        sys.stderr.write(f"   [ERROR] Error: {e}\n")

    # Test 5: Check signal receivers
    sys.stdout.write("\n5. Checking signal receivers...\n")
    try:
        from allauth.socialaccount.signals import social_account_added

        receivers = social_account_added.receivers
        sys.stdout.write(f"   [INFO] Found {len(receivers)} receivers\n")
        for receiver in receivers:
            sys.stdout.write(f"   - {receiver}\n")
    except Exception as e:
        sys.stderr.write(f"   [ERROR] Error: {e}\n")

    sys.stdout.write("\n" + "=" * 60 + "\n")
    sys.stdout.write("TEST COMPLETE\n")
    sys.stdout.write("=" * 60 + "\n")
    sys.stdout.write("\nIf giveBacon works but users aren't getting tokens,\n")
    sys.stdout.write("the signal might not be firing during OAuth signup.\n")
    sys.stdout.write("\nWatch logs during signup: docker-compose logs -f app\n")
    sys.stdout.write("Look for: SIGNAL FIRED messages\n")
    sys.stdout.write("=" * 60 + "\n")


if __name__ == "__main__":
    main()
