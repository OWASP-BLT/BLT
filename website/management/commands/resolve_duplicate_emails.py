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
        failed_emails = []

        for dup in duplicate_emails:
            email = dup["email"]
            users = User.objects.filter(email=email).order_by("-id")

            # Get users that would be deleted (all except the first/newest)
            users_to_contact = list(users[1:])
            kept_user = users.first()

            if not users_to_contact:
                continue

            self.stdout.write(f"\n📧 Processing email group: {email}")
            self.stdout.write(f"   Users affected: {len(users_to_contact)}")
            self.stdout.write(f"   User to keep: {kept_user.username}")

            # Build message with all affected usernames
            affected_usernames = [user.username for user in users_to_contact]

            subject = "Action Required: Update Your Email Address"
            message = f"""
Dear user,

We've detected that your email address ({email}) is shared with multiple accounts on our platform.

The following accounts are affected:
{chr(10).join(f'- {username}' for username in affected_usernames)}

To ensure you don't lose access to your account(s), please log in and update your email address to a unique one for each account.

The account "{kept_user.username}" will be preserved, and other accounts with this email will be removed if not updated.

Please update your email addresses within 7 days to avoid any service interruption.

If you believe this is an error or need assistance, please contact our support team.

Best regards,
The Team
"""

            if dry_run:
                self.stdout.write(f"   📧 Would send email to {email}")
                self.stdout.write(f"      Subject: {subject}")
                self.stdout.write(f"      Affected users: {', '.join(affected_usernames)}")
                total_emails_sent += 1
            else:
                # Retry logic with exponential backoff - send once per email group
                max_retries = 3
                retry_count = 0
                sent = False

                while retry_count < max_retries and not sent:
                    try:
                        send_mail(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL,
                            [email],
                            fail_silently=False,
                        )
                        self.stdout.write(self.style.SUCCESS(f"   ✅ Email sent to {email}"))
                        self.stdout.write(f"      Notified users: {', '.join(affected_usernames)}")
                        total_emails_sent += 1
                        sent = True
                    except Exception as e:
                        retry_count += 1
                        if retry_count >= max_retries:
                            failed_emails.append(
                                {
                                    "email": email,
                                    "affected_users": affected_usernames,
                                    "error": str(e),
                                    "attempts": retry_count,
                                }
                            )
                            self.stdout.write(
                                self.style.ERROR(
                                    f"   ❌ Failed to send email to {email} after {max_retries} attempts: {e}"
                                )
                            )
                        else:
                            self.stdout.write(self.style.WARNING(f"   ⚠️ Retry {retry_count}/{max_retries} for {email}"))
                            import time

                            time.sleep(2**retry_count)  # Exponential backoff

        # Export failure report if any failures occurred
        if failed_emails and not dry_run:
            import json

            from django.utils import timezone

            failure_report = f"email_failures_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(failure_report, "w") as f:
                json.dump(failed_emails, f, indent=2, default=str)
            self.stdout.write(self.style.WARNING(f"\n⚠️ Failed emails logged to: {failure_report}"))

        if dry_run:
            self.stdout.write(f"\n📊 Would send {total_emails_sent} emails")
        else:
            self.stdout.write(f"\n📊 Summary: {total_emails_sent} sent, {len(failed_emails)} failed")

    def merge_users(self, from_user_id, to_user_id, dry_run=False):
        """Merge data from one user account to another with comprehensive FK handling"""
        try:
            from_user = User.objects.get(id=from_user_id)
            to_user = User.objects.get(id=to_user_id)
        except User.DoesNotExist as e:
            raise CommandError(f"User not found: {e}")

        if from_user.email != to_user.email:
            raise CommandError("Users must have the same email address to merge")

        if from_user.id == to_user.id:
            raise CommandError("Cannot merge a user with themselves")

        self.stdout.write("\n🔄 Merging user data:")
        self.stdout.write(f"   FROM: {from_user.username} (ID: {from_user_id})")
        self.stdout.write(f"   TO: {to_user.username} (ID: {to_user_id})")

        # Import all models that reference User
        from website.models import (
            Activity,
            Bid,
            ForumPost,
            ForumPostComment,
            HuntResult,
            Issue,
            Organization,
            Points,
            StakingEntry,
            StakingTransaction,
            UserProfile,
        )

        if dry_run:
            # Show what would be merged
            merge_counts = {}
            merge_counts["issues"] = Issue.objects.filter(user=from_user).count()
            merge_counts["issues_closed_by"] = Issue.objects.filter(closed_by=from_user).count()
            merge_counts["points"] = Points.objects.filter(user=from_user).count()
            merge_counts["hunt_results_winner"] = HuntResult.objects.filter(winner=from_user).count()
            merge_counts["hunt_results_runner"] = HuntResult.objects.filter(runner=from_user).count()
            merge_counts["hunt_results_second_runner"] = HuntResult.objects.filter(second_runner=from_user).count()
            merge_counts["bids"] = Bid.objects.filter(user=from_user).count()
            merge_counts["forum_posts"] = ForumPost.objects.filter(user=from_user).count()
            merge_counts["forum_comments"] = ForumPostComment.objects.filter(user=from_user).count()
            merge_counts["activities"] = Activity.objects.filter(user=from_user).count()
            merge_counts["staking_entries"] = StakingEntry.objects.filter(user=from_user).count()
            merge_counts["staking_transactions"] = StakingTransaction.objects.filter(user=from_user).count()

            self.stdout.write("\n📊 Would merge:")
            for field, count in merge_counts.items():
                if count > 0:
                    self.stdout.write(f"   {field}: {count}")

            # Check ManyToMany relationships
            m2m_counts = {}
            m2m_counts["issue_teams"] = Issue.objects.filter(team_members=from_user).count()
            m2m_counts["org_managers"] = Organization.objects.filter(managers=from_user).count()
            m2m_counts["activity_likes"] = Activity.objects.filter(likes=from_user).count()
            m2m_counts["activity_dislikes"] = Activity.objects.filter(dislikes=from_user).count()
            m2m_counts["profile_subscriptions"] = UserProfile.objects.filter(subscribed_users=from_user).count()

            # Check optional M2M relationships
            try:
                from website.models import Domain

                m2m_counts["domain_managers"] = Domain.objects.filter(managers=from_user).count()
            except ImportError:
                pass

            try:
                from website.models import Referral

                m2m_counts["referral_recipients"] = Referral.objects.filter(recipients=from_user).count()
            except ImportError:
                pass

            try:
                from website.models import Challenge

                m2m_counts["challenge_participants"] = Challenge.objects.filter(participants=from_user).count()
            except ImportError:
                pass

            try:
                from website.models import ChatRoom

                m2m_counts["chatroom_users"] = ChatRoom.objects.filter(users=from_user).count()
            except ImportError:
                pass

            try:
                from website.models import Thread

                m2m_counts["thread_participants"] = Thread.objects.filter(participants=from_user).count()
            except ImportError:
                pass

            for field, count in m2m_counts.items():
                if count > 0:
                    self.stdout.write(f"   {field}: {count}")

            self.stdout.write("   User profile data")
            self.stdout.write("\n⚠️  FROM user would be DELETED")
        else:
            with transaction.atomic():
                merge_counts = {}

                # Merge all ForeignKey relationships
                merge_counts["issues"] = Issue.objects.filter(user=from_user).update(user=to_user)
                merge_counts["issues_closed_by"] = Issue.objects.filter(closed_by=from_user).update(closed_by=to_user)
                merge_counts["points"] = Points.objects.filter(user=from_user).update(user=to_user)
                merge_counts["hunt_results_winner"] = HuntResult.objects.filter(winner=from_user).update(winner=to_user)
                merge_counts["hunt_results_runner"] = HuntResult.objects.filter(runner=from_user).update(runner=to_user)
                merge_counts["hunt_results_second_runner"] = HuntResult.objects.filter(second_runner=from_user).update(
                    second_runner=to_user
                )
                merge_counts["bids"] = Bid.objects.filter(user=from_user).update(user=to_user)
                merge_counts["forum_posts"] = ForumPost.objects.filter(user=from_user).update(user=to_user)
                merge_counts["forum_comments"] = ForumPostComment.objects.filter(user=from_user).update(user=to_user)
                merge_counts["activities"] = Activity.objects.filter(user=from_user).update(user=to_user)
                merge_counts["staking_entries"] = StakingEntry.objects.filter(user=from_user).update(user=to_user)
                merge_counts["staking_transactions"] = StakingTransaction.objects.filter(user=from_user).update(
                    user=to_user
                )

                # Handle ManyToMany relationships
                m2m_transfers = 0

                # For Issue.team_members - add from_user's memberships to to_user
                issues_with_from_user = Issue.objects.filter(team_members=from_user)
                for issue in issues_with_from_user:
                    issue.team_members.add(to_user)
                    issue.team_members.remove(from_user)
                    m2m_transfers += 1

                # For Organization.managers - add from_user's managerships to to_user
                orgs_managed_by_from_user = Organization.objects.filter(managers=from_user)
                for org in orgs_managed_by_from_user:
                    org.managers.add(to_user)
                    org.managers.remove(from_user)
                    m2m_transfers += 1

                # Transfer Activity likes
                activities_liked = Activity.objects.filter(likes=from_user)
                for activity in activities_liked:
                    if not activity.likes.filter(id=to_user.id).exists():
                        activity.likes.add(to_user)
                    activity.likes.remove(from_user)
                    m2m_transfers += 1

                # Transfer Activity dislikes
                activities_disliked = Activity.objects.filter(dislikes=from_user)
                for activity in activities_disliked:
                    if not activity.dislikes.filter(id=to_user.id).exists():
                        activity.dislikes.add(to_user)
                    activity.dislikes.remove(from_user)
                    m2m_transfers += 1

                # Transfer UserProfile subscriptions
                profiles_subscribed_to = UserProfile.objects.filter(subscribed_users=from_user)
                for profile in profiles_subscribed_to:
                    if not profile.subscribed_users.filter(id=to_user.id).exists():
                        profile.subscribed_users.add(to_user)
                    profile.subscribed_users.remove(from_user)
                    m2m_transfers += 1

                # Transfer Domain managerships
                try:
                    from website.models import Domain

                    domains_managed = Domain.objects.filter(managers=from_user)
                    for domain in domains_managed:
                        if not domain.managers.filter(id=to_user.id).exists():
                            domain.managers.add(to_user)
                        domain.managers.remove(from_user)
                        m2m_transfers += 1
                except ImportError:
                    pass  # Domain model might not exist

                # Transfer Referral recipients
                try:
                    from website.models import Referral

                    referrals_received = Referral.objects.filter(recipients=from_user)
                    for referral in referrals_received:
                        if not referral.recipients.filter(id=to_user.id).exists():
                            referral.recipients.add(to_user)
                        referral.recipients.remove(from_user)
                        m2m_transfers += 1
                except ImportError:
                    pass  # Referral model might not exist

                # Transfer Challenge participations
                try:
                    from website.models import Challenge

                    challenges_participated = Challenge.objects.filter(participants=from_user)
                    for challenge in challenges_participated:
                        if not challenge.participants.filter(id=to_user.id).exists():
                            challenge.participants.add(to_user)
                        challenge.participants.remove(from_user)
                        m2m_transfers += 1
                except ImportError:
                    pass  # Challenge model might not exist

                # Transfer ChatRoom memberships
                try:
                    from website.models import ChatRoom

                    chatrooms_joined = ChatRoom.objects.filter(users=from_user)
                    for chatroom in chatrooms_joined:
                        if not chatroom.users.filter(id=to_user.id).exists():
                            chatroom.users.add(to_user)
                        chatroom.users.remove(from_user)
                        m2m_transfers += 1
                except ImportError:
                    pass  # ChatRoom model might not exist

                # Transfer Thread participations
                try:
                    from website.models import Thread

                    threads_participated = Thread.objects.filter(participants=from_user)
                    for thread in threads_participated:
                        if not thread.participants.filter(id=to_user.id).exists():
                            thread.participants.add(to_user)
                        thread.participants.remove(from_user)
                        m2m_transfers += 1
                except ImportError:
                    pass  # Thread model might not exist

                if m2m_transfers > 0:
                    self.stdout.write(f"   ✅ Transferred {m2m_transfers} M2M relationships")

                # Merge user profile data with proper error handling
                try:
                    # Ensure to_user has a profile (create if needed)
                    to_profile, created = UserProfile.objects.get_or_create(user=to_user)
                    if created:
                        self.stdout.write("   ✅ Created UserProfile for target user")

                    # Try to get from_user profile
                    try:
                        from_profile = from_user.userprofile

                        # Merge specific fields (only if target field is empty)
                        if not to_profile.user_avatar and from_profile.user_avatar:
                            to_profile.user_avatar = from_profile.user_avatar

                        if not to_profile.description and from_profile.description:
                            to_profile.description = from_profile.description

                        # Add visit counts
                        to_profile.visit_count += from_profile.visit_count
                        to_profile.daily_visit_count += from_profile.daily_visit_count

                        to_profile.save()
                        self.stdout.write("   ✅ Merged UserProfile data")

                    except UserProfile.DoesNotExist:
                        self.stdout.write("   ℹ️ FROM user has no UserProfile to merge")

                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"   ⚠️ UserProfile merge failed: {e}"))

                # Store username before deletion
                from_username = from_user.username

                # Delete the from_user (this will cascade to any remaining relationships)
                from_user.delete()

                self.stdout.write(self.style.SUCCESS("\n✅ Successfully merged:"))
                for field, count in merge_counts.items():
                    if count > 0:
                        self.stdout.write(f"   {field}: {count}")
                self.stdout.write(f"   User {from_username} deleted")

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
            try:
                with transaction.atomic():
                    # Update user email
                    user.email = new_email
                    user.save()

                    # Also update any email verification records if using django-allauth
                    try:
                        from allauth.account.models import EmailAddress

                        email_addresses = EmailAddress.objects.filter(user=user, email=old_email)
                        for email_addr in email_addresses:
                            email_addr.email = new_email
                            email_addr.save()

                        if email_addresses:
                            self.stdout.write("   ✅ Updated email verification records")
                    except ImportError:
                        pass  # django-allauth not installed

                    self.stdout.write(self.style.SUCCESS(f"✅ Updated email for {user.username}"))
                    self.stdout.write(f"   FROM: {old_email}")
                    self.stdout.write(f"   TO: {new_email}")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Failed to update email for {user.username}: {e}"))
                raise CommandError(f"Email update failed: {e}")
