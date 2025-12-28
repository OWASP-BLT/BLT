import logging
from datetime import timedelta
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import (
    Activity,
    BaconEarning,
    Badge,
    Bid,
    Count,
    Contribution,
    ForumPost,
    Hunt,
    IpReport,
    Issue,
    Organization,
    Post,
    TimeLog,
    TeamBadge,
    UserBadge,
    UserProfile,
)
from django.utils import timezone
from .utils import analyze_contribution

logger = logging.getLogger(__name__)

# Default BACON rewards for different contribution types
DEFAULT_BACON_REWARDS = {
    "Issue": 5,
    "Post": 10,
    "Hunt": 15,
    "IpReport": 3,
    "Organization": 10,
    "ForumPost": 2,
    "Bid": 2,
}


def get_default_bacon_reward(instance, action_type):
    """Get the default BACON reward for a given instance type"""
    model_name = instance._meta.model_name.capitalize()
    base_reward = DEFAULT_BACON_REWARDS.get(model_name, 1)

    # Add bonus for security-related content if applicable
    if hasattr(instance, "is_security") and getattr(instance, "is_security", False):
        base_reward += 3

    return base_reward


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


def create_activity(instance, action_type):
    """Generic function to create an activity for a given model instance."""
    model_name = instance._meta.model_name
    user_field = (
        getattr(instance, "user", None) or getattr(instance, "author", None) or getattr(instance, "modified_by", None)
    )
    user = user_field or get_default_user()

    # Get the content type of the instance
    content_type = ContentType.objects.get_for_model(instance)

    # Get instance name or title
    name = getattr(instance, "name", getattr(instance, "title", ""))[:50]
    title = f"{model_name.capitalize()} {action_type.capitalize()} {name}"
    description = getattr(instance, "description", None)
    # Create the activity
    Activity.objects.create(
        user=user,
        action_type=action_type,
        title=title,
        content_type=content_type,
        object_id=instance.id,  # Use object_id for GenericForeignKey
        description=description[:100] if description else "",
        image=getattr(instance, "screenshot", getattr(instance, "image", None)),
    )


def giveBacon(user, instance=None, action_type=None, amt=None):
    """
    Award BACON tokens to a user based on their contribution.

    Args:
        user: User object to award tokens to
        instance: Optional model instance for AI analysis
        action_type: Optional action type for AI analysis
        amt: Optional fixed amount to award (bypasses AI analysis)

    Returns:
        int: Amount of BACON tokens awarded

    Security:
        - Validates user exists and has ID
        - Ensures reward amount is within valid range (1-50)
        - Handles errors gracefully
    """
    if user is None:
        return

    # Security: Validate user has been saved to database
    if not user.id:
        logger.warning("giveBacon: User has no ID yet, skipping reward")
        return

    token_earning, created = BaconEarning.objects.get_or_create(user=user)

    try:
        # If amount is specified, use it
        if amt is not None:
            reward_amount = amt
        # Otherwise analyze the contribution if we have an instance
        elif instance is not None and action_type is not None:
            try:
                reward_amount = analyze_contribution(instance, action_type)
            except Exception as e:
                # Fallback to default reward system
                reward_amount = get_default_bacon_reward(instance, action_type)
        else:
            reward_amount = 1  # Default minimum reward

        # Ensure reward amount is within valid range (1-50)
        reward_amount = max(1, min(50, int(reward_amount)))

        if created:
            token_earning.tokens_earned = reward_amount
        else:
            token_earning.tokens_earned += reward_amount

        token_earning.save()
        return reward_amount

    except Exception as e:
        # If anything fails, ensure at least minimum reward is given
        if created:
            token_earning.tokens_earned = 1
        else:
            token_earning.tokens_earned += 1
        token_earning.save()
        return 1


def _safe_assign_badge(user, badge_name):
    """Safely assign a badge to a user, logging any errors."""
    try:
        assign_first_action_badge(user, badge_name)
    except Exception as e:
        logger.warning(f"Failed to assign badge '{badge_name}' to user: {str(e)}", exc_info=True)


def _safe_create_activity(instance, action_type):
    """Safely create an activity, logging any errors."""
    try:
        create_activity(instance, action_type)
    except Exception as e:
        logger.warning(
            f"Failed to create activity for {instance._meta.model_name}: {str(e)}",
            exc_info=True,
        )


def _safe_give_bacon(user, instance=None, action_type=None):
    """Safely award Bacon, logging any errors."""
    try:
        giveBacon(user, instance=instance, action_type=action_type)
    except Exception as e:
        logger.warning(f"Failed to give Bacon to user: {str(e)}", exc_info=True)


@receiver(post_save)
def handle_post_save(sender, instance, created, **kwargs):
    """Generic handler for post_save signal."""
    try:
        if sender == IpReport and created:  # Track first IP report
            _safe_assign_badge(instance.user, "First IP Reported")
            _safe_give_bacon(instance.user, instance=instance, action_type="created")
            _safe_create_activity(instance, "created")

        elif sender == Post and created:  # Track first blog post
            _safe_assign_badge(instance.author, "First Blog Posted")
            _safe_create_activity(instance, "created")
            _safe_give_bacon(instance.author, instance=instance, action_type="created")

        elif sender == Issue and created:  # Track first bug report
            _safe_assign_badge(instance.user, "First Bug Reported")
            _safe_create_activity(instance, "created")
            _safe_give_bacon(instance.user, instance=instance, action_type="created")

        elif sender == Hunt and created:  # Track first bug bounty
            # Attempt to get the user from Domain managers or Organization
            user = None
            if instance.domain:
                # Try managers of the domain
                user = instance.domain.managers.first()
                # Optionally, if Organization has a user, fetch it here
                if not user and instance.domain.organization:
                    user = getattr(instance.domain.organization, "user", None)

            # Assign badge and activity if a user is found
            if user:
                _safe_assign_badge(user, "First Bug Bounty")
                _safe_create_activity(instance, "created")
                _safe_give_bacon(user, instance=instance, action_type="created")

        elif sender == ForumPost and created:  # Track first forum post
            _safe_assign_badge(instance.user, "First Forum Post")
            _safe_create_activity(instance, "created")
            _safe_give_bacon(instance.user, instance=instance, action_type="created")

        elif sender == Bid and created:  # Track first bid placed
            _safe_assign_badge(instance.user, "First Bid Placed")
            _safe_create_activity(instance, "placed")
            _safe_give_bacon(instance.user, instance=instance, action_type="placed")

        elif sender is User and created:  # Handle user sign-up
            try:
                Activity.objects.create(
                    user=instance,
                    action_type="signup",
                    title=f"New User Signup: {instance.username}",
                    content_type=ContentType.objects.get_for_model(instance),
                    object_id=instance.id,
                    description=f"Welcome to the community {instance.username}!",
                )
            except Exception as e:
                logger.warning(
                    f"Failed to create signup activity for User {instance.username}: {str(e)}",
                    exc_info=True,
                )
    except Exception as e:
        logger.error(f"Unexpected error in handle_post_save signal: {str(e)}", exc_info=True)


@receiver(pre_delete)
def handle_pre_delete(sender, instance, **kwargs):
    """Generic handler for pre_delete signal."""
    if sender in [Issue, Hunt, IpReport, Post]:
        _safe_create_activity(instance, "deleted")


@receiver(post_save, sender=TimeLog)
def update_user_streak(sender, instance, created, **kwargs):
    """
    Update a user's daily streak and award points when a TimeLog is created.
    
    When a new TimeLog is created for an authenticated user, compute the check‑in date from the TimeLog's start_time and call the user's UserProfile.update_streak_and_award_points(check_in_date). If the user has no UserProfile, create one with current_streak and longest_streak set to 1 and last_check_in set to the check‑in date.
    
    Parameters:
        sender: The model class sending the signal (unused).
        instance: The created TimeLog instance.
        created (bool): True if the TimeLog was just created.
    """
    if created and instance.user and instance.user.is_authenticated:
        check_in_date = instance.start_time.date()
        try:
            user_profile = instance.user.userprofile
            user_profile.update_streak_and_award_points(check_in_date)
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(
                user=instance.user, current_streak=1, longest_streak=1, last_check_in=check_in_date
            )

logger = logging.getLogger(__name__)

# TEAM HELPERS
def get_user_team(user: User):
    """
    Return the Organization (team) where the given user is an admin or a manager.
    
    Parameters:
        user (User): The user to look up.
    
    Returns:
        Organization or None: The team where the user is the admin if present; otherwise the team where the user is listed as a manager; returns None if no team is found or if `user` is falsy.
    """
    if not user:
        return None
    # Admin of team
    team = Organization.objects.filter(admin=user).first()
    if team:
        return team
    # Member of team
    return Organization.objects.filter(managers=user).first()


def get_team_members(team: Organization):
    """
    Get the users who are members of the team (its managers plus the admin).
    
    Parameters:
        team (Organization): The team to retrieve members for.
    
    Returns:
        QuerySet[User]: A queryset of User objects representing the team's members; returns an empty queryset if `team` is falsy.
    """
    if not team:
        return User.objects.none()
    members = team.managers.all()
    if team.admin:
        members = members | User.objects.filter(id=team.admin.id)
    return members.distinct()


# METRICS
def get_team_contribution_count(team: Organization):
    """
    Count total Contributions made by members of a team.
    
    Parameters:
        team (Organization): Team (Organization) whose members' contributions will be counted.
    
    Returns:
        int: Number of Contribution records authored by the team's members.
    """
    members = get_team_members(team)
    return Contribution.objects.filter(user__in=members).count()


def get_team_closed_issue_count(team: Organization):
    """
    Count closed issues resolved by members of a team.
    
    Parameters:
        team (Organization): The team whose members' closed issues will be counted.
    
    Returns:
        closed_issues_count (int): Number of Issue records with status "closed" where `closed_by` is a member of the team.
    """
    members = get_team_members(team)
    return Issue.objects.filter(
        closed_by__in=members,
        status="closed"
    ).count()


def get_team_total_issue_count(team: Organization):
    """
    Return the total number of Issue records created by members of the given team.
    
    Parameters:
        team (Organization): The team whose members' issues will be counted.
    
    Returns:
        int: Count of Issue objects authored by any member of the team.
    """
    members = get_team_members(team)
    return Issue.objects.filter(user__in=members).count()


def get_team_activity_score(team: Organization):
    """
    Compute a team's activity score as the sum of its contributions and closed issues.
    
    Parameters:
        team (Organization): The team whose activity score will be calculated.
    
    Returns:
        int: Total activity score equal to contributions count plus closed issues count.
    """
    return get_team_contribution_count(team) + get_team_closed_issue_count(team)


def get_first_contributor(team: Organization):
    """
    Return the earliest user who made a Contribution as a member of the given team.
    
    Parameters:
        team (Organization): Team whose members will be considered.
    
    Returns:
        User or None: The user who made the first Contribution by any team member, or `None` if no contributions exist.
    """
    members = get_team_members(team)
    contrib = Contribution.objects.filter(user__in=members).order_by("created").first()
    return contrib.user if contrib else None


def get_top_contributor(team: Organization):
    """
    Return the team member with the highest number of Contributions.
    
    Parameters:
        team (Organization): The team whose members will be evaluated.
    
    Returns:
        User or None: The member with the most Contribution records, or `None` if the team has no members.
    """
    members = get_team_members(team)
    if not members.exists():
        return None
    ranked = sorted(
        members,
        key=lambda u: Contribution.objects.filter(user=u).count(),
        reverse=True
    )
    return ranked[0] if ranked else None


def get_user_team_issue_count(user: User):
    """
    Return the number of issues closed by the given user; returns 0 if the user does not belong to a team.
    
    Parameters:
        user (User): The user whose closed issues will be counted.
    
    Returns:
        int: Count of issues with status "closed" that have `closed_by` set to the given user, or 0 if the user has no team.
    """
    team = get_user_team(user)
    if not team:
        return 0
    return Issue.objects.filter(closed_by=user, status="closed").count()


def get_user_team_contribution_count(user: User):
    """
    Return the number of Contributions made by a user when the user belongs to a team.
    
    Parameters:
        user (User): The user whose contributions to count.
    
    Returns:
        int: The number of Contribution records for the given user if the user belongs to a team, otherwise 0.
    """
    team = get_user_team(user)
    if not team:
        return 0
    return Contribution.objects.filter(user=user).count()



# BADGE HELPERS
def award_team_badge(team, badge, user=None, reason=None):
    """
    Award a TeamBadge linking the given badge to the specified team and optional user if one does not already exist.
    
    Creates a TeamBadge record with the provided reason (or the badge's description when reason is not supplied) and logs the award. No action is taken if `team` or `badge` is falsy or if a matching TeamBadge already exists.
    
    Parameters:
        team (Organization): The team (Organization) that should receive the badge.
        badge (Badge): The badge to award to the team.
        user (User, optional): An optional user associated with the team badge (e.g., the member who earned it).
        reason (str, optional): A human-readable reason for the award; defaults to the badge's description.
    """
    if not team or not badge:
        return
    exists = TeamBadge.objects.filter(team=team, badge=badge, user=user).exists()
    if exists:
        return
    TeamBadge.objects.create(
        team=team,
        badge=badge,
        user=user,
        reason=reason or badge.description
    )
    logger.info(f"Awarded badge '{badge.title}' to team {team} (user={user})")


def revoke_team_badge(team, badge, user=None):
    """
    Revoke a badge assignment from a team, optionally scoped to a specific user.
    
    Deletes any TeamBadge records linking the given team and badge (and user, if provided) and logs the revocation.
    
    Parameters:
        team: The Organization (team) from which the badge should be revoked.
        badge: The Badge to revoke.
        user (optional): If provided, only revoke the badge association for this user within the team.
    """
    TeamBadge.objects.filter(team=team, badge=badge, user=user).delete()
    logger.info(f"Revoked badge '{badge.title}' from team {team} (user={user})")


# EVALUATORS
def evaluate_team_badges(team: Organization):
    """
    Evaluate automatic, team-scoped badges for the given team and award or revoke them according to each badge's criteria.
    
    Parameters:
        team (Organization): The team whose metrics will be evaluated; no action is taken if `team` is falsy.
    """
    if not team:
        return
    badges = Badge.objects.filter(type="automatic", scope="team")
    for badge in badges:
        criteria = badge.criteria or {}
        metric = criteria.get("metric")
        threshold = criteria.get("threshold")
        rank = criteria.get("rank")

        if metric == "team_contributions":
            count = get_team_contribution_count(team)
            if count >= threshold:
                award_team_badge(team, badge, reason=f"Team reached {count} contributions")

        elif metric == "team_issues_closed":
            count = get_team_closed_issue_count(team)
            if count >= threshold:
                award_team_badge(team, badge, reason=f"Team closed {count} issues")

        elif metric == "team_total_issues":
            count = get_team_total_issue_count(team)
            if count >= threshold:
                award_team_badge(team, badge, reason=f"Team has {count} total issues")

        elif metric == "team_top_activity_rank":
            all_teams = Organization.objects.all()
            ranked = sorted(all_teams, key=lambda t: get_team_activity_score(t), reverse=True)
            top_team = ranked[0] if ranked else None
            if top_team == team:
                award_team_badge(team, badge, reason="Top activity team")
            else:
                revoke_team_badge(team, badge)

# USER_TEAM BADGES
def evaluate_user_team_badges(team: Organization):
    """
    Evaluate and assign user-scoped team badges for a given team based on badge criteria.
    
    Processes automatic badges with scope "topuser_team" and applies their criteria:
    - "top_contributor_team_rank": awards the badge to the team's top contributor.
    - "first_contributor_team": awards the badge to the team's first contributor.
    - "user_team_issues": awards the badge to each team member whose closed-issue count meets or exceeds the badge threshold.
    - "user_team_contributions": awards the badge to each team member whose contribution count meets or exceeds the badge threshold.
    
    Parameters:
        team (Organization): The team (Organization) whose members will be evaluated. If falsy, the function returns immediately.
    """
    if not team:
        return
    badges = Badge.objects.filter(type="automatic", scope="topuser_team")
    members = get_team_members(team)
    for badge in badges:
        criteria = badge.criteria or {}
        metric = criteria.get("metric")
        threshold = criteria.get("threshold")
        rank = criteria.get("rank")

        if metric == "top_contributor_team_rank":
            top_user = get_top_contributor(team)
            if top_user:
                award_team_badge(team, badge, user=top_user, reason="Top contributor in team")

        elif metric == "first_contributor_team":
            first_user = get_first_contributor(team)
            if first_user:
                award_team_badge(team, badge, user=first_user, reason="First contributor in team")

        elif metric == "user_team_issues":
            for member in members:
                count = get_user_team_issue_count(member)
                if count >= threshold:
                    award_team_badge(team, badge, user=member,
                                     reason=f"{member.username} closed {count} issues")

        elif metric == "user_team_contributions":
            for member in members:
                count = get_user_team_contribution_count(member)
                if count >= threshold:
                    award_team_badge(team, badge, user=member,
                                     reason=f"{member.username} contributed {count} times")


# SIGNALS
@receiver(post_save, sender=Contribution)
def contribution_created(sender, instance, created, **kwargs):
    """
    Handle Contribution post-save events to evaluate team and user-team badges when a new contribution is created.
    
    Triggered on Contribution post_save; if the contribution is newly created and has an associated user, determines that user's team and runs team-level and user-team badge evaluation routines.
    """
    if not created or not instance.user:
        return
    team = get_user_team(instance.user)
    evaluate_team_badges(team)
    evaluate_user_team_badges(team)


@receiver(post_save, sender=Issue)
def issue_updated(sender, instance, **kwargs):
    """
    Trigger team- and user-team badge evaluations when an Issue is updated.
    
    Parameters:
        sender (type): The model class that sent the signal.
        instance (Issue): The Issue instance that was saved; its owner and closer (if any) are used to locate teams for evaluation.
    
    Description:
        - Evaluates automatic team-level and user-team badge rules for the team of the issue's owner.
        - If the issue's status is "closed" and `instance.closed_by` is set, also evaluates team-level badge rules for the team of the user who closed the issue.
    """
    team = get_user_team(instance.user)
    evaluate_team_badges(team)
    evaluate_user_team_badges(team)

    if instance.status != "closed" or not instance.closed_by:
        return

    team = get_user_team(instance.closed_by)
    evaluate_team_badges(team)