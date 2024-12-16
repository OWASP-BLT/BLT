from django.db.models.signals import post_save
from django.dispatch import receiver
from website.models import IpReport, Issue, UserProfile, Points
from .models import Challenge, Team

@receiver(post_save, sender=IpReport)
def update_ip_report_challenge_progress(sender, instance, **kwargs):
    user = instance.user
    if user is None:
        return

    team = user.userprofile.team if user.userprofile.team else None

    # Update single user challenge progress
    single_challenge = Challenge.objects.get(title="Report 5 IPs", challenge_type="single")
    user_ip_reports = IpReport.objects.filter(user=user).count()
    single_challenge.progress = min((user_ip_reports / 5) * 100, 100)
    single_challenge.save()

    if single_challenge.progress == 100:
        Points.objects.create(user=user, score=single_challenge.fresh_points, reason="Completed 'Report 5 IPs' challenge")

    # Update team challenge progress
    if team:
        team_challenge = Challenge.objects.get(title="Report 10 IPs", challenge_type="team")
        team_ip_reports = IpReport.objects.filter(user__in=team.members.all()).count()
        team_challenge.progress = min((team_ip_reports / 10) * 100, 100)
        team_challenge.save()

        if team_challenge.progress == 100:
            team.fresh_points += team_challenge.fresh_points
            team.save()

@receiver(post_save, sender=Issue)
def update_issue_report_challenge_progress(sender, instance, **kwargs):
    user = instance.user
    if user is None:
        return

    team = user.userprofile.team if user.userprofile.team else None

    # Update single user challenge progress
    single_challenge = Challenge.objects.get(title="Report 5 Issues", challenge_type="single")
    user_issues = Issue.objects.filter(user=user).count()
    single_challenge.progress = min((user_issues / 5) * 100, 100)
    single_challenge.save()

    if single_challenge.progress == 100:
        Points.objects.create(user=user, score=single_challenge.fresh_points, reason="Completed 'Report 5 Issues' challenge")

    # Update team challenge progress
    if team:
        team_challenge = Challenge.objects.get(title="Report 10 Issues", challenge_type="team")
        team_issues = Issue.objects.filter(user__in=team.members.all()).count()
        team_challenge.progress = min((team_issues / 10) * 100, 100)
        team_challenge.save()

        if team_challenge.progress == 100:
            team.fresh_points += team_challenge.fresh_points
            team.save()
