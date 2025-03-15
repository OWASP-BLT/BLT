# website/apps.py
from django.apps import AppConfig


class WebsiteConfig(AppConfig):
    name = "website"

    def ready(self):
        import website.challenge_signals  # noqa
        import website.feed_signals  # noqa

