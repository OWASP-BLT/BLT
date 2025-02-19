import os
import shutil

from django.conf import settings
from django.core.files import File
from django.db import migrations

from website.models import Badge


def add_badge_icons(apps, schema_editor):
    new_badges = [
        {
            "title": "Weekly Streak",
            "icon": "7-day-streak.png",
            "description": "Awarded when a 7-day streak is achieved.",
        },
        {
            "title": "15 Day Streak",
            "icon": "15-day-streak.png",
            "description": "Awarded when a 15-day streak is achieved.",
        },
        {
            "title": "Monthly Streak",
            "icon": "30-day-streak.png",
            "description": "Awarded when a 30-day streak is achieved.",
        },
        {
            "title": "100 Day Streak",
            "icon": "100-day-streak.png",
            "description": "Awarded when a 100-day streak is achieved.",
        },
        {
            "title": "Six Month Streak",
            "icon": "180-day-streak.png",
            "description": "Awarded when a 180-day streak is achieved.",
        },
        {
            "title": "Yearly Streak",
            "icon": "365-day-streak.png",
            "description": "Awarded when a 365-day streak is achieved.",
        },
    ]

    for badge_data in new_badges:
        badge, created = Badge.objects.get_or_create(
            title=badge_data["title"],
            defaults={
                "description": badge_data["description"],
                "type": "automatic",
            },
        )

        static_icon_path = os.path.join("website", "static", "img", "badges", badge_data["icon"])

        # Checking if the image exists in the static folder
        if os.path.exists(static_icon_path):
            print(f"Found image for {badge_data['title']} at {static_icon_path}")

            # Create the target directory in MEDIA_ROOT (media/badges/)
            media_icon_path = os.path.join(settings.MEDIA_ROOT, "badges", os.path.basename(static_icon_path))

            # Ensure the target directory exists
            os.makedirs(os.path.dirname(media_icon_path), exist_ok=True)

            # Copy the image to the media directory
            shutil.copy(static_icon_path, media_icon_path)

            # Open the copied file and save it to the Badge model
            with open(media_icon_path, "rb") as f:
                badge.icon.save(os.path.basename(media_icon_path), File(f), save=True)
                badge.save()


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0167_points_reason_userprofile_current_streak_and_more"),
    ]
    operations = [
        migrations.RunPython(add_badge_icons),
    ]
