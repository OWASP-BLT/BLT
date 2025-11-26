"""
Management command to export all trademarks from USPTO to a CSV file.

This command fetches all ~3 million trademarks from the USPTO API and exports them
to a CSV file. It respects rate limits, handles pagination, and supports resuming
from where it left off.

Usage:
    python manage.py export_all_trademarks output.csv
    python manage.py export_all_trademarks output.csv --delay 2 --batch-size 100
    python manage.py export_all_trademarks output.csv --resume
"""

import csv
import json
import os
import time
from datetime import datetime

import requests
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Export all trademarks from USPTO API to a CSV file with rate limiting"

    def add_arguments(self, parser):
        parser.add_argument(
            "output_file",
            type=str,
            help="Path to the output CSV file",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=1.0,
            help="Delay between API requests in seconds (default: 1.0)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of results per API call (default: 100)",
        )
        parser.add_argument(
            "--resume",
            action="store_true",
            help="Resume from the last position (reads from progress file)",
        )
        parser.add_argument(
            "--max-records",
            type=int,
            default=None,
            help="Maximum number of records to fetch (for testing)",
        )

    def get_progress_file(self, output_file):
        """Get the progress file path for tracking state."""
        return f"{output_file}.progress"

    def load_progress(self, progress_file):
        """Load progress from the progress file."""
        if os.path.exists(progress_file):
            try:
                with open(progress_file, "r") as f:
                    progress = json.load(f)
                return progress
            except Exception as e:
                self.stderr.write(f"Error loading progress: {e}")
        return {"start_index": 0, "total_fetched": 0, "last_scroll_id": None}

    def save_progress(self, progress_file, start_index, total_fetched, scroll_id=None):
        """Save current progress to file."""
        progress = {
            "start_index": start_index,
            "total_fetched": total_fetched,
            "last_scroll_id": scroll_id,
            "last_updated": datetime.now().isoformat(),
        }
        with open(progress_file, "w") as f:
            json.dump(progress, f, indent=2)

    def fetch_trademark_batch(self, start_index, batch_size, scroll_id=None, delay=1.0):
        """
        Fetch a batch of trademarks from the USPTO API.

        The USPTO API supports fetching all trademarks by using a wildcard search
        or by iterating through the entire database in batches.
        """
        if not settings.USPTO_API:
            raise ValueError("USPTO_API key is not configured in settings")

        url = "https://uspto-trademark.p.rapidapi.com/v1/batchTrademarkSearch/"

        # Use a wildcard search to get all trademarks
        # The API supports pagination with start_index and scroll_id
        payload = {
            "keywords": '["*"]',  # Wildcard to match all trademarks
            "start_index": str(start_index),
        }

        if scroll_id:
            payload["scroll_id"] = scroll_id

        headers = {
            "x-rapidapi-key": settings.USPTO_API,
            "x-rapidapi-host": "uspto-trademark.p.rapidapi.com",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # Add delay to respect rate limits
        time.sleep(delay)

        try:
            response = requests.post(url, data=payload, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.stderr.write(f"API request failed: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                self.stderr.write(f"Status code: {e.response.status_code}")
                self.stderr.write(f"Response: {e.response.text[:500]}")
            raise

    def write_csv_header(self, csv_writer):
        """Write CSV header row."""
        csv_writer.writerow(
            [
                "keyword",
                "registration_number",
                "serial_number",
                "status_label",
                "status_code",
                "status_date",
                "status_definition",
                "filing_date",
                "registration_date",
                "abandonment_date",
                "expiration_date",
                "description",
                "owner_name",
                "owner_address1",
                "owner_address2",
                "owner_city",
                "owner_state",
                "owner_country",
                "owner_postcode",
                "owner_type",
                "owner_label",
                "legal_entity_type",
                "legal_entity_type_label",
            ]
        )

    def write_trademark_to_csv(self, csv_writer, trademark):
        """Write a single trademark record to CSV."""
        # Handle multiple owners by creating one row per owner
        owners = trademark.get("owners", [])

        if not owners:
            # No owners, write trademark with empty owner fields
            csv_writer.writerow(
                [
                    trademark.get("keyword", ""),
                    trademark.get("registration_number", ""),
                    trademark.get("serial_number", ""),
                    trademark.get("status_label", ""),
                    trademark.get("status_code", ""),
                    trademark.get("status_date", ""),
                    trademark.get("status_definition", ""),
                    trademark.get("filing_date", ""),
                    trademark.get("registration_date", ""),
                    trademark.get("abandonment_date", ""),
                    trademark.get("expiration_date", ""),
                    trademark.get("description", ""),
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )
        else:
            # Write one row per owner
            for owner in owners:
                csv_writer.writerow(
                    [
                        trademark.get("keyword", ""),
                        trademark.get("registration_number", ""),
                        trademark.get("serial_number", ""),
                        trademark.get("status_label", ""),
                        trademark.get("status_code", ""),
                        trademark.get("status_date", ""),
                        trademark.get("status_definition", ""),
                        trademark.get("filing_date", ""),
                        trademark.get("registration_date", ""),
                        trademark.get("abandonment_date", ""),
                        trademark.get("expiration_date", ""),
                        trademark.get("description", ""),
                        owner.get("name", ""),
                        owner.get("address1", ""),
                        owner.get("address2", ""),
                        owner.get("city", ""),
                        owner.get("state", ""),
                        owner.get("country", ""),
                        owner.get("postcode", ""),
                        owner.get("owner_type", ""),
                        owner.get("owner_label", ""),
                        owner.get("legal_entity_type", ""),
                        owner.get("legal_entity_type_label", ""),
                    ]
                )

    def handle(self, *args, **options):
        output_file = options["output_file"]
        delay = options["delay"]
        batch_size = options["batch_size"]
        resume = options["resume"]
        max_records = options["max_records"]

        progress_file = self.get_progress_file(output_file)

        # Load progress if resuming
        if resume:
            progress = self.load_progress(progress_file)
            start_index = progress["start_index"]
            total_fetched = progress["total_fetched"]
            scroll_id = progress.get("last_scroll_id")
            self.stdout.write(
                self.style.SUCCESS(f"Resuming from index {start_index}, {total_fetched} records already fetched")
            )
            file_mode = "a"
        else:
            start_index = 0
            total_fetched = 0
            scroll_id = None
            file_mode = "w"

        self.stdout.write(
            f"Starting trademark export to {output_file}\n"
            f"Delay between requests: {delay}s\n"
            f"Batch size: {batch_size}\n"
        )

        start_time = time.time()
        consecutive_errors = 0
        max_consecutive_errors = 5

        try:
            with open(output_file, file_mode, newline="", encoding="utf-8") as csvfile:
                csv_writer = csv.writer(csvfile)

                # Write header if starting fresh
                if not resume:
                    self.write_csv_header(csv_writer)

                while True:
                    # Check if we've reached the maximum
                    if max_records and total_fetched >= max_records:
                        self.stdout.write(self.style.SUCCESS(f"Reached maximum records limit: {max_records}"))
                        break

                    try:
                        self.stdout.write(f"Fetching batch starting at index {start_index}...")

                        # Fetch batch from API
                        response_data = self.fetch_trademark_batch(start_index, batch_size, scroll_id, delay)

                        # Extract results and scroll_id
                        results = response_data.get("results", [])
                        scroll_id = response_data.get("scroll_id")
                        total_count = response_data.get("count", 0)

                        if not results:
                            self.stdout.write(self.style.SUCCESS("No more results. Export complete!"))
                            break

                        # Write results to CSV
                        for trademark in results:
                            self.write_trademark_to_csv(csv_writer, trademark)

                        total_fetched += len(results)
                        start_index += batch_size

                        # Save progress
                        self.save_progress(progress_file, start_index, total_fetched, scroll_id)

                        # Calculate ETA
                        elapsed = time.time() - start_time
                        rate = total_fetched / elapsed if elapsed > 0 else 0
                        remaining = total_count - total_fetched if total_count > 0 else 0
                        eta_seconds = remaining / rate if rate > 0 else 0
                        eta_hours = eta_seconds / 3600

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Fetched {len(results)} records. "
                                f"Total: {total_fetched}/{total_count if total_count > 0 else '?'} "
                                f"({rate:.1f} records/sec, ETA: {eta_hours:.1f}h)"
                            )
                        )

                        # Reset error counter on success
                        consecutive_errors = 0

                    except Exception as e:
                        consecutive_errors += 1
                        self.stderr.write(
                            self.style.ERROR(
                                f"Error fetching batch (attempt {consecutive_errors}/{max_consecutive_errors}): {str(e)}"
                            )
                        )

                        if consecutive_errors >= max_consecutive_errors:
                            self.stderr.write(self.style.ERROR("Too many consecutive errors. Stopping export."))
                            break

                        # Exponential backoff on errors
                        backoff_delay = delay * (2**consecutive_errors)
                        self.stdout.write(f"Waiting {backoff_delay}s before retry...")
                        time.sleep(backoff_delay)

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING(f"\nExport interrupted by user. Progress saved to {progress_file}"))
            return

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Fatal error: {str(e)}"))
            raise

        elapsed = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(
                f"\nExport complete!\n"
                f"Total records: {total_fetched}\n"
                f"Time elapsed: {elapsed/3600:.2f} hours\n"
                f"Output file: {output_file}\n"
            )
        )

        # Clean up progress file on successful completion
        if os.path.exists(progress_file):
            os.remove(progress_file)
