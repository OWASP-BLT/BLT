# Generated manually to update bacon rewards for existing challenges

from django.db import migrations


def update_challenge_bacon_rewards(apps, schema_editor):
    Challenge = apps.get_model("website", "Challenge")

    # Update team challenges with higher bacon rewards
    team_challenge_rewards = {
        "Report 10 IPs": 10,
        "Report 10 Issues": 10,
        "All Members Sign in for 5 Days": 15,
    }

    # Update single user challenges with appropriate bacon rewards
    single_challenge_rewards = {
        "Report 5 IPs": 5,
        "Report 5 Issues": 5,
        "Sign in for 5 Days": 8,
    }

    # Update team challenges
    for title, bacon_amount in team_challenge_rewards.items():
        Challenge.objects.filter(title=title, challenge_type="team").update(bacon_reward=bacon_amount)

    # Update single challenges
    for title, bacon_amount in single_challenge_rewards.items():
        Challenge.objects.filter(title=title, challenge_type="single").update(bacon_reward=bacon_amount)


def reverse_update_challenge_bacon_rewards(apps, schema_editor):
    # Reset all bacon rewards to default value of 5
    Challenge = apps.get_model("website", "Challenge")
    Challenge.objects.all().update(bacon_reward=5)


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0178_add_bacon_reward_to_challenge"),
    ]

    operations = [
        migrations.RunPython(update_challenge_bacon_rewards, reverse_update_challenge_bacon_rewards),
    ]
