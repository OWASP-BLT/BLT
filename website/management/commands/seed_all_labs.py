from django.core.management.base import BaseCommand

from .create_broken_auth_tasks import Command as BrokenAuth
from .create_commands_injection_tasks import Command as CI
from .create_csrf_tasks import Command as CSRF
from .create_data_exposure_tasks import Command as DataExposure
from .create_file_upload_tasks import Command as FileUpload
from .create_idor_tasks import Command as IDOR
from .create_open_redirect_tasks import Command as OpenRedirect
from .create_sql_injection_tasks import Command as SQL
from .create_ssrf_tasks import Command as SSRF
from .create_xss_tasks import Command as XSS

ALL_LABS = [BrokenAuth, DataExposure, FileUpload, IDOR, OpenRedirect, SSRF, XSS, CSRF, SQL, CI]


class Command(BaseCommand):
    help = "Seeds ALL labs at once (theory + simulation)."

    def handle(self, *_args, **_kwargs):
        for Seeder in ALL_LABS:
            self.stdout.write(self.style.WARNING(f"Seeding: {Seeder.lab_name}"))
            seeder = Seeder()
            seeder.stdout = self.stdout
            seeder.stderr = self.stderr
            seeder.handle()

        self.stdout.write(self.style.SUCCESS("All labs seeded successfully"))
