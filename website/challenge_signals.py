from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Challenge, IpReport, Issue, Points, TimeLog, UserProfile


def handle_staking_pool_completion(user, challenge):
    """Handle staking pool completion when a user completes a challenge"""
    from .models import StakingEntry  # Import here to avoid circular imports
    from .views.staking_competitive import calculate_individual_user_progress  # Import progress function

    # Find active staking entries for this user and challenge
    active_entries = StakingEntry.objects.filter(
        user=user, pool__challenge=challenge, pool__status="active", status="active", challenge_completed=False
    )

    # Check each staking entry individually with pool-specific progress
    for entry in active_entries:
        # Calculate progress only from when user joined this specific pool
        pool_progress = calculate_individual_user_progress(user, challenge, pool_entry=entry)

        # If user has completed the challenge for this specific pool, complete the entry
        if pool_progress >= 100:
            entry.complete_challenge()
            print(
                f"Staking pool completion for {user.username} in {entry.pool.name}: Challenge completed with {pool_progress}% progress"
            )


def update_challenge_progress(user, challenge_title, model_class, reason, threshold=None, team_threshold=None):
    if not user.is_authenticated:
        return
    try:
        challenge = Challenge.objects.get(title=challenge_title)

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

            if team_progress == 100 and not challenge.completed:
                challenge.completed = True  # Explicitly mark the challenge as completed
                challenge.completed_at = timezone.now()  # Track completion time (optional)
                challenge.save()  # Save changes to the challenge

                team.team_points += challenge.points
                team.save()

                # Award BACON tokens to all team members
                from website.feed_signals import giveBacon

                for team_member in team.user_profiles.all():
                    if team_member.user:
                        giveBacon(team_member.user, amt=challenge.bacon_reward)

                # Award BACON tokens to all team members
                from website.feed_signals import giveBacon

                for team_member in team.user_profiles.all():
                    if team_member.user:
                        giveBacon(team_member.user, amt=challenge.bacon_reward)
        else:
            if user not in challenge.participants.all():
                challenge.participants.add(user)

            user_count = model_class.objects.filter(user=user).count()
            progress = min((user_count / threshold) * 100, 100)  # Ensure it doesn't exceed 100%

            challenge.progress = int(progress)
            challenge.save()
            print(challenge.completed)
            if challenge.progress == 100 and not challenge.completed:
                challenge.completed = True  # Explicitly mark the challenge as completed
                challenge.completed_at = timezone.now()
                challenge.save()

                # Award points to the user
                Points.objects.create(user=user, score=challenge.points, reason=reason)

                # Award BACON tokens for completing the challenge
                from website.feed_signals import giveBacon

                giveBacon(user, amt=challenge.bacon_reward)

                # Handle staking pool completion
                handle_staking_pool_completion(user, challenge)

    except Challenge.DoesNotExist:
        pass


@receiver(post_save)
def handle_post_save(sender, instance, created, **kwargs):
    """Generic handler for post_save signal."""
    if sender == IpReport and created:  # Track first IP report
        if instance.user and instance.user.is_authenticated:
            update_challenge_progress(
                user=instance.user,
                challenge_title="Report 5 IPs",
                model_class=IpReport,
                reason="Completed 'Report 5 IPs' challenge",
                threshold=5,
            )
            if instance.user.is_authenticated and instance.user.userprofile.team:
                update_challenge_progress(
                    user=instance.user,
                    challenge_title="Report 10 IPs",
                    model_class=IpReport,
                    reason="Completed 'Report 10 IPs challenge",
                    team_threshold=10,  # For team challenge
                )

    elif sender == Issue and created:  # Track first bug report
        if instance.user and instance.user.is_authenticated:
            update_challenge_progress(
                user=instance.user,
                challenge_title="Report 5 Issues",
                model_class=Issue,
                reason="Completed 'Report 5 Issues challenge",
                threshold=5,
            )
            if instance.user.is_authenticated and instance.user.userprofile.team:
                update_challenge_progress(
                    user=instance.user,
                    challenge_title="Report 10 Issues",
                    model_class=Issue,
                    reason="Completed 'Report 10 Issues challenge",
                    team_threshold=10,  # For team challenge
                )


@receiver(post_save, sender=TimeLog)
def update_user_streak(sender, instance, created, **kwargs):
    if created and instance.user and instance.user.is_authenticated:
        check_in_date = instance.start_time.date()  # Extract the date from TimeLog
        user = instance.user

        try:
            user_profile = user.userprofile
            user_profile.update_streak_and_award_points(check_in_date)

            handle_sign_in_challenges(user, user_profile)

            if user_profile.team:
                handle_team_sign_in_challenges(user_profile.team)

        except UserProfile.DoesNotExist:
            pass


def handle_sign_in_challenges(user, user_profile):
    """
    Update progress for single challenges based on the user's streak.
    """
    try:
        print("Handling user sign-in challenge...")
        challenge_title = "Sign in for 5 Days"
        challenge = Challenge.objects.get(title=challenge_title, challenge_type="single")

        if user not in challenge.participants.all():
            challenge.participants.add(user)

        streak_count = user_profile.current_streak
        print(streak_count)

        if streak_count >= 5:
            progress = 100
        else:
            progress = streak_count * 100 / 5  # Calculate progress if streak is less than 5
        print(progress)
        # Update the challenge progress
        challenge.progress = int(progress)
        challenge.save()

        # Award points if the challenge is completed (when streak is 5)
        if progress == 100 and not challenge.completed:
            challenge.completed = True
            challenge.completed_at = timezone.now()
            challenge.save()

            Points.objects.create(
                user=user,
                score=challenge.points,
                reason=f"Completed '{challenge_title}' challenge",
            )

            # Award BACON tokens for completing the challenge
            from website.feed_signals import giveBacon

            giveBacon(user, amt=challenge.bacon_reward)

            # Handle staking pool completion
            handle_staking_pool_completion(user, challenge)

    except Challenge.DoesNotExist:
        # Handle case when the challenge does not exist
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

        if streaks:  # If the team has members
            min_streak = min(streaks)
            progress = min((min_streak / 5) * 100, 100)
        else:
            min_streak = 0
            progress = 0

        challenge.progress = int(progress)
        challenge.save()

        if progress == 100 and not challenge.completed:
            challenge.completed = True
            challenge.completed_at = timezone.now()
            challenge.save()

            # Add points to the team
            team.team_points += challenge.points
            team.save()

            # Award BACON tokens to all team members
            from website.feed_signals import giveBacon

            for team_member in team.user_profiles.all():
                if team_member.user:
                    giveBacon(team_member.user, amt=challenge.bacon_reward)
    except Challenge.DoesNotExist:
        print(f"Challenge '{challenge_title}' does not exist.")
        pass
