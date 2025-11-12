import logging

from django.core.management.base import BaseCommand


class SizzleBaseCommand(BaseCommand):
    """Base command class for Sizzle management commands"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(self.__class__.__module__)

    def log_info(self, message):
        """Log info message"""
        self.stdout.write(self.style.SUCCESS(message))
        self.logger.info(message)

    def log_error(self, message):
        """Log error message"""
        self.stdout.write(self.style.ERROR(message))
        self.logger.error(message)

    def log_warning(self, message):
        """Log warning message"""
        self.stdout.write(self.style.WARNING(message))
        self.logger.warning(message)
