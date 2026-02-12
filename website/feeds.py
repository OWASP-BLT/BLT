from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils.feedgenerator import Rss201rev2Feed

from website.models import Activity


class ActivityFeed(Feed):
    """RSS feed for global activity feed."""

    title = "OWASP BLT - Global Activity Feed"
    link = "/feed/"
    description = "Stay updated with the latest activities on the OWASP Bug Logging Tool"
    feed_type = Rss201rev2Feed

    def items(self):
        """Return the latest 50 activities."""
        return Activity.objects.all().order_by("-timestamp")[:50]

    def item_title(self, item):
        """Return the title of the activity."""
        return item.title

    def item_description(self, item):
        """Return the description of the activity."""
        description = f"{item.get_action_type_display()} by {item.user.username}"
        if item.description:
            description += f"\n\n{item.description}"
        return description

    def item_link(self, item):
        """Return the link to the activity."""
        if item.url:
            return item.url
        return reverse("feed")

    def item_pubdate(self, item):
        """Return the publication date of the activity."""
        return item.timestamp

    def item_author_name(self, item):
        """Return the author's name."""
        return item.user.username

    def item_guid(self, item):
        """Return a unique identifier for the item."""
        return f"activity-{item.id}"

    def item_guid_is_permalink(self, item):
        """Indicate that the GUID is not a permalink."""
        return False
