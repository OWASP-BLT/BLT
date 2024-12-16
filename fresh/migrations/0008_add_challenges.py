from django.db import migrations


def create_challenges(apps, schema_editor):
    Challenge = apps.get_model("fresh", "Challenge")
    
    # Single User Challenges
    single_user_challenges = [
        {
            "title": "Report 5 IPs",
            "description": "Report 5 different suspicious IPs to complete this challenge.",
            "challenge_type": "single",
            "fresh_points": 10,
        },
        {
            "title": "Report 5 Issues",
            "description": "Report 5 unique issues to complete this challenge.",
            "challenge_type": "single",
            "fresh_points": 15,
        },
        {
            "title": "Sign in for 5 Days",
            "description": "Sign in for 5 consecutive days to complete this challenge.",
            "challenge_type": "single",
            "fresh_points": 5,
        },
    ]

    # Team Challenges
    team_challenges = [
        {
            "title": "Report 10 IPs",
            "description": "Report 10 different suspicious IPs as a team to complete this challenge.",
            "challenge_type": "team",
            "fresh_points": 20,
        },
        {
            "title": "Report 10 Issues",
            "description": "Report 10 unique issues as a team to complete this challenge.",
            "challenge_type": "team",
            "fresh_points": 25,
        },
        {
            "title": "All Members Sign in for 5 Days",
            "description": "Ensure all team members sign in for 5 consecutive days to complete this challenge.",
            "challenge_type": "team",
            "fresh_points": 10,
        },
    ]

    # Create challenges in the database
    for challenge_data in single_user_challenges + team_challenges:
        Challenge.objects.create(**challenge_data)

class Migration(migrations.Migration):

    dependencies = [
        ("fresh", "0007_challenge_fresh_points"),
    ]

    operations = [
        migrations.RunPython(create_challenges),
    ]
