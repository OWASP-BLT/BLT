import csv
import logging
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from website.models import Trademark, TrademarkOwner

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """
    Bulk import trademarks from a CSV file.
    
    CSV file should have the following columns:
    keyword, registration_number, serial_number, status_label, status_code,
    status_date, status_definition, filing_date, registration_date,
    abandonment_date, expiration_date, description
    
    Example usage:
    python manage.py bulk_import_trademarks /path/to/trademarks.csv --batch-size 10000
    """

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the CSV file containing trademark data")
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10000,
            help="Number of records to import in each batch (default: 10000)",
        )
        parser.add_argument(
            "--skip-header",
            action="store_true",
            help="Skip the first row of the CSV file",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        batch_size = options["batch_size"]
        skip_header = options["skip_header"]

        self.stdout.write(self.style.NOTICE(f"Starting bulk import from {csv_file}"))

        try:
            with open(csv_file, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                if skip_header:
                    next(reader)

                batch = []
                total_imported = 0
                total_skipped = 0

                for row in reader:
                    try:
                        # Parse dates
                        status_date = self._parse_date(row.get("status_date"))
                        filing_date = self._parse_date(row.get("filing_date"))
                        registration_date = self._parse_date(row.get("registration_date"))
                        abandonment_date = self._parse_date(row.get("abandonment_date"))
                        expiration_date = self._parse_date(row.get("expiration_date"))

                        trademark = Trademark(
                            keyword=row.get("keyword", "").strip(),
                            registration_number=row.get("registration_number", "").strip() or None,
                            serial_number=row.get("serial_number", "").strip() or None,
                            status_label=row.get("status_label", "").strip() or None,
                            status_code=row.get("status_code", "").strip() or None,
                            status_date=status_date,
                            status_definition=row.get("status_definition", "").strip() or None,
                            filing_date=filing_date,
                            registration_date=registration_date,
                            abandonment_date=abandonment_date,
                            expiration_date=expiration_date,
                            description=row.get("description", "").strip() or None,
                        )

                        batch.append(trademark)

                        if len(batch) >= batch_size:
                            imported = self._bulk_insert_batch(batch)
                            total_imported += imported
                            self.stdout.write(
                                self.style.SUCCESS(f"Imported {total_imported} trademarks so far...")
                            )
                            batch = []

                    except Exception as e:
                        total_skipped += 1
                        logger.warning(f"Error processing row: {str(e)}")
                        continue

                # Insert remaining records
                if batch:
                    imported = self._bulk_insert_batch(batch)
                    total_imported += imported

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Bulk import completed. Imported: {total_imported}, Skipped: {total_skipped}"
                    )
                )

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"File not found: {csv_file}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error during import: {str(e)}"))
            logger.error(f"Error during bulk import: {str(e)}", exc_info=True)

    def _parse_date(self, date_string):
        """Parse date string into a date object."""
        if not date_string or not date_string.strip():
            return None

        date_string = date_string.strip()

        # Try different date formats
        formats = ["%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"]

        for fmt in formats:
            try:
                return datetime.strptime(date_string, fmt).date()
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_string}")
        return None

    def _bulk_insert_batch(self, batch):
        """Insert a batch of trademarks using bulk_create."""
        try:
            with transaction.atomic():
                Trademark.objects.bulk_create(batch, ignore_conflicts=True)
                return len(batch)
        except Exception as e:
            logger.error(f"Error inserting batch: {str(e)}", exc_info=True)
            return 0
