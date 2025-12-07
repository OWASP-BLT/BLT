#!/usr/bin/env python
"""
Quick test script to verify BACON token system is working.
Run with: docker-compose exec app python test_bacon_system.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blt.settings')
django.setup()

from django.contrib.auth.models import User
from website.models import BaconEarning, Activity
from allauth.socialaccount.models import SocialAccount
from website.feed_signals import giveBacon

print("=" * 60)
print("BACON TOKEN SYSTEM TEST")
print("=" * 60)

# Test 1: Check if signal module is loaded
print("\n1. Checking signal module...")
try:
    from website import social_signals
    print("   [OK] Signal module loaded")
    print(f"   [OK] Function exists: {hasattr(social_signals, 'reward_social_account_connection')}")
except Exception as e:
    print(f"   [ERROR] Error: {e}")

# Test 2: Check giveBacon function
print("\n2. Testing giveBacon function...")
try:
    # Get or create test user
    user, created = User.objects.get_or_create(
        username='bacon_test_user',
        defaults={'email': 'test@bacon.com'}
    )
    if created:
        # Set a secure random password for test user
        import secrets
        user.set_password(secrets.token_urlsafe(32))
        user.save()
        print(f"   [OK] Created test user: {user.username}")
    else:
        print(f"   [OK] Using existing user: {user.username}")
    
    # Get current BACON
    bacon, _ = BaconEarning.objects.get_or_create(user=user)
    before = bacon.tokens_earned
    print(f"   [INFO] BACON before: {before}")
    
    # Award 5 BACON
    result = giveBacon(user, amt=5)
    print(f"   [INFO] giveBacon returned: {result}")
    
    # Check after
    bacon.refresh_from_db()
    after = bacon.tokens_earned
    print(f"   [INFO] BACON after: {after}")
    
    if after > before:
        print(f"   [OK] giveBacon works! (+{after - before})")
    else:
        print(f"   [ERROR] giveBacon didn't work!")
        
except Exception as e:
    print(f"   [ERROR] Error: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Check all users with GitHub
print("\n3. Checking users with GitHub connected...")
try:
    github_accounts = SocialAccount.objects.filter(provider='github')
    print(f"   [INFO] Found {github_accounts.count()} users with GitHub")
    
    for account in github_accounts:
        user = account.user
        bacon = BaconEarning.objects.filter(user=user).first()
        bacon_amount = bacon.tokens_earned if bacon else 0
        print(f"   - {user.username}: {bacon_amount} BACON")
        
except Exception as e:
    print(f"   [ERROR] Error: {e}")

# Test 4: Check activities
print("\n4. Checking connection activities...")
try:
    activities = Activity.objects.filter(action_type='connected')
    print(f"   [INFO] Found {activities.count()} connection activities")
    
    for activity in activities[:5]:
        print(f"   - {activity.user.username}: {activity.title}")
        
except Exception as e:
    print(f"   [ERROR] Error: {e}")

# Test 5: Check signal receivers
print("\n5. Checking signal receivers...")
try:
    from allauth.socialaccount.signals import social_account_added
    receivers = social_account_added.receivers
    print(f"   [INFO] Found {len(receivers)} receivers")
    for receiver in receivers:
        print(f"   - {receiver}")
except Exception as e:
    print(f"   [ERROR] Error: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
print("\nIf giveBacon works but users aren't getting tokens,")
print("the signal might not be firing during OAuth signup.")
print("\nWatch logs during signup: docker-compose logs -f app")
print("Look for: SIGNAL FIRED messages")
print("=" * 60)
