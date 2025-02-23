from django.core.management.base import BaseCommand

from website.models import Domain


class Command(BaseCommand):
    help = "Check security.txt for all domains"

    def handle(self, *args, **kwargs):
        domains = Domain.objects.all()
        for domain in domains:
            has_security = domain.check_security_txt()
            self.stdout.write(
                self.style.SUCCESS(f'Checked {domain.name}: {"Has" if has_security else "No"} security.txt')
            )
