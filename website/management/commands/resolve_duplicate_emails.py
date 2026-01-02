"""
Management command to help resolve duplicate email issues safely.

This command provides tools to:
1. Contact users with duplicate emails
2. Manually merge user accounts
3. Update email addresses
4. Preview what the migration would do

Usage:
    python manage.py resolve_duplicate_emails --list
    python manage.py resolve_duplicate_emails --contact-users
    python manage.py resolve_duplicate_emails --merge-users <from_user_id> <to_user_id>
    python manage.py resolve_duplicate_emails --update-email <user_id> <new_email>
"""

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count, Sum


class Command(BaseCommand):
    help = "Safely resolve duplicate email issues before running migration"

    def add_arguments(self, parser):
        parser.add_argument(
            "--list",
            action="store_true",
            help="List all duplicate email situations",
        )
        parser.add_argument(
            "--contact-users",
            action="store_true",
            help="Send emails to users asking them to update their email addresses",
        )
        parser.add_argument(
            "--merge-users",
            nargs=2,
            metavar=("FROM_USER_ID", "TO_USER_ID"),
            help="Merge data from one user to another (FROM_USER_ID data goes to TO_USER_ID)",
        )
        parser.add_argument(
            "--update-email",
            nargs=2,
            metavar=("USER_ID", "NEW_EMAIL"),
            help="Update a user's email address",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

    def handle(self, *args, **options):
        if options["list"]:
            self.list_duplicates()
        elif options["contact_users"]:
            self.contact_users(dry_run=options["dry_run"])
        elif options["merge_users"]:
            from_user_id, to_user_id = options["merge_users"]
            self.merge_users(int(from_user_id), int(to_user_id), dry_run=options["dry_run"])
        elif options["update_email"]:
            user_id, new_email = options["update_email"]
            self.update_email(int(user_id), new_email, dry_run=options["dry_run"])
        else:
            self.stdout.write(self.style.ERROR("Please specify an action. Use --help for options."))

    def list_duplicates(self):
        """List all duplicate email situations with user details"""
        from website.models import Issue, Points

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("DUPLICATE EMAIL RESOLUTION TOOL")
        self.stdout.write("=" * 80)

        duplicate_emails = (
            User.objects.exclude(email="")
            .exclude(email__isnull=True)
            .values("email")
            .annotate(email_count=Count("id"))
            .filter(email_count__gt=1)
            .order_by("-email_count")
        )

        if not duplicate_emails:
            self.stdout.write(self.style.SUCCESS("✅ No duplicate emails found!"))
            return

        for dup in duplicate_emails:
            email = dup["email"]
            users = User.objects.filter(email=email).order_by("-id")  # Newest first

            self.stdout.write(f"\n📧 Email: {email}")
            self.stdout.write(f"   Users: {len(users)}")

            for i, user in enumerate(users):
                # Get activity metrics
                issue_count = Issue.objects.filter(user=user).count()
                points_data = Points.objects.filter(user=user).aggregate(
                    total_points=Sum("score"), total_entries=Count("id")
                )
                total_points = points_data["total_points"] or 0

                last_login_str = user.last_login.strftime("%Y-%m-%d") if user.last_login else "Never"

                status = "WOULD KEEP" if i == 0 else "WOULD DELETE"
                style = self.style.SUCCESS if i == 0 else self.style.ERROR

                self.stdout.write(style(f"   {status}: {user.username} (ID: {user.id})"))
                self.stdout.write(f"     Joined: {user.date_joined.strftime('%Y-%m-%d')}")
                self.stdout.write(f"     Last login: {last_login_str}")
                self.stdout.write(f"     Issues: {issue_count}, Points: {total_points}")
                self.stdout.write(
                    f"     Email verified: {getattr(user, 'emailaddress_set', None) and user.emailaddress_set.filter(verified=True).exists()}"
                )

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("RESOLUTION OPTIONS:")
        self.stdout.write("1. Contact users: python manage.py resolve_duplicate_emails --contact-users")
        self.stdout.write(
            "2. Update email: python manage.py resolve_duplicate_emails --update-email <user_id> <new_email>"
        )
        self.stdout.write("3. Merge users: python manage.py resolve_duplicate_emails --merge-users <from_id> <to_id>")
        self.stdout.write("=" * 80)

    def contact_users(self, dry_run=False):
        """Send emails to users asking them to update their email addresses"""
        duplicate_emails = (
            User.objects.exclude(email="")
            .exclude(email__isnull=True)
            .values("email")
            .annotate(email_count=Count("id"))
            .filter(email_count__gt=1)
        )

        if not duplicate_emails:
            self.stdout.write(self.style.SUCCESS("✅ No duplicate emails found!"))
            return

        total_emails_sent = 0

        for dup in duplicate_emails:
            email = dup["email"]
            users = User.objects.filter(email=email).order_by("-id")

            self.stdout.write(f"\n📧 Processing email: {email}")

            for i, user in enumerate(users):
                if i == 0:  # Skip the user that would be kept
                    self.stdout.write(f"   ✅ Skipping {user.username} (would be kept)")
                    continue

                subject = "Action Required: Update Your Email Address"
                message = f"""
Dear {user.username},

We've detected that your email address ({email}) is shared with another account on our platform.

To ensure you don't lose access to your account, please log in and update your email address to a unique one.

Your account details:
- Username: {user.username}
- Account created: {user.date_joined.strftime('%Y-%m-%d')}
- Last login: {user.last_login.strftime('%Y-%m-%d') if user.last_login else 'Never'}

Please update your email address within 7 days to avoid any service interruption.

If you believe this is an error or need assistance, please contact our support team.

Best regards,
The Team
"""

                if dry_run:
                    self.stdout.write(f"   📧 Would send email to {user.username}")
                    self.stdout.write(f"      Subject: {subject}")
                    total_emails_sent += 1
                else:
                    try:
                        send_mail(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL,
                            [email],
                            fail_silently=False,
                        )
                        self.stdout.write(self.style.SUCCESS(f"   ✅ Email sent to {user.username}"))
                        total_emails_sent += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"   ❌ Failed to send email to {user.username}: {e}"))

        if dry_run:
            self.stdout.write(f"\n📊 Would send {total_emails_sent} emails")
        else:
            self.stdout.write(f"\n📊 Sent {total_emails_sent} emails")

    def merge_users(self, from_user_id, to_user_id, dry_run=False):
        """Merge data from one user account to another"""
        try:
            from_user = User.objects.get(id=from_user_id)
            to_user = User.objects.get(id=to_user_id)
        except User.DoesNotExist as e:
            raise CommandError(f"User not found: {e}")

        if from_user.email != to_user.email:
            raise CommandError("Users must have the same email address to merge")

        self.stdout.write("\n🔄 Merging user data:")
        self.stdout.write(f"   FROM: {from_user.username} (ID: {from_user_id})")
        self.stdout.write(f"   TO: {to_user.username} (ID: {to_user_id})")

        # Import models
        from website.models import Issue, Points, UserProfile

        if dry_run:
            # Show what would be merged
            issues_count = Issue.objects.filter(user=from_user).count()
            points_count = Points.objects.filter(user=from_user).count()

            self.stdout.write("\n📊 Would merge:")
            self.stdout.write(f"   Issues: {issues_count}")
            self.stdout.write(f"   Points entries: {points_count}")
            self.stdout.write("   User profile data")
            self.stdout.write("\n⚠️  FROM user would be DELETED")
        else:
            with transaction.atomic():
                # Merge issues
                issues_updated = Issue.objects.filter(user=from_user).update(user=to_user)

                # Merge points
                points_updated = Points.objects.filter(user=from_user).update(user=to_user)

                # Merge user profile data (if needed)
                try:
                    from_profile = from_user.userprofile
                    to_profile = to_user.userprofile

                    # Merge specific fields (customize as needed)
                    if not to_profile.user_avatar and from_profile.user_avatar:
                        to_profile.user_avatar = from_profile.user_avatar

                    if not to_profile.description and from_profile.description:
                        to_profile.description = from_profile.description

                    # Add visit counts
                    to_profile.visit_count += from_profile.visit_count
                    to_profile.daily_visit_count += from_profile.daily_visit_count

                    to_profile.save()
                except UserProfile.DoesNotExist:
                    pass

                # Delete the from_user
                from_user.delete()

                self.stdout.write(self.style.SUCCESS("\n✅ Successfully merged:"))
                self.stdout.write(f"   Issues: {issues_updated}")
                self.stdout.write(f"   Points entries: {points_updated}")
                self.stdout.write(f"   User {from_user.username} deleted")

    def update_email(self, user_id, new_email, dry_run=False):
        """Update a user's email address"""
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise CommandError(f"User with ID {user_id} not found")

        # Check if new email is already in use
        if User.objects.filter(email=new_email).exclude(id=user_id).exists():
            raise CommandError(f"Email {new_email} is already in use by another user")

        old_email = user.email

        if dry_run:
            self.stdout.write(f"📧 Would update email for {user.username} (ID: {user_id})")
            self.stdout.write(f"   FROM: {old_email}")
            self.stdout.write(f"   TO: {new_email}")
        else:
            user.email = new_email
            user.save()

            self.stdout.write(self.style.SUCCESS(f"✅ Updated email for {user.username}"))
            self.stdout.write(f"   FROM: {old_email}")
            self.stdout.write(f"   TO: {new_email}")

            # Also update any email verification records if using django-allauth
            try:
                from allauth.account.models import EmailAddress

                email_addresses = EmailAddress.objects.filter(user=user, email=old_email)
                for email_addr in email_addresses:
                    email_addr.email = new_email
                    email_addr.save()
                    self.stdout.write("   ✅ Updated email verification record")
            except ImportError:
                pass  # django-allauth not installed
