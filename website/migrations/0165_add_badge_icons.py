import os
import shutil

from django.conf import settings
from django.core.files import File
from django.db import migrations


def add_badge_icons(apps, schema_editor):
    Badge = apps.get_model("website", "Badge")
    new_badges = [
        {"title": "Mentor", "icon": "badges/icons8-mentor-94.png"},
        {"title": "First Pull Request Merged", "icon": "badges/icons8-merge-40.png"},
        {"title": "First Contribution", "icon": "badges/icons8-contribution-64.png"},
        {"title": "First Code Review", "icon": "badges/icons8-code-review-64.png"},
        {"title": "First Documentation Contribution", "icon": "badges/icons8-documentation-64.png"},
        {"title": "First Test Added", "icon": "badges/icons8-test-60.png"},
        {"title": "First Issue Closed", "icon": "badges/icons8-close-window-64.png"},
        {"title": "First Pull Request Reviewed", "icon": "badges/icons8-request-review-48.png"},
        {"title": "First Milestone Achieved", "icon": "badges/icons8-milestone-50.png"},
        {"title": "First CI Build Passed", "icon": "badges/ci-build-passed.png"},
        {"title": "First CI Build Failed", "icon": "badges/icons8-fail-32.png"},
        {"title": "First Security Issue Reported", "icon": "badges/icons8-security-shield-96.png"},
        {
            "title": "First Security Fix Merged",
            "icon": "badges/icons8-security-configuration-40.png",
        },
        {
            "title": "First Code Linter Passed",
            "icon": "badges/icons8-eslint-pluggable-and-configurable-linter-tool-for-identifying-and-reporting-on-patterns-in-javascript-96.png",
        },
        {"title": "First Code Linter Failed", "icon": "badges/linter-fail.png"},
        {"title": "First Dependency Updated", "icon": "badges/icons8-dependency-60.png"},
        {"title": "First Fork Created", "icon": "badges/icons8-branch-80.png"},
        {"title": "First Star Given", "icon": "badges/icons8-star-96.png"},
        {"title": "First Branch Created", "icon": "badges/icons8-branch-80.png"},
        {"title": "First Tag Created", "icon": "badges/icons8-tag-100.png"},
        {"title": "First Commit", "icon": "badges/icons8-commit-git-80.png"},
        {"title": "First Merge Conflict Resolved", "icon": "badges/conflict-resolve.png"},
        {"title": "First Code Refactor", "icon": "badges/icons8-refactoring-60.png"},
        {"title": "First Code Optimization", "icon": "badges/icons8-optimize-64.png"},
        {"title": "First Performance Improvement", "icon": "badges/icons8-performance-goal-96.png"},
        {"title": "First Bug Reported", "icon": "badges/icons8-bug-96.png"},
        {"title": "First Blog Posted", "icon": "badges/icons8-blog-96.png"},
        {"title": "First Discussion Started", "icon": "badges/icons8-discussion-100.png"},
        {"title": "First Project Board Created", "icon": "badges/icons8-dashboard-100.png"},
        {"title": "First Project Board Completed", "icon": "badges/icons8-complete-100.png"},
        {"title": "First Wiki Page Created", "icon": "badges/icons8-wiki-64.png"},
        {"title": "First Wiki Page Edited", "icon": "badges/icons8-edit-96.png"},
        {"title": "First API Documentation Added", "icon": "badges/icons8-api-64.png"},
        {"title": "First Markdown File Added", "icon": "badges/icons8-markdown-56.png"},
        {"title": "First Community Event Hosted", "icon": "badges/icons8-host-64.png"},
        {"title": "First Demo Recorded", "icon": "badges/icons8-demo-60.png"},
        {"title": "First Tutorial Published", "icon": "badges/icons8-tutorial-64.png"},
        {"title": "First Webinar Hosted", "icon": "badges/icons8-webinar-100.png"},
        {"title": "First Meetup Organized", "icon": "badges/icons8-run-into-men-100.png"},
        {"title": "First Conference Talk", "icon": "badges/icons8-conference-80.png"},
        {"title": "First Newsletter Sent", "icon": "badges/icons8-newsletter-96.png"},
        {"title": "First Social Media Post", "icon": "badges/icons8-social-50.png"},
        {"title": "First Community Survey", "icon": "badges/icons8-survey-96.png"},
        {"title": "First User Feedback", "icon": "badges/icons8-feedback-80.png"},
        {
            "title": "First IP Reported",
            "icon": "badges/icons8-ip-48.png",
        },
        {
            "title": "First Bid Placed",
            "icon": "badges/icons8-bid-64.png",
        },
        {
            "title": "First Bug Bounty",
            "icon": "badges/icons8-bug-bounty-64.png",
        },
        {
            "title": "First Suggestion",
            "icon": "badges/icons8-suggestion-64.png",
        },
    ]

    for badge_data in new_badges:
        badge = Badge.objects.filter(title=badge_data["title"]).first()

        if badge:
            # Construct the full file path for the static folder where images are added
            static_icon_path = os.path.join("website", "static", "img", badge_data["icon"])

            # Checking if the image exists in static folder
            if os.path.exists(static_icon_path):
                # Create the target directory in MEDIA_ROOT (media/badges/)
                media_icon_path = os.path.join(settings.MEDIA_ROOT, "badges", os.path.basename(static_icon_path))

                # Ensure the target directory exists
                os.makedirs(os.path.dirname(media_icon_path), exist_ok=True)

                # Need to copy this image in the media file so that it can be served by django
                shutil.copy(static_icon_path, media_icon_path)

                # Open the copied file and save it to the Badge model
                with open(media_icon_path, "rb") as f:
                    badge.icon.save(os.path.basename(media_icon_path), File(f), save=True)
                    badge.save()


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0164_integration_company_integrations_slackintegration"),
    ]
    operations = [
        migrations.RunPython(add_badge_icons),
    ]

