from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from website.models import UserProfile
from .models import Team, JoinRequest, Challenge

# Create your views here.
from django.views.generic import TemplateView

class TeamOverview(TemplateView):
    template_name = "team_overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            user_profile = self.request.user.userprofile
            if user_profile.team:
                team_members = user_profile.team.members.all()
                print("Team Members:", team_members)  # Print team members in the backend
                context['team_members'] = team_members
        return context

@login_required
def search_users(request):
    query = request.GET.get("query", "")
    if query:
        users = User.objects.filter(username__icontains=query).values("username")
        return JsonResponse(list(users), safe=False)
    return JsonResponse([], safe=False)

@login_required
def create_team(request):
    if request.method == "POST":
        team_name = request.POST.get("teamName")
        team_avatar = request.FILES.get("teamAvatar")
        team_members = request.POST.get("teamMembers").split(',')

        # Create the team
        team = Team.objects.create(name=team_name)
        if team_avatar:
            team.avatar = team_avatar
            team.save()

        # Assign the creator as the team leader and add them as a member
        team.leader = request.user
        team.members.add(request.user)
        team.save()

        # Associate the team with the user's profile
        user_profile = request.user.userprofile
        user_profile.team = team
        user_profile.save()

        # Send join requests to other members
        for username in team_members:
            if username.strip() != request.user.username:
                try:
                    user = User.objects.get(username=username.strip())
                    JoinRequest.objects.create(team=team, user=user)
                except User.DoesNotExist:
                    continue

        return redirect('team_overview')

    return render(request, 'create_team.html')

@login_required
def join_requests(request):
    join_requests = JoinRequest.objects.filter(user=request.user)
    if request.method == "POST":
        team_id = request.POST.get("team_id")
        team = Team.objects.get(id=team_id)
        user_profile = request.user.userprofile
        user_profile.team = team
        user_profile.save()
        JoinRequest.objects.filter(user=request.user, team=team).delete()
        return redirect('team_overview')

    return render(request, 'join_requests.html', {'join_requests': join_requests})

@login_required
def add_member(request):
    if request.method == "POST":
        username = request.POST.get("newMember")
        if username == request.user.username:
            return JsonResponse({"success": False, "error": "You cannot invite yourself to your own team"})
        try:
            user = User.objects.get(username=username)
            team = request.user.userprofile.team
            if team.members.filter(username=username).exists():
                return JsonResponse({"success": False, "error": "User is already a member of the team"})
            if JoinRequest.objects.filter(team=team, user=user).exists():
                return JsonResponse({"success": False, "error": "A join request is already pending for this user"})
            JoinRequest.objects.create(team=team, user=user)
            return JsonResponse({"success": True})
        except User.DoesNotExist:
            return JsonResponse({"success": False, "error": "User does not exist"})
    return JsonResponse({"success": False, "error": "Invalid request method"})

@login_required
def delete_team(request):
    user_profile = request.user.userprofile
    if user_profile.team and user_profile.team.leader == request.user:
        team = user_profile.team
        team.members.clear()
        team.delete()
        user_profile.team = None
        user_profile.save()
    return redirect('team_overview')

@login_required
def leave_team(request):
    user_profile = request.user.userprofile
    if user_profile.team:
        team = user_profile.team
        team.members.remove(request.user)
        user_profile.team = None
        user_profile.save()
        if team.members.count() == 0:
            team.delete()
    return redirect('team_overview')

@login_required
def challenges(request):
    single_user_challenges = Challenge.objects.filter(challenge_type='single')
    team_challenges = Challenge.objects.filter(challenge_type='team')
    context = {
        'single_user_challenges': single_user_challenges,
        'team_challenges': team_challenges,
    }
    return render(request, 'challenges.html', context)

@login_required
def update_progress(request, challenge_id):
    challenge = Challenge.objects.get(id=challenge_id)
    user_profile = request.user.userprofile
    team = user_profile.team

    if challenge.challenge_type == 'single':
        # Update progress for single user challenge
        challenge.participants.add(request.user)
        challenge.save()
    elif challenge.challenge_type == 'team' and team:
        # Update progress for team challenge
        challenge.teams.add(team)
        challenge.save()

    return JsonResponse({'success': True})

@login_required
def leaderboard_global(request):
    leaderboard = User.objects.annotate(total_score=Sum('points__score')).order_by('-total_score')[:10]
    team_leaderboard = User.objects.filter(userprofile__team=request.user.userprofile.team).annotate(total_score=Sum('points__score')).order_by('-total_score')[:10]
    global_team_leaderboard = Team.objects.order_by('-fresh_points')[:10]
    
    context = {
        'leaderboard': leaderboard,
        'team_leaderboard': team_leaderboard,
        'global_team_leaderboard': global_team_leaderboard,
    }
    return render(request, 'leaderboard_global.html', context)
