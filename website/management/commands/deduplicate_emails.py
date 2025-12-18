import logging

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import models, transaction
from django.db.models.functions import Lower

logger = logging.getLogger(__name__)
User = get_user_model()


def mask_email(email):
    """Masks an email address to prevent PII exposure, e.g., u***@example.com."""
    if not isinstance(email, str) or "@" not in email:
        return "***"  # Return a generic mask for invalid input

    local_part, domain = email.split("@", 1)
    if len(local_part) <= 1:
        masked_local = "***"
    else:
        masked_local = f"{local_part[0]}***"

    return f"{masked_local}@{domain}"


class Command(BaseCommand):
    help = (
        "Deduplicates email addresses in allauth.account.EmailAddress table to prepare for ACCOUNT_UNIQUE_EMAIL = True."
    )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting email deduplication..."))

        # 1. Find all duplicate emails
        # This query finds emails that appear more than once, ignoring case.
        duplicate_emails_qs = (
            EmailAddress.objects.annotate(email_lower=Lower("email"))
            .values("email_lower")
            .annotate(email_count=models.Count("email_lower"))
            .filter(email_count__gt=1)
        )

        duplicate_emails = [item["email_lower"] for item in duplicate_emails_qs]

        if not duplicate_emails:
            self.stdout.write(self.style.SUCCESS("No duplicate emails found. Exiting."))
            return

        self.stdout.write(self.style.WARNING(f"Found {len(duplicate_emails)} unique email addresses with duplicates."))

        with transaction.atomic():
            for email in duplicate_emails:
                masked_email = mask_email(email)
                self.stdout.write(f"Processing duplicates for email: {masked_email}")
                # Get all EmailAddress objects for this email
                # Order by: verified (True first), primary (True first), then oldest (pk)
                email_addresses = EmailAddress.objects.filter(email__iexact=email).order_by(
                    "-verified", "-primary", "pk"
                )

                if not email_addresses.exists():  # pragma: no cover
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
                                f"Kept email {keep_email_address.pk} for {masked_email} had no user. "
                                f"Assigning user {found_user_id} to {keep_email_address.pk}."
                            )
                        )
                        keep_email_address.user_id = found_user_id
                        keep_email_address.save(update_fields=["user_id"])
                    else:  # pragma: no cover
                        self.stdout.write(
                            self.style.ERROR(
                                f'Could not find an associated user for any email address related to "{masked_email}". '
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
                                f'Email "{masked_email}" (ID: {keep_email_address.pk}) was not verified, '
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
                                f'Email "{masked_email}" (ID: {keep_email_address.pk}) was not primary, '
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

                # --- Final Safety Checks Before Deletion ---

                # 1. Check for cross-user duplicates. If the same email is tied to multiple users,
                #    this is a serious data integrity issue that should be manually reviewed.
                user_ids_for_email = set(email_addresses.values_list("user_id", flat=True).distinct())
                user_ids_for_email.discard(None)  # Ignore entries not linked to any user

                if len(user_ids_for_email) > 1:
                    self.stdout.write(
                        self.style.ERROR(
                            f'CRITICAL: Email "{masked_email}" is linked to multiple users: {list(user_ids_for_email)}. '
                            "Skipping deletion. Manual intervention is required."
                        )
                    )
                    continue  # Skip to the next duplicate email

                # 2. Ensure we don't delete a user's last email address.
                user = keep_email_address.user
                if user and user.emailaddress_set.count() <= delete_email_addresses.count():
                    self.stdout.write(
                        self.style.ERROR(
                            f"CRITICAL: Deleting duplicates for '{masked_email}' would leave user {user.id} with no email addresses. Skipping deletion."
                        )
                    )
                    continue

                # Delete the redundant entries
                deleted_count, _ = delete_email_addresses.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully kept EmailAddress ID {keep_email_address.pk} for "{masked_email}" '
                        f"and deleted {deleted_count} duplicate(s)."
                    )
                )

        self.stdout.write(self.style.SUCCESS("Email deduplication complete."))
