from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates all labs and seeds all tasks in the correct order."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("\n=== Starting full seeding process ===\n"))

        self.stdout.write(self.style.WARNING("→ Creating labs..."))
        call_command("create_initial_labs")
        self.stdout.write(self.style.SUCCESS("Labs created/updated."))

        self.stdout.write(self.style.WARNING("\n→ Seeding lab tasks..."))
        call_command("seed_all_labs")
        self.stdout.write(self.style.SUCCESS(" Tasks seeded for all labs."))

        self.stdout.write(self.style.SUCCESS("\n All labs & tasks seeded successfully!"))
