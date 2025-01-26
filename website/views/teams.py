import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render

# Create your views here.
from django.views.generic import TemplateView

from website.models import Challenge, JoinRequest, Organization


class TeamOverview(TemplateView):
    template_name = "team_overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            user_profile = self.request.user.userprofile
            if user_profile.team:
                team_members = user_profile.team.managers.all()
                context["team_members"] = team_members
        return context


@login_required
def search_users(request):
    query = request.GET.get("query", "")
    if query:
        users = User.objects.filter(username__icontains=query).values("username", "userprofile__team__name")
        users_list = [{"username": user["username"], "team": user["userprofile__team__name"]} for user in users]
        return JsonResponse(users_list, safe=False)
    return JsonResponse([], safe=False)


from django.db import IntegrityError
from django.http import JsonResponse


@login_required
def create_team(request):
    if request.method == "POST":
        team_name = request.POST.get("teamName")
        team_avatar = request.FILES.get("teamAvatar")
        selected_users = request.POST.get("selectedMembers")  # Get the selected users
        team_members = selected_users.split(",") if selected_users else []

        try:
            # Generate a unique URL for the team
            team_url = team_name.lower().replace(" ", "-")  # Simple slugify logic
            counter = 1
            while Organization.objects.filter(url=team_url).exists():
                team_url = f"{team_url}-{counter}"
                counter += 1

            # Create the team
            team = Organization.objects.create(name=team_name, type="team", admin=request.user, url=team_url)
            if team_avatar:
                team.logo = team_avatar
                team.save()  # Save the logo if provided

            # Update user's profile
            user_profile = request.user.userprofile
            user_profile.team = team
            user_profile.save()

            # Send join requests to selected members
            for username in team_members:
                username = username.strip()
                if username:  # Check if username is not empty
                    result = send_join_request(team, request.user, username)
                    if not result["success"]:
                        messages.error(request, f"Error inviting {username}: {result['error']}")

            messages.success(request, "Team created successfully and join requests sent.")
            return redirect("team_overview")

        except IntegrityError:
            messages.error(request, "A team with this name or URL already exists. Please choose another name.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

    return render(request, "create_team.html")


@login_required
def join_requests(request):
    join_requests = JoinRequest.objects.filter(user=request.user)
    if request.method == "POST":
        team_id = request.POST.get("team_id")
        team = Organization.objects.get(id=team_id, type="team")
        if request.user.is_authenticated:
            user_profile = request.user.userprofile
            user_profile.team = team
            user_profile.save()
            team.managers.add(request.user)
            JoinRequest.objects.filter(user=request.user, team=team).delete()
        return redirect("team_overview")

    return render(request, "join_requests.html", {"join_requests": join_requests})


@login_required
def add_member(request):
    if request.method == "POST":
        username = request.POST.get("newMember")
        team = request.user.userprofile.team  # Assume userprofile.team gives the team object

        # Use helper function
        result = send_join_request(team, request.user, username)

        # Return the result as JSON response
        return JsonResponse(result)

    return JsonResponse({"success": False, "error": "Invalid request method"})


def send_join_request(team, requesting_user, target_username):
    if target_username == requesting_user.username:
        return {"success": False, "error": "You cannot invite yourself to your own team"}

    try:
        user = User.objects.get(username=target_username)

        if team.managers.filter(username=target_username).exists():
            return {"success": False, "error": "User is already a member of the team"}

        if JoinRequest.objects.filter(team=team, user=user).exists():
            return {"success": False, "error": "A join request is already pending for this user"}

        # Create the join request
        JoinRequest.objects.create(team=team, user=user)
        return {"success": True}

    except User.DoesNotExist:
        return {"success": False, "error": "User does not exist"}


@login_required
def delete_team(request):
    if request.user.is_authenticated:
        user_profile = request.user.userprofile
        if user_profile.team and user_profile.team.admin == request.user:
            team = user_profile.team
            team.managers.clear()
            team.delete()
            user_profile.team = None
            user_profile.save()
    return redirect("team_overview")


@login_required
def leave_team(request):
    if request.user.is_authenticated:
        user_profile = request.user.userprofile
        if user_profile.team:
            team = user_profile.team
            if team.admin == request.user:
                managers = team.managers.all()
                if managers.exists():
                    new_admin = managers.first()
                    team.managers.remove(new_admin)
                    team.admin = new_admin
                    team.save()
                else:
                    team.delete()
            else:
                team.managers.remove(request.user)
            user_profile.team = None
            user_profile.save()
    return redirect("team_overview")


@login_required
def kick_member(request):
    if request.method == "POST":
        try:
            # Parse JSON data from request body
            data = json.loads(request.body)
            username = data.get("member")  # Extract 'member' from the JSON payload

            user = User.objects.get(username=username)
            team = request.user.userprofile.team

            # Check if the requester is the team admin
            if team.admin != request.user:
                return JsonResponse({"success": False, "error": "Only the team admin can kick members"})

            # Check if the user is a manager in the team
            if not team.managers.filter(username=username).exists():
                return JsonResponse({"success": False, "error": "User is not a member of the team"})

            # Remove the user from the managers
            team.managers.remove(user)

            # Remove the team from the user's profile
            user_profile = user.userprofile
            user_profile.team = None
            user_profile.save()

            return JsonResponse({"success": True, "message": f"User {username} has been kicked out of the team."})

        except User.DoesNotExist:
            return JsonResponse({"success": False, "error": "User does not exist"})
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON data"})
    return JsonResponse({"success": False, "error": "Invalid request method"})


class TeamChallenges(TemplateView):
    """View for displaying all team challenges and their progress."""

    def get(self, request):
        # Get all team challenges
        team_challenges = Challenge.objects.filter(challenge_type="team")
        if request.user.is_authenticated:
            user_profile = request.user.userprofile  # Get the user's profile

            # Check if the user belongs to a team
            if user_profile.team:
                user_team = user_profile.team  # Get the user's team

                for challenge in team_challenges:
                    # Check if the team is a participant in this challenge
                    if user_team in challenge.team_participants.all():
                        # Progress is already stored in the Challenge model
                        challenge.progress = challenge.progress
                    else:
                        # Team is not a participant, set progress to 0
                        challenge.progress = 0
            else:
                # If the user is not part of a team, set progress to 0 for all challenges
                for challenge in team_challenges:
                    challenge.progress = 0

        # Render the team challenges template
        return render(request, "team_challenges.html", {"team_challenges": team_challenges})


class TeamLeaderboard(TemplateView):
    """View to display the team leaderboard based on total points."""

    def get(self, request):
        teams = Organization.objects.all()
        leaderboard = []
        for team in teams:
            team_points = team.team_points
            leaderboard.append((team, team_points))

        # Sort by points in descending order
        leaderboard.sort(key=lambda x: x[1], reverse=True)

        return render(request, "team_leaderboard.html", {"leaderboard": leaderboard})
