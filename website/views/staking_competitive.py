from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Case, Count, F, IntegerField, Q, Sum, When
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from ..models import BaconEarning, Challenge, IpReport, Issue, StakingEntry, StakingPool, StakingTransaction, TimeLog


def calculate_individual_user_progress(user, challenge, pool_entry=None):
    """Calculate individual user progress for a challenge

    Args:
        user: User object
        challenge: Challenge object
        pool_entry: StakingEntry object (optional) - if provided, only count contributions after pool join
    """
    # Default threshold mapping - in a real implementation, this should be stored in the challenge model
    challenge_thresholds = {"find_bugs": 10, "report_bugs": 5, "log_time": 20, "default": 10}

    # Determine when to start counting from (reset point)
    count_from_date = pool_entry.created_at if pool_entry else None

    # Map challenge types to their respective models and count logic
    challenge_mapping = {
        "find_bugs": (
            Issue,
            lambda u, from_date: Issue.objects.filter(
                user=u, created__gte=from_date if from_date else timezone.now() - timedelta(days=365 * 10)
            ).count(),
        ),
        "report_bugs": (
            IpReport,
            lambda u, from_date: IpReport.objects.filter(
                user=u, created__gte=from_date if from_date else timezone.now() - timedelta(days=365 * 10)
            ).count(),
        ),
        "log_time": (
            TimeLog,
            lambda u, from_date: TimeLog.objects.filter(
                user=u, created__gte=from_date if from_date else timezone.now() - timedelta(days=365 * 10)
            ).count(),
        ),
    }

    # Determine challenge type and threshold from title
    threshold = challenge_thresholds["default"]
    user_count = 0

    for challenge_type, (model_class, count_func) in challenge_mapping.items():
        if challenge_type.lower() in challenge.title.lower():
            user_count = count_func(user, count_from_date)
            threshold = challenge_thresholds.get(challenge_type, challenge_thresholds["default"])
            break
    else:
        # Default to Issue count if no specific type found
        if count_from_date:
            user_count = Issue.objects.filter(user=user, created__gte=count_from_date).count()
        else:
            user_count = Issue.objects.filter(user=user).count()

    # Calculate progress as percentage
    progress = min((user_count / threshold) * 100, 100) if threshold > 0 else 0
    return int(progress)


@login_required
def staking_home(request):
    """Display competitive staking home page with available pools"""
    # Get pools by status
    open_pools = StakingPool.objects.filter(status="open").order_by("-created_at")
    full_pools = StakingPool.objects.filter(status="full").order_by("-created_at")
    active_pools = StakingPool.objects.filter(status="active").order_by("-created_at")
    completed_pools = StakingPool.objects.filter(status="completed").order_by("-completed_at")[:5]

    # Get user's BACON balance
    user_bacon_balance = 0
    try:
        bacon_earning = BaconEarning.objects.get(user=request.user)
        user_bacon_balance = bacon_earning.tokens_earned
    except BaconEarning.DoesNotExist:
        pass

    # Add join status to each pool
    all_pools = list(open_pools) + list(full_pools) + list(active_pools) + list(completed_pools)
    for pool in all_pools:
        # Check if user has already joined this pool
        user_entry = pool.entries.filter(user=request.user).first()
        pool.user_has_joined = bool(user_entry)
        pool.user_entry = user_entry

        # Check if user can join
        if not pool.user_has_joined:
            can_join, join_message = pool.can_user_join(request.user)
            pool.user_can_join = can_join
            pool.join_message = join_message
        else:
            pool.user_can_join = False
            pool.join_message = "Already joined"

    # Get user's current stakes and statss
    user_active_stakes = StakingEntry.objects.filter(user=request.user, status="active").count()
    user_total_staked = (
        StakingEntry.objects.filter(user=request.user, status="active").aggregate(total=Sum("staked_amount"))["total"]
        or 0
    )

    user_wins = StakingEntry.objects.filter(user=request.user, status="won").count()
    user_losses = StakingEntry.objects.filter(user=request.user, status="lost").count()
    user_total_winnings = (
        StakingEntry.objects.filter(user=request.user, status="won").aggregate(total=Sum("actual_reward"))["total"] or 0
    )

    context = {
        "open_pools": open_pools,
        "full_pools": full_pools,
        "active_pools": active_pools,
        "completed_pools": completed_pools,
        "user_bacon_balance": user_bacon_balance,
        "user_active_stakes": user_active_stakes,
        "user_total_staked": user_total_staked,
        "user_wins": user_wins,
        "user_losses": user_losses,
        "user_total_winnings": user_total_winnings,
    }

    return render(request, "staking/staking_home.html", context)


@login_required
def pool_detail(request, pool_id):
    """Display detailed view of a specific staking pool"""
    pool = get_object_or_404(StakingPool, id=pool_id)

    # Get all participants
    participants = StakingEntry.objects.filter(pool=pool).select_related("user")
    participants_count = participants.count()

    # Add challenge progress information for each participant
    if pool.challenge:
        for participant in participants:
            # Check if user is participating in the challenge
            if participant.user in pool.challenge.participants.all():
                # Calculate individual user progress for staking pools - pass pool entry to reset progress
                participant.challenge_progress = calculate_individual_user_progress(
                    participant.user,
                    pool.challenge,
                    pool_entry=participant,  # This resets progress to only count contributions after joining this pool
                )
            else:
                participant.challenge_progress = 0

            # Calculate progress circle styling (same as user_challenges)
            circumference = 125.6
            participant.stroke_dasharray = circumference
            participant.stroke_dashoffset = circumference - (circumference * participant.challenge_progress / 100)

            # Add completion status
            participant.challenge_completed_status = participant.challenge_progress >= 100
    else:
        # If no challenge associated, set default values
        for participant in participants:
            participant.challenge_progress = 0
            participant.stroke_dasharray = 125.6
            participant.stroke_dashoffset = 125.6
            participant.challenge_completed_status = False

    # Check if user has joined this pool
    user_entry = None
    if request.user.is_authenticated:
        try:
            user_entry = StakingEntry.objects.get(pool=pool, user=request.user)
        except StakingEntry.DoesNotExist:
            pass

    # Get user's BACON balance
    user_bacon_balance = 0
    if request.user.is_authenticated:
        try:
            bacon_earning = BaconEarning.objects.get(user=request.user)
            user_bacon_balance = bacon_earning.tokens_earned
        except BaconEarning.DoesNotExist:
            pass

    # Check if user can join
    can_join = False
    join_message = "Please log in to join"
    if request.user.is_authenticated:
        if user_entry:
            can_join = False
            join_message = "Already joined"
        else:
            can_join, join_message = pool.can_user_join(request.user)

    # Calculate statistics
    total_staked = sum(entry.staked_amount for entry in participants)
    completed_challenges = participants.filter(challenge_completed=True).count()

    # Get top stakers (for competitive pools, all stakes are the same, so just show participants)
    top_stakers = participants.order_by("-created_at")[:5]

    context = {
        "pool": pool,
        "participants": participants,
        "participants_count": participants_count,
        "user_entry": user_entry,
        "user_bacon_balance": user_bacon_balance,
        "can_join": can_join,
        "join_message": join_message,
        "total_staked": total_staked,
        "completed_challenges": completed_challenges,
        "top_stakers": top_stakers,
    }

    return render(request, "staking/pool_detail.html", context)


@login_required
@require_http_methods(["POST"])
def stake_in_pool(request, pool_id):
    """Join a competitive staking pool"""
    pool = get_object_or_404(StakingPool, id=pool_id)

    try:
        with transaction.atomic():
            success, message = pool.join_pool(request.user)

            if success:
                messages.success(request, message)

                # If pool is now full, redirect to show it's ready to start
                if pool.is_full:
                    messages.info(request, "Pool is now full! Challenge will begin soon.")

            else:
                messages.error(request, message)

    except Exception as e:
        messages.error(request, "An error occurred while joining the pool. Please try again.")

    return redirect("pool_detail", pool_id=pool_id)


@login_required
def complete_staking_challenge(request, challenge_id):
    """Mark a challenge as completed for staking pools"""
    if request.method != "POST":
        messages.error(request, "Invalid request method")
        return redirect("staking_home")

    # Get the challenge
    challenge = get_object_or_404(Challenge, id=challenge_id)

    # Find active staking entries for this user and challenge
    active_entries = StakingEntry.objects.filter(
        user=request.user, pool__challenge=challenge, pool__status="active", status="active", challenge_completed=False
    )

    if not active_entries.exists():
        messages.error(request, "No active staking entries found for this challenge.")
        return redirect("staking_home")

    results = []

    try:
        with transaction.atomic():
            for entry in active_entries:
                success, message = entry.complete_challenge()
                results.append({"pool": entry.pool.name, "success": success, "message": message})

                if success and entry.status == "won":
                    messages.success(
                        request,
                        f"🎉 Congratulations! You won {entry.pool.name} and earned {entry.actual_reward} BACON!",
                    )
                elif success:
                    messages.info(
                        request, f"Challenge completed for {entry.pool.name}, but someone else finished first."
                    )

    except Exception as e:
        messages.error(request, "An error occurred while completing the challenge.")

    return redirect("my_staking")


@login_required
def my_staking(request):
    """Display user's staking entries and history"""
    # Get user's active entries
    active_entries = (
        StakingEntry.objects.filter(user=request.user, status="active")
        .select_related("pool", "pool__challenge")
        .order_by("-created_at")
    )

    # Get user's completed entries
    completed_entries = (
        StakingEntry.objects.filter(user=request.user, status__in=["won", "lost"])
        .select_related("pool", "pool__challenge")
        .order_by("-created_at")
    )

    # Get user's transaction history
    transactions = (
        StakingTransaction.objects.filter(user=request.user).select_related("pool").order_by("-created_at")[:20]
    )

    # Calculate stats
    total_staked = active_entries.aggregate(total=Sum("staked_amount"))["total"] or 0
    total_wins = completed_entries.filter(status="won").count()
    total_losses = completed_entries.filter(status="lost").count()
    total_winnings = completed_entries.filter(status="won").aggregate(total=Sum("actual_reward"))["total"] or 0

    # Get user's BACON balance
    user_bacon_balance = 0
    try:
        bacon_earning = BaconEarning.objects.get(user=request.user)
        user_bacon_balance = bacon_earning.tokens_earned
    except BaconEarning.DoesNotExist:
        pass

    context = {
        "active_entries": active_entries,
        "completed_entries": completed_entries,
        "transactions": transactions,
        "total_staked": total_staked,
        "total_wins": total_wins,
        "total_losses": total_losses,
        "total_winnings": total_winnings,
        "user_bacon_balance": user_bacon_balance,
    }

    return render(request, "staking/my_staking.html", context)


@login_required
def staking_leaderboard(request):
    """Display global staking leaderboard with top performers"""
    from django.contrib.auth.models import User

    # Get top winners by total winnings
    top_winners = (
        User.objects.annotate(
            total_winnings=Sum("staking_entries__actual_reward"),
            total_wins=Count("staking_entries", filter=Q(staking_entries__status="won")),
            total_competitions=Count("staking_entries"),
            win_rate=Case(
                When(staking_entries__isnull=False, then=F("total_wins") * 100.0 / F("total_competitions")),
                default=0,
                output_field=IntegerField(),
            ),
        )
        .filter(total_winnings__gt=0)
        .order_by("-total_winnings")[:20]
    )

    # Get most active players
    most_active = (
        User.objects.annotate(
            total_competitions=Count("staking_entries"),
            total_staked=Sum("staking_entries__staked_amount"),
            total_wins=Count("staking_entries", filter=Q(staking_entries__status="won")),
        )
        .filter(total_competitions__gt=0)
        .order_by("-total_competitions")[:20]
    )

    # Get recent winners
    recent_winners = (
        StakingEntry.objects.filter(status="won").select_related("user", "pool").order_by("-completion_time")[:10]
    )

    # Get statistics for the stats cards
    total_pools_active = StakingPool.objects.filter(status="active").count()
    total_participants = StakingEntry.objects.values("user").distinct().count()
    total_prize_pool = (
        StakingPool.objects.filter(status__in=["open", "full", "active"]).aggregate(
            total=Sum("stake_amount") * 2  # Assuming head-to-head pools
        )["total"]
        or 0
    )
    total_distributed = StakingEntry.objects.filter(status="won").aggregate(total=Sum("actual_reward"))["total"] or 0

    context = {
        "top_winners": top_winners,
        "most_active": most_active,
        "recent_winners": recent_winners,
        "leaderboard_users": top_winners,  # Use top_winners for the main leaderboard table
        "top_users": top_winners[:3],  # Top 3 for the podium display
        "total_pools_active": total_pools_active,
        "total_participants": total_participants,
        "total_prize_pool": total_prize_pool,
        "total_distributed": total_distributed,
        "is_pool_specific": False,
    }

    return render(request, "staking/leaderboard.html", context)


@login_required
def create_staking_pool(request):
    """Allow users to create their own competitive staking pools"""
    if request.method == "POST":
        try:
            name = request.POST.get("name")
            description = request.POST.get("description")
            pool_type = request.POST.get("pool_type", "head_to_head")
            challenge_id = request.POST.get("challenge_id")
            stake_amount = Decimal(request.POST.get("stake_amount", "0"))
            days_duration = int(request.POST.get("days_duration", "7"))

            # Validate inputs
            if not all([name, description, challenge_id]) or stake_amount <= 0:
                messages.error(request, "Please fill in all required fields with valid values.")
                return redirect("create_staking_pool")

            challenge = get_object_or_404(Challenge, id=challenge_id, challenge_type="single")

            # Check if user has enough BACON to stake
            try:
                bacon_earning = BaconEarning.objects.get(user=request.user)
                if bacon_earning.tokens_earned < stake_amount:
                    messages.error(request, f"You need at least {stake_amount} BACON to create this pool.")
                    return redirect("create_staking_pool")
            except BaconEarning.DoesNotExist:
                messages.error(request, "You don't have any BACON tokens.")
                return redirect("create_staking_pool")

            # Create the pool
            with transaction.atomic():
                pool = StakingPool.objects.create(
                    name=name,
                    description=description,
                    pool_type=pool_type,
                    challenge=challenge,
                    stake_amount=stake_amount,
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=days_duration),
                    created_by=request.user,
                )

                # Creator automatically joins their own pool
                pool.join_pool(request.user)

                messages.success(
                    request,
                    f"Pool '{name}' created successfully! You've automatically joined with {stake_amount} BACON.",
                )
                return redirect("pool_detail", pool_id=pool.id)

        except ValueError:
            messages.error(request, "Invalid number format in stake amount or duration.")
        except Exception as e:
            messages.error(request, "An error occurred while creating the pool.")

    # GET request - show form
    challenges = Challenge.objects.filter(challenge_type="single").order_by("title")

    # Get user's BACON balance
    user_bacon_balance = 0
    try:
        bacon_earning = BaconEarning.objects.get(user=request.user)
        user_bacon_balance = bacon_earning.tokens_earned
    except BaconEarning.DoesNotExist:
        pass

    context = {
        "challenges": challenges,
        "user_bacon_balance": user_bacon_balance,
    }

    return render(request, "staking/create_pool.html", context)
