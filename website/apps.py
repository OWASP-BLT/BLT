# website/apps.py
from django.apps import AppConfig


class WebsiteConfig(AppConfig):
    name = "website"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        import website.challenge_signals  # noqa
        import website.feed_signals  # noqa
        import website.signals  # noqa
        import website.social_signals  # noqa
