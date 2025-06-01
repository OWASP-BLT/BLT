import os
import shutil

from django.conf import settings
from django.core.files import File
from django.db import migrations

def link_streak_badge_icons(apps, schema_editor):
    Badge = apps.get_model("website", "Badge")
    badge_icon_map = {
        "Weekly Streak": "badges/7-day-streak.PNG",
        "15 Day Streak": "badges/15-day-streak.PNG",
        "Monthly Streak": "badges/30-day-streak.PNG",
        "100 Day Streak": "badges/100-day-streak.PNG",
        "Six Month Streak": "badges/180-day-streak.PNG",
        "Yearly Streak": "badges/365-day-streak.PNG",
    }
    for title, icon_relative_path in badge_icon_map.items():
        badge = Badge.objects.filter(title=title).first()
        if badge:
            static_icon_path = os.path.join("website", "static", "img", icon_relative_path)
            if os.path.exists(static_icon_path):
                media_icon_path = os.path.join(settings.MEDIA_ROOT, "badges", os.path.basename(static_icon_path))
                os.makedirs(os.path.dirname(media_icon_path), exist_ok=True)
                shutil.copy(static_icon_path, media_icon_path)
                with open(media_icon_path, "rb") as f:
                    badge.icon.save(os.path.basename(media_icon_path), File(f), save=True)
                    badge.save()

class Migration(migrations.Migration):
    dependencies = [
        ("website", "0241_domain_has_security_txt_and_more"),
    ]
    operations = [
        migrations.RunPython(link_streak_badge_icons),
    ] 