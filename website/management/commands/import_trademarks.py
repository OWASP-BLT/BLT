import csv

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date

from website.models import Trademark, TrademarkOwner

BATCH_SIZE = 5000


# Helpers
def safe_trim(value, max_len):
    if not value:
        return None
    value = value.strip()
    return value[:max_len] if value else None


def safe_date(value):
    if not value:
        return None
    return parse_date(value)


# Command
class Command(BaseCommand):
    help = "Import USPTO trademark data from case_file.csv + owner.csv"

    def add_arguments(self, parser):
        parser.add_argument("case_file_csv", type=str)
        parser.add_argument("owner_csv", type=str)

    def handle(self, *args, **options):
        case_file = options["case_file_csv"]
        owner_file = options["owner_csv"]

        self.stdout.write(f"Importing trademarks from {case_file}...")
        serial_map = self.import_trademarks(case_file)

        self.stdout.write(f"Importing owners from {owner_file}...")
        created_owners, linked = self.import_owners(owner_file, serial_map)

        self.stdout.write(
            self.style.SUCCESS(f"Imported {created_owners} owners and linked {linked} trademark-owner relationships")
        )
        self.stdout.write(self.style.SUCCESS("USPTO import completed."))

    # Trademark Import
    def import_trademarks(self, csv_path):
        serial_map = {}  # serial_no -> Trademark.pk
        batch = []
        total = 0

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                serial_no = row.get("serial_no")
                if not serial_no:
                    continue

                batch.append(
                    Trademark(
                        serial_number=serial_no,
                        registration_number=row.get("registration_no") or None,
                        keyword=row.get("mark_id_char") or serial_no,
                        status_code=row.get("cfh_status_cd"),
                        status_date=safe_date(row.get("cfh_status_dt")),
                        filing_date=safe_date(row.get("filing_dt")),
                        registration_date=safe_date(row.get("registration_dt")),
                        abandonment_date=safe_date(row.get("abandon_dt")),
                        expiration_date=safe_date(row.get("reg_cancel_dt")),
                    )
                )

                if len(batch) >= BATCH_SIZE:
                    total += self._flush_trademarks(batch, serial_map)
                    batch.clear()

            if batch:
                total += self._flush_trademarks(batch, serial_map)

        self.stdout.write(self.style.SUCCESS(f"Imported {total} trademarks"))
        return serial_map

    def _flush_trademarks(self, batch, serial_map):
        Trademark.objects.bulk_create(
            batch,
            batch_size=BATCH_SIZE,
            ignore_conflicts=True,
        )

        serials = [tm.serial_number for tm in batch]

        # Map serial → PK (NOT full object)
        for serial, pk in Trademark.objects.filter(serial_number__in=serials).values_list("serial_number", "pk"):
            serial_map[serial] = pk

        return len(serials)

    # Owner Import
    def import_owners(self, csv_path, serial_map):
        created_owners = 0
        linked = 0

        with open(csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                row = {k.strip().lower(): (v.strip() or None) for k, v in row.items()}

                serial = row.get("serial_no")
                tm_id = serial_map.get(serial)

                if not tm_id:
                    continue

                # REQUIRED fallback (prevents IntegrityError)
                owner_name = safe_trim(row.get("own_name"), 255) or f"OWNER_{serial}"

                owner, created = TrademarkOwner.objects.get_or_create(
                    name=owner_name,
                    defaults={
                        "address1": safe_trim(row.get("own_addr_1"), 255),
                        "address2": safe_trim(row.get("own_addr_2"), 255),
                        "city": safe_trim(row.get("own_addr_city"), 100),
                        "state": safe_trim(row.get("own_addr_state_cd"), 100),
                        "country": safe_trim(row.get("own_addr_country_cd"), 100),
                        "postcode": safe_trim(row.get("own_addr_postal"), 20),
                        "owner_type": safe_trim(row.get("own_type_cd"), 20),
                        "owner_label": safe_trim(row.get("own_entity_desc"), 100),
                        "legal_entity_type": safe_trim(row.get("own_entity_cd"), 20),
                        "legal_entity_type_label": safe_trim(row.get("own_nalty_country_cd"), 100),
                    },
                )

                if created:
                    created_owners += 1

                Trademark.owners.through.objects.get_or_create(
                    trademark_id=tm_id,
                    trademarkowner_id=owner.pk,
                )
                linked += 1

        return created_owners, linked
