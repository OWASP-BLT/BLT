#!/usr/bin/env python
"""
Assign a specific challenge type for demo purposes.
Excludes Early Bird since it's late evening.
"""
import os
import sys
from datetime import date

import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blt.settings')
django.setup()

from django.contrib.auth.models import User
from django.db import transaction

from website.models import DailyChallenge, UserDailyChallenge


def assign_demo_challenge(username=None, challenge_type=None):
    """Assign a specific challenge for demo."""
    
    if username:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            print(f"❌ User '{username}' not found!")
            print("Available users:")
            for u in User.objects.all():
                print(f"  - {u.username}")
            return
    else:
        users = User.objects.filter(is_active=True)
        if not users.exists():
            print("❌ No active users found!")
            return
        user = users.first()
        print(f"Using user: {user.username}")
    
    # Get available daily-completable challenges (excluding Early Bird for evening demo)
    demo_challenge_types = [
        "positive_mood",           # Select Happy/Smile
        "complete_all_fields",     # Fill all fields
        "no_blockers",             # Select "No blockers"
        "detailed_reporter",       # 200+ words in previous work
        "goal_achiever",           # Accomplish goals
        "detailed_planner",        # 200+ words in next plan
    ]
    
    if challenge_type:
        if challenge_type not in demo_challenge_types:
            print(f"❌ Invalid challenge type: {challenge_type}")
            print(f"Available types: {', '.join(demo_challenge_types)}")
            return
        target_type = challenge_type
    else:
        # Default to "positive_mood" - easiest to demo
        target_type = "positive_mood"
        print(f"Using default challenge: {target_type}")
    
    try:
        challenge = DailyChallenge.objects.get(challenge_type=target_type, is_active=True)
    except DailyChallenge.DoesNotExist:
        print(f"❌ Challenge type '{target_type}' not found or not active!")
        print("Available challenges:")
        for c in DailyChallenge.objects.filter(is_active=True):
            print(f"  - {c.challenge_type}: {c.title}")
        return
    
    today = date.today()
    
    try:
        with transaction.atomic():
            existing = UserDailyChallenge.objects.filter(
                user=user,
                challenge_date=today,
            ).first()
            
            if existing:
                existing.challenge = challenge
                existing.status = "assigned"
                existing.completed_at = None
                existing.points_awarded = 0
                existing.next_challenge_at = None
                existing.save()
                print(f"✅ Updated existing challenge to: {challenge.title}")
            else:
                UserDailyChallenge.objects.create(
                    user=user,
                    challenge=challenge,
                    challenge_date=today,
                    status="assigned",
                )
                print(f"✅ Assigned new challenge: {challenge.title}")
            
            print(f"\n📋 Challenge Details:")
            print(f"   Title: {challenge.title}")
            print(f"   Description: {challenge.description}")
            print(f"   Points: {challenge.points_reward}")
            print(f"   Type: {challenge.challenge_type}")
            
            if challenge.challenge_type == "positive_mood":
                print(f"\n💡 To complete: Select 'Happy' 😊 or 'Smile' 😄 mood")
            elif challenge.challenge_type == "no_blockers":
                print(f"\n💡 To complete: Select 'No blockers' from dropdown")
            elif challenge.challenge_type == "complete_all_fields":
                print(f"\n💡 To complete: Fill all required fields")
            elif challenge.challenge_type == "detailed_reporter":
                print(f"\n💡 To complete: Write 200+ words in 'Previous Work'")
            elif challenge.challenge_type == "goal_achiever":
                print(f"\n💡 To complete: Select 'Yes' for goal accomplished")
            elif challenge.challenge_type == "detailed_planner":
                print(f"\n💡 To complete: Write 200+ words in 'Next Plan'")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Assign a demo-friendly challenge')
    parser.add_argument('--username', '-u', type=str, help='Username')
    parser.add_argument('--type', '-t', type=str, 
                       choices=['positive_mood', 'complete_all_fields', 'no_blockers', 
                               'detailed_reporter', 'goal_achiever', 'detailed_planner'],
                       help='Challenge type to assign')
    args = parser.parse_args()
    
    assign_demo_challenge(args.username, args.type)




