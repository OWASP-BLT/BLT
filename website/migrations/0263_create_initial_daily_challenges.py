# Generated migration to create initial DailyChallenge records

from django.db import migrations


def create_initial_daily_challenges(apps, schema_editor):
    """
    Create initial DailyChallenge records for all challenge types.
    This ensures the feature works out of the box after migration.
    """
    DailyChallenge = apps.get_model("website", "DailyChallenge")

    challenges_data = [
        {
            "challenge_type": "early_checkin",
            "title": "Early Bird",
            "description": "Submit your check-in before 10 AM in your local timezone to earn bonus points!",
            "points_reward": 15,
            "is_active": True,
        },
        {
            "challenge_type": "positive_mood",
            "title": "Positive Vibes",
            "description": "Start your day with a positive mood! Select Happy 😊 or Smile 😄 when submitting your check-in.",
            "points_reward": 10,
            "is_active": True,
        },
        {
            "challenge_type": "complete_all_fields",
            "title": "Complete Check-in",
            "description": "Fill out all fields in your daily check-in form completely to earn points.",
            "points_reward": 10,
            "is_active": True,
        },
        {
            "challenge_type": "streak_milestone",
            "title": "Streak Master",
            "description": "Reach a streak milestone (7, 15, 30, 100, 180, or 365 days) to earn bonus points!",
            "points_reward": 50,
            "is_active": True,
        },
        {
            "challenge_type": "no_blockers",
            "title": "Smooth Sailing",
            "description": "Have a blocker-free day! Select 'No blockers' when submitting your check-in.",
            "points_reward": 10,
            "is_active": True,
        },
        {
            "challenge_type": "detailed_reporter",
            "title": "Detailed Reporter",
            "description": "Write at least 200 words in your 'Previous Work' field to earn bonus points for detailed reporting!",
            "points_reward": 15,
            "is_active": True,
        },
        {
            "challenge_type": "goal_achiever",
            "title": "Goal Achiever",
            "description": "Accomplish your goals from yesterday! Select 'Yes' for goal accomplished to earn points.",
            "points_reward": 15,
            "is_active": True,
        },
        {
            "challenge_type": "detailed_planner",
            "title": "Detailed Planner",
            "description": "Plan ahead! Write at least 200 words in your 'Next Plan' field to earn bonus points for detailed planning!",
            "points_reward": 15,
            "is_active": True,
        },
    ]

    for challenge_data in challenges_data:
        DailyChallenge.objects.get_or_create(
            challenge_type=challenge_data["challenge_type"],
            defaults={
                "title": challenge_data["title"],
                "description": challenge_data["description"],
                "points_reward": challenge_data["points_reward"],
                "is_active": challenge_data["is_active"],
            },
        )


def reverse_create_challenges(apps, schema_editor):
    """Reverse migration - remove all DailyChallenge records"""
    DailyChallenge = apps.get_model("website", "DailyChallenge")
    DailyChallenge.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0262_add_new_daily_challenge_types"),
    ]

    operations = [
        migrations.RunPython(create_initial_daily_challenges, reverse_create_challenges),
    ]
