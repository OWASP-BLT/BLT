from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import (
    Activity,
    Badge,
    Bid,
    Challenge,
    Hunt,
    IpReport,
    Issue,
    Points,
    Post,
    Suggestion,
    TimeLog,
    UserBadge,
    UserProfile,
)


def get_default_user():
    """Get or create a default 'anonymous' user."""
    return User.objects.get_or_create(username="anonymous")[0]


# Helper function to assign the badge based on action
def assign_first_action_badge(user, action_title):
    """Assign badges for first-time actions."""
    if user is not None and user.is_authenticated:
        badge, created = Badge.objects.get_or_create(title=action_title, type="automatic")

        if not UserBadge.objects.filter(user=user, badge=badge).exists():
            UserBadge.objects.get_or_create(user=user, badge=badge)
            print(f"Assigned '{action_title}' badge to {user.username}")


def create_activity(instance, action_type):
    """Generic function to create an activity for a given model instance."""
    model_name = instance._meta.model_name
    user_field = (
        getattr(instance, "user", None)
        or getattr(instance, "author", None)
        or getattr(instance, "modified_by", None)
    )
    user = user_field or get_default_user()

    # Get the content type of the instance
    content_type = ContentType.objects.get_for_model(instance)

    # Create the activity
    Activity.objects.create(
        user=user,
        action_type=action_type,
        title=f"{model_name.capitalize()} {action_type.capitalize()} {getattr(instance, 'name', getattr(instance, 'title', ''))[:50]}",
        content_type=content_type,
        object_id=instance.id,  # Use object_id for GenericForeignKey
        description=getattr(instance, "description", getattr(instance, "content", ""))[:100],
        image=getattr(instance, "screenshot", getattr(instance, "image", None)),
    )


def update_challenge_progress(
    user, challenge_title, model_class, reason, threshold=None, team_threshold=None
):
    try:
        # Get the user's challenge
        challenge = Challenge.objects.get(title=challenge_title)

        # If it's a team challenge, use the team participants
        if challenge.challenge_type == "team":
            # Get the user's team
            user_profile = user.userprofile
            if user_profile.team is None:
                return

            team = user_profile.team
            if team not in challenge.team_participants.all():
                challenge.team_participants.add(team)

            total_actions = 0
            for member in team.user_profiles.all():
                total_actions += model_class.objects.filter(user=member.user).count()

            # Calculate progress based on actions performed by the team
            team_progress = min((total_actions / team_threshold) * 100, 100)

            challenge.progress = int(team_progress)
            challenge.save()

            if team_progress == 100 and not challenge.is_completed():
                challenge.completed = True  # Explicitly mark the challenge as completed
                challenge.completed_at = timezone.now()  # Track completion time (optional)
                challenge.save()  # Save changes to the challenge

                # Award points to the team
                team.team_points += challenge.points
                team.save()
        else:
            if user not in challenge.participants.all():
                challenge.participants.add(user)

            # Calculate progress as a percentage
            user_count = model_class.objects.filter(user=user).count()
            progress = min((user_count / threshold) * 100, 100)  # Ensure it doesn't exceed 100%

            # Update the challenge progress
            challenge.progress = int(progress)
            challenge.save()
            print(challenge.progress)
            # Award points if the challenge is completed
            if progress == 100 and not challenge.is_completed():
                challenge.completed = True  # Explicitly mark the challenge as completed
                challenge.completed_at = timezone.now()
                challenge.save()

                # Award points to the user
                Points.objects.create(user=user, score=challenge.points, reason=reason)

    except Challenge.DoesNotExist:
        # If the challenge doesn't exist, do nothing or handle the exception as needed
        pass


def update_challenge_progress_for_team_sign_in(user, challenge_title):
    """
    Update progress for a team challenge where all members must sign in for 5 days.
    """
    try:
        # Get the challenge object
        challenge = Challenge.objects.get(title=challenge_title, challenge_type="team")

        # Get the user's profile and team
        user_profile = user.userprofile
        if not user_profile.team:
            return  # User is not part of a team

        team = user_profile.team

        # Ensure the team is registered as a participant
        if team not in challenge.team_participants.all():
            challenge.team_participants.add(team)

        # Check streaks for all team members
        all_members = team.user_profiles.all()
        team_completed_days = []

        for member in all_members:
            # Calculate streak for each member
            if member.current_streak >= 5:
                team_completed_days.append(member)

        # Calculate progress based on the number of members who meet the condition
        total_members = all_members.count()
        if total_members > 0:
            team_progress = min((len(team_completed_days) / total_members) * 100, 100)
        else:
            team_progress = 0  # No team members

        # Update challenge progress
        challenge.progress = int(team_progress)
        challenge.save()

        # Award points to the team if the challenge is completed
        if team_progress == 100 and not challenge.is_completed():
            challenge.completed = True
            challenge.completed_at = timezone.now()
            challenge.save()

            # Add points to the team
            team.team_points += challenge.points
            team.save()

    except Challenge.DoesNotExist:
        # Handle case where the challenge is not found
        pass


@receiver(post_save)
def handle_post_save(sender, instance, created, **kwargs):
    """Generic handler for post_save signal."""
    if sender == IpReport and created:  # Track first IP report
        assign_first_action_badge(instance.user, "First IP Reported")
        create_activity(instance, "created")

        update_challenge_progress(
            user=instance.user,
            challenge_title="Report 5 IPs",
            model_class=IpReport,
            reason="Completed 'Report 5 IPs' challenge",
            threshold=5,
        )
        if instance.user.userprofile.team:
            update_challenge_progress(
                user=instance.user,
                challenge_title="Report 10 IPs",
                model_class=IpReport,
                reason="Completed 'Report 10 IPs' challenge",
                team_threshold=10,  # For team challenge
            )

    elif sender == Post and created:  # Track first blog post
        assign_first_action_badge(instance.author, "First Blog Posted")
        create_activity(instance, "created")

    elif sender == Issue and created:  # Track first bug report
        assign_first_action_badge(instance.user, "First Bug Reported")
        create_activity(instance, "created")

        update_challenge_progress(
            user=instance.user,
            challenge_title="Report 5 Issues",
            model_class=Issue,
            reason="Completed 'Report 5 Issues' challenge",
            threshold=5,
        )
        if instance.user.userprofile.team:
            update_challenge_progress(
                user=instance.user,
                challenge_title="Report 10 Issues",
                model_class=Issue,
                reason="Completed 'Report 10 Issues' challenge",
                team_threshold=10,  # For team challenge
            )

    elif sender == Hunt and created:  # Track first bid placed
        assign_first_action_badge(instance.user, "First Bug Bounty")
        create_activity(instance, "created")

    elif sender == Suggestion and created:  # Track first suggestion
        assign_first_action_badge(instance.user, "First Suggestion")
        create_activity(instance, "suggested")

    elif sender == Bid and created:  # Track first bid placed
        assign_first_action_badge(instance.user, "First Bid Placed")
        create_activity(instance, "placed")

    elif sender is User and created:  # Handle user sign-up
        Activity.objects.create(
            user=instance,
            action_type="signup",
            title=f"New User Signup: {instance.username}",
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.id,
            description=f"Welcome to the community {instance.username}!",
        )


@receiver(pre_delete)
def handle_pre_delete(sender, instance, **kwargs):
    """Generic handler for pre_delete signal."""
    if sender in [Issue, Hunt, IpReport, Post]:  # Add any model you want to track
        create_activity(instance, "deleted")


@receiver(post_save, sender=TimeLog)
def update_user_streak(sender, instance, created, **kwargs):
    """
    Signal triggered when a TimeLog entry is created. Updates the user's streak
    and handles progress for both single and team challenges.
    """
    if created:
        check_in_date = instance.start_time.date()  # Extract the date from TimeLog
        user = instance.user

        try:
            # Get the user's profile and update streak
            user_profile = user.userprofile
            user_profile.update_streak_and_award_points(check_in_date)

            # Update single challenges (e.g., "Sign in for 5 Days")
            handle_sign_in_challenges(user, user_profile)

            # Update team challenges (e.g., "Team: Sign in for 5 Days")
            if user_profile.team:
                handle_team_sign_in_challenges(user_profile.team)

        except UserProfile.DoesNotExist:
            # Fallback: Create a UserProfile if it doesn't exist
            UserProfile.objects.create(
                user=user,
                current_streak=1,
                longest_streak=1,
                last_check_in=check_in_date,
            )


def handle_sign_in_challenges(user, user_profile):
    """
    Update progress for single challenges based on the user's streak.
    """
    try:
        challenge_title = "Sign in for 5 Days"  # Title of the single challenge
        challenge = Challenge.objects.get(title=challenge_title, challenge_type="single")

        # Use the user's current streak to calculate progress
        streak_count = user_profile.current_streak
        progress = min((streak_count / 5) * 100, 100)  # Max 100%

        # Update the challenge progress
        challenge.progress = int(progress)
        challenge.save()

        # Award points if the challenge is completed
        if progress == 100 and not challenge.is_completed():
            challenge.completed = True
            challenge.completed_at = timezone.now()
            challenge.save()

            Points.objects.create(
                user=user,
                score=challenge.points,
                reason=f"Completed '{challenge_title}' challenge",
            )
    except Challenge.DoesNotExist:
        # Challenge doesn't exist; handle accordingly (optional logging)
        pass


def handle_team_sign_in_challenges(team):
    """
    Update progress for team challenges where all members must sign in for 5 days consecutively.
    """
    try:
        challenge_title = "All Members Sign in for 5 Days"  # Title of the team challenge
        challenge = Challenge.objects.get(title=challenge_title, challenge_type="team")
        print("Handling team sign-in challenge...")

        # Ensure the team is registered as a participant
        if team not in challenge.team_participants.all():
            challenge.team_participants.add(team)

        # Get streaks for all team members
        streaks = [member.current_streak for member in team.user_profiles.all()]

        # Determine the minimum streak among team members
        if streaks:  # If the team has members
            min_streak = min(streaks)
            progress = min((min_streak / 5) * 100, 100)  # Progress is based on the lowest streak
        else:
            # If the team has no members, progress is 0
            min_streak = 0
            progress = 0

        # Update the challenge progress
        challenge.progress = int(progress)
        challenge.save()

        # Award points if the challenge is completed
        if progress == 100 and not challenge.is_completed():
            challenge.completed = True
            challenge.completed_at = timezone.now()
            challenge.save()

            # Add points to the team
            team.team_points += challenge.points
            team.save()
    except Challenge.DoesNotExist:
        # Challenge doesn't exist; handle accordingly (optional logging)
        print(f"Challenge '{challenge_title}' does not exist.")
        pass
