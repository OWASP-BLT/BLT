# website/apps.py
from django.apps import AppConfig


class WebsiteConfig(AppConfig):
    name = "website"

    def ready(self):
        import website.feed_signals 
        import website.challenge_signals # noqa
