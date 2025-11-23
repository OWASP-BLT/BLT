"""
Management command to bulk import trademark data from CSV file.

This command is designed to import large datasets (e.g., 3 million records) efficiently
using Django's bulk_create with batching to avoid memory issues.

Expected CSV format:
keyword,registration_number,serial_number,status_label,status_code,status_date,
status_definition,filing_date,registration_date,abandonment_date,expiration_date,
description,owner_name,owner_address1,owner_address2,owner_city,owner_state,
owner_country,owner_postcode,owner_type,owner_label,legal_entity_type,
legal_entity_type_label

Usage:
    python manage.py import_trademarks_bulk <csv_file_path>
    python manage.py import_trademarks_bulk --json <json_file_path>
"""

import csv
import json
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from website.models import Trademark, TrademarkOwner


class Command(BaseCommand):
    help = "Bulk import trademark data from CSV or JSON file"

    def add_arguments(self, parser):
        parser.add_argument(
            "file_path",
            type=str,
            help="Path to the CSV or JSON file containing trademark data",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Import from JSON file instead of CSV",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Number of records to process in each batch (default: 1000)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing trademark data before import",
        )

    def parse_date(self, date_str):
        """Parse date string to date object, return None if invalid."""
        if not date_str or date_str.strip() == "":
            return None
        try:
            # Try multiple date formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"]:
                try:
                    return datetime.strptime(date_str.strip(), fmt).date()
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    def import_from_csv(self, file_path, batch_size):
        """Import trademark data from CSV file."""
        self.stdout.write(f"Starting CSV import from {file_path}")

        trademarks_batch = []
        owners_cache = {}
        total_imported = 0
        total_skipped = 0

        with open(file_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Get or create owner if owner data exists
                    owner = None
                    owner_name = row.get("owner_name", "").strip()
                    if owner_name:
                        # Use cache to avoid duplicate owner creation
                        cache_key = (
                            owner_name,
                            row.get("owner_address1", ""),
                            row.get("owner_city", ""),
                        )
                        if cache_key not in owners_cache:
                            owner, _ = TrademarkOwner.objects.get_or_create(
                                name=owner_name,
                                address1=row.get("owner_address1", ""),
                                address2=row.get("owner_address2", ""),
                                city=row.get("owner_city", ""),
                                state=row.get("owner_state", ""),
                                country=row.get("owner_country", ""),
                                postcode=row.get("owner_postcode", ""),
                                owner_type=row.get("owner_type", ""),
                                owner_label=row.get("owner_label", ""),
                                legal_entity_type=row.get("legal_entity_type", ""),
                                legal_entity_type_label=row.get("legal_entity_type_label", ""),
                            )
                            owners_cache[cache_key] = owner
                        else:
                            owner = owners_cache[cache_key]

                    # Create trademark object
                    trademark = Trademark(
                        keyword=row.get("keyword", "").strip() or f"Unknown-{row_num}",
                        registration_number=row.get("registration_number", "").strip() or None,
                        serial_number=row.get("serial_number", "").strip() or None,
                        status_label=row.get("status_label", "").strip() or None,
                        status_code=row.get("status_code", "").strip() or None,
                        status_date=self.parse_date(row.get("status_date", "")),
                        status_definition=row.get("status_definition", "").strip() or None,
                        filing_date=self.parse_date(row.get("filing_date", "")),
                        registration_date=self.parse_date(row.get("registration_date", "")),
                        abandonment_date=self.parse_date(row.get("abandonment_date", "")),
                        expiration_date=self.parse_date(row.get("expiration_date", "")),
                        description=row.get("description", "").strip() or None,
                    )

                    trademarks_batch.append((trademark, owner))

                    # Batch insert
                    if len(trademarks_batch) >= batch_size:
                        self._bulk_insert(trademarks_batch)
                        total_imported += len(trademarks_batch)
                        trademarks_batch = []
                        self.stdout.write(self.style.SUCCESS(f"Imported {total_imported} trademarks..."))

                except Exception as e:
                    total_skipped += 1
                    self.stderr.write(f"Error on row {row_num}: {str(e)}")

            # Insert remaining records
            if trademarks_batch:
                self._bulk_insert(trademarks_batch)
                total_imported += len(trademarks_batch)

        self.stdout.write(
            self.style.SUCCESS(f"\nImport complete! Total imported: {total_imported}, Skipped: {total_skipped}")
        )

    def import_from_json(self, file_path, batch_size):
        """Import trademark data from JSON file."""
        self.stdout.write(f"Starting JSON import from {file_path}")

        with open(file_path, "r", encoding="utf-8") as jsonfile:
            data = json.load(jsonfile)

        trademarks_batch = []
        owners_cache = {}
        total_imported = 0
        total_skipped = 0

        for idx, item in enumerate(data):
            try:
                # Get or create owner if owner data exists
                owner = None
                owner_data = item.get("owner")
                if owner_data and owner_data.get("name"):
                    cache_key = (
                        owner_data["name"],
                        owner_data.get("address1", ""),
                        owner_data.get("city", ""),
                    )
                    if cache_key not in owners_cache:
                        owner, _ = TrademarkOwner.objects.get_or_create(
                            name=owner_data["name"],
                            address1=owner_data.get("address1", ""),
                            address2=owner_data.get("address2", ""),
                            city=owner_data.get("city", ""),
                            state=owner_data.get("state", ""),
                            country=owner_data.get("country", ""),
                            postcode=owner_data.get("postcode", ""),
                            owner_type=owner_data.get("owner_type", ""),
                            owner_label=owner_data.get("owner_label", ""),
                            legal_entity_type=owner_data.get("legal_entity_type", ""),
                            legal_entity_type_label=owner_data.get("legal_entity_type_label", ""),
                        )
                        owners_cache[cache_key] = owner
                    else:
                        owner = owners_cache[cache_key]

                # Create trademark object
                trademark = Trademark(
                    keyword=item.get("keyword", "").strip() or f"Unknown-{idx}",
                    registration_number=item.get("registration_number", "").strip() or None,
                    serial_number=item.get("serial_number", "").strip() or None,
                    status_label=item.get("status_label", "").strip() or None,
                    status_code=item.get("status_code", "").strip() or None,
                    status_date=self.parse_date(item.get("status_date", "")),
                    status_definition=item.get("status_definition", "").strip() or None,
                    filing_date=self.parse_date(item.get("filing_date", "")),
                    registration_date=self.parse_date(item.get("registration_date", "")),
                    abandonment_date=self.parse_date(item.get("abandonment_date", "")),
                    expiration_date=self.parse_date(item.get("expiration_date", "")),
                    description=item.get("description", "").strip() or None,
                )

                trademarks_batch.append((trademark, owner))

                # Batch insert
                if len(trademarks_batch) >= batch_size:
                    self._bulk_insert(trademarks_batch)
                    total_imported += len(trademarks_batch)
                    trademarks_batch = []
                    self.stdout.write(self.style.SUCCESS(f"Imported {total_imported} trademarks..."))

            except Exception as e:
                total_skipped += 1
                self.stderr.write(f"Error on record {idx}: {str(e)}")

        # Insert remaining records
        if trademarks_batch:
            self._bulk_insert(trademarks_batch)
            total_imported += len(trademarks_batch)

        self.stdout.write(
            self.style.SUCCESS(f"\nImport complete! Total imported: {total_imported}, Skipped: {total_skipped}")
        )

    @transaction.atomic
    def _bulk_insert(self, trademarks_batch):
        """Bulk insert trademarks and associate owners."""
        # Extract trademarks and owners
        trademarks = [tm for tm, _ in trademarks_batch]
        owners = [owner for _, owner in trademarks_batch]

        # Bulk create trademarks
        created_trademarks = Trademark.objects.bulk_create(trademarks, ignore_conflicts=True)

        # Associate owners with trademarks
        for trademark, owner in zip(created_trademarks, owners):
            if owner:
                trademark.owners.add(owner)

    def handle(self, *args, **options):
        file_path = options["file_path"]
        batch_size = options["batch_size"]
        is_json = options["json"]
        clear_existing = options["clear"]

        if clear_existing:
            self.stdout.write(self.style.WARNING("Clearing existing trademark data..."))
            Trademark.objects.all().delete()
            TrademarkOwner.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Existing data cleared."))

        try:
            if is_json:
                self.import_from_json(file_path, batch_size)
            else:
                self.import_from_csv(file_path, batch_size)
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Import failed: {str(e)}"))
