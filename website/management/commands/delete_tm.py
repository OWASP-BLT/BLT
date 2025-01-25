from django.core.management.base import BaseCommand

from website.models import Trademark, TrademarkOwner


class Command(BaseCommand):
    help = "Delete all entries from Trademarks and TrademarkOwner"

    def handle(self, *args, **kwargs):
        # Delete all TrademarkOwner entries
        TrademarkOwner.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Deleted all entries from TrademarkOwner"))

        # Delete all Trademark entries
        Trademark.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Deleted all entries from Trademark"))
