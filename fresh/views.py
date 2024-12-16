from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from website.models import UserProfile
from .models import Team

# Create your views here.
from django.views.generic import TemplateView

class TeamOverview(TemplateView):
    template_name = "team_overview.html"

@login_required
def search_users(request):
    query = request.GET.get("query", "")
    if query:
        users = UserProfile.objects.filter(user__username__icontains=query).values("user__username")
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

        # Add members to the team
        for username in team_members:
            username = username.strip()
            if username:
                try:
                    user = User.objects.get(username=username)
                    team.members.add(user)
                except User.DoesNotExist:
                    continue

        # Associate the team with the user's profile
        user_profile = request.user.userprofile
        user_profile.team = team
        user_profile.save()

        return redirect('team_overview')

    return render(request, 'create_team.html')

# class ChallengesView(TemplateView):
#     template_name = "gamification/challenges.html"

# class WeeklyActivityView(TemplateView):
#     template_name = "gamification/weekly_activity.html"

# class LeaderboardView(TemplateView):
#     template_name = "gamification/leaderboard.html"
