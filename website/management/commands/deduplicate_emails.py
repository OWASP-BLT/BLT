import logging

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import models, transaction

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = (
        "Deduplicates email addresses in allauth.account.EmailAddress table to prepare for ACCOUNT_UNIQUE_EMAIL = True."
    )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting email deduplication..."))

        # 1. Find all duplicate emails
        # This query finds emails that appear more than once
        duplicate_emails_qs = (
            EmailAddress.objects.values("email").annotate(email_count=models.Count("email")).filter(email_count__gt=1)
        )

        duplicate_emails = [item["email"] for item in duplicate_emails_qs]

        if not duplicate_emails:
            self.stdout.write(self.style.SUCCESS("No duplicate emails found. Exiting."))
            return

        self.stdout.write(self.style.WARNING(f"Found {len(duplicate_emails)} unique email addresses with duplicates."))

        with transaction.atomic():
            for email in duplicate_emails:
                self.stdout.write(f"Processing duplicates for email: {email}")
                # Get all EmailAddress objects for this email
                # Order by: verified (True first), primary (True first), then oldest (pk)
                email_addresses = EmailAddress.objects.filter(email__iexact=email).order_by(
                    "-verified", "-primary", "pk"
                )

                if not email_addresses.exists():
                    self.stdout.write(
                        self.style.WARNING(
                            f"No email addresses found for {email} (might have been deleted by another process). Skipping."
                        )
                    )
                    continue

                # The first one in the ordered queryset is the one to keep
                keep_email_address = email_addresses.first()
                delete_email_addresses = email_addresses.exclude(pk=keep_email_address.pk)

                # --- Data Integrity Checks and Merging Logic ---

                # Ensure the kept email is linked to a user.
                # If the chosen `keep_email_address` has no user, try to find one from the duplicates.
                if not keep_email_address.user_id:  # Use user_id for efficiency
                    found_user_id = None
                    for ea in delete_email_addresses:
                        if ea.user_id:
                            found_user_id = ea.user_id
                            break
                    if found_user_id:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Kept email {keep_email_address.pk} for {email} had no user. "
                                f"Assigning user {found_user_id} to {keep_email_address.pk}."
                            )
                        )
                        keep_email_address.user_id = found_user_id
                        keep_email_address.save(update_fields=["user_id"])
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f'Could not find an associated user for any email address related to "{email}". '
                                "This indicates a deeper data inconsistency. Skipping deletion for this email."
                            )
                        )
                        # Skip deletion for this email if no user can be associated
                        continue

                # Merge 'verified' status: if any duplicate was verified, the kept one should be.
                if not keep_email_address.verified:
                    if any(ea.verified for ea in delete_email_addresses):
                        self.stdout.write(
                            self.style.WARNING(
                                f'Email "{email}" (ID: {keep_email_address.pk}) was not verified, '
                                "but a duplicate was. Setting to verified."
                            )
                        )
                        keep_email_address.verified = True
                        keep_email_address.save(update_fields=["verified"])

                # Merge 'primary' status: if any duplicate was primary, the kept one should be.
                # Ensure only one primary email per user.
                if not keep_email_address.primary:
                    if any(ea.primary for ea in delete_email_addresses):
                        self.stdout.write(
                            self.style.WARNING(
                                f'Email "{email}" (ID: {keep_email_address.pk}) was not primary, '
                                "but a duplicate was. Setting to primary."
                            )
                        )
                        # Demote any other primary email for this user first
                        EmailAddress.objects.filter(user=keep_email_address.user, primary=True).exclude(
                            pk=keep_email_address.pk
                        ).update(primary=False)

                        keep_email_address.primary = True
                        keep_email_address.save(update_fields=["primary"])
                else:
                    # If the kept email is already primary, ensure no other emails for this user are primary.
                    EmailAddress.objects.filter(user=keep_email_address.user, primary=True).exclude(
                        pk=keep_email_address.pk
                    ).update(primary=False)

                # Delete the redundant entries
                deleted_count, _ = delete_email_addresses.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully kept EmailAddress ID {keep_email_address.pk} for "{email}" '
                        f"and deleted {deleted_count} duplicate(s)."
                    )
                )

        self.stdout.write(self.style.SUCCESS("Email deduplication complete."))
