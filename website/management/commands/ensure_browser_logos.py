import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Ensures browser logos are copied to the static directory'

    def handle(self, *args, **options):
        try:
            subprocess.check_call(['npm', 'run', 'copy-logos'], cwd=settings.BASE_DIR)
            self.stdout.write(self.style.SUCCESS('Successfully copied browser logos'))
        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f'Failed to copy browser logos: {e}'))