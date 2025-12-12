#!/usr/bin/env python
"""
Reset demo data for screen recording.
Clears check-ins, challenges, and points to show fresh state.
"""
import os
import sys

import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blt.settings')
django.setup()

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from website.models import DailyStatusReport, Points, UserDailyChallenge


def reset_demo_data(username=None):
    """Reset all demo data for a user."""
    
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
        # Get first active user or ask
        users = User.objects.filter(is_active=True)
        if not users.exists():
            print("❌ No active users found!")
            return
        user = users.first()
        print(f"Using user: {user.username}")
    
    print(f"\n🔄 Resetting demo data for user: {user.username}")
    print("=" * 50)
    
    # 1. Clear all check-ins
    checkins_count = DailyStatusReport.objects.filter(user=user).count()
    DailyStatusReport.objects.filter(user=user).delete()
    print(f"✅ Deleted {checkins_count} check-in(s)")
    
    # 2. Clear all user challenges
    challenges_count = UserDailyChallenge.objects.filter(user=user).count()
    UserDailyChallenge.objects.filter(user=user).delete()
    print(f"✅ Deleted {challenges_count} challenge assignment(s)")
    
    # 3. Clear challenge-related points (optional - comment out if you want to keep other points)
    challenge_points = Points.objects.filter(
        user=user,
        reason__icontains='daily challenge'
    )
    challenge_points_count = challenge_points.count()
    challenge_points.delete()
    print(f"✅ Deleted {challenge_points_count} challenge-related point(s)")
    
    # 4. Show remaining points
    remaining_points = Points.objects.filter(user=user).aggregate(
        total=models.Sum('score')
    )['total'] or 0
    print(f"📊 Remaining total points: {remaining_points}")
    
    print("\n" + "=" * 50)
    print("✅ Demo data reset complete!")
    print("\nNext steps:")
    print("1. Assign a new challenge via admin or management command")
    print("2. Submit a check-in to see timer start")
    print("3. Check-in history will be empty (fresh start)")
    print(f"\nTo assign a challenge, run:")
    print(f"  poetry run python manage.py generate_daily_challenges --date $(date +%Y-%m-%d)")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Reset demo data for screen recording')
    parser.add_argument('--username', '-u', type=str, help='Username to reset data for')
    args = parser.parse_args()
    
    reset_demo_data(args.username)

