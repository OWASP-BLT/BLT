# website/apps.py
from django.apps import AppConfig


class WebsiteConfig(AppConfig):
    name = "website"

    def ready(self):
        import website.signals  # noqa

        from . import scheduler_config

        scheduler_config.start()
