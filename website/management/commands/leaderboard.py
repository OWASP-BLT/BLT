from django.db.models import Count

from website.management.base import LoggedBaseCommand
from website.models import UserProfile

# Title thresholds: (max_issues, title_level)
TITLE_THRESHOLDS = [
    (10, 1),
    (50, 2),
    (200, 3),
]
DEFAULT_TITLE = 4


def get_title_for_count(issue_count):
    """Return the title level for a given issue count."""
    for max_issues, title_level in TITLE_THRESHOLDS:
        if issue_count <= max_issues:
            return title_level
    return DEFAULT_TITLE


class Command(LoggedBaseCommand):
    help = "Update user titles based on number of bugs reported"

    def handle(self, *args, **options):
        # Single annotated query replaces per-profile N+1 issue count lookups
        profiles = list(UserProfile.objects.annotate(issue_count=Count("user__issue")).select_related("user"))

        changed = []
        for profile in profiles:
            new_title = get_title_for_count(profile.issue_count)
            if profile.title != new_title:
                profile.title = new_title
                changed.append(profile)

        # Bulk update only the profiles that changed
        if changed:
            UserProfile.objects.bulk_update(changed, ["title"])

        self.stdout.write(self.style.SUCCESS(f"Updated {len(changed)} of {len(profiles)} user titles."))
