from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates all labs and seeds all tasks in the correct order."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("\n=== Starting full seeding process ===\n"))

        # Step 1: Create labs (page 1)
        self.stdout.write(self.style.WARNING("→ Creating labs..."))
        call_command("create_initial_labs")
        self.stdout.write(self.style.SUCCESS("✔ Labs created/updated."))

        # Step 2: Seed tasks (page 2)
        self.stdout.write(self.style.WARNING("\n→ Seeding lab tasks..."))
        call_command("seed_all_labs")
        self.stdout.write(self.style.SUCCESS("✔ Tasks seeded for all labs."))

        # Final output
        self.stdout.write(self.style.SUCCESS("\n🎉 All labs + tasks seeded successfully!"))
