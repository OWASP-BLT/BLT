from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection

class Command(BaseCommand):
    help = 'Creates the cache table if it does not exist'

    def handle(self, *args, **options):
        # Assuming the default cache table name; change if yours is different
        table_name = 'django_cache'
        table_exists = table_name in connection.introspection.table_names()

        if table_exists:
            self.stdout.write(self.style.SUCCESS(f"'{table_name}' table already exists."))
        else:
            # Create the cache table
            call_command('createcachetable')
            self.stdout.write(self.style.SUCCESS(f"'{table_name}' table created."))
