import os
from datetime import datetime

import pytz
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import redirect, render
from django.utils import timezone
from slack_sdk.web import WebClient

from website.forms import ReminderSettingsForm
from website.models import ReminderSettings

if os.getenv("ENV") != "production":
    from dotenv import load_dotenv

    load_dotenv()

SLACK_CLIENT_ID = os.environ.get("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.environ.get("SLACK_CLIENT_SECRET")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")


@login_required
def reminder_settings(request):
    settings, created = ReminderSettings.objects.get_or_create(
        user=request.user,
        defaults={
            "reminder_time": timezone.now().time(),  # Set default time to current time
            "timezone": "UTC",  # Set default timezone
            "is_active": False,  # Set default active state
        },
    )

    if request.method == "POST":
        form = ReminderSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            # Get the timezone from the form
            user_timezone = form.cleaned_data["timezone"]

            # Create a timezone object
            tz = pytz.timezone(user_timezone)

            # Get the reminder time from the form
            reminder_time = form.cleaned_data["reminder_time"]

            # Create a datetime object with today's date and the reminder time
            today = timezone.now().date()
            local_dt = tz.localize(datetime.combine(today, reminder_time))

            # Convert to UTC for storage
            utc_dt = local_dt.astimezone(pytz.UTC)

            # Save the form
            form.save()

            # Update the UTC time
            settings.reminder_time_utc = utc_dt.time()
            settings.save()

            messages.success(request, "Your reminder settings have been updated successfully.")
            return redirect("reminder_settings")
    else:
        form = ReminderSettingsForm(instance=settings)

        # If we have a UTC time stored, convert it to the user's timezone for display
        if settings.reminder_time_utc:
            user_tz = pytz.timezone(settings.timezone)
            today = timezone.now().date()
            utc_dt = pytz.UTC.localize(datetime.combine(today, settings.reminder_time_utc))
            local_dt = utc_dt.astimezone(user_tz)
            form.initial["reminder_time"] = local_dt.time()

    return render(request, "website/reminder_settings.html", {"form": form, "settings": settings, "user": request.user})


@login_required
def send_test_reminder(request):
    """Send a test reminder email to the user."""
    if request.method == "POST":
        try:
            # Get user's reminder settings
            reminder_settings = ReminderSettings.objects.filter(user=request.user).first()

            # Get organization info
            org_name = ""
            org_info_html = ""
            if hasattr(request.user, "userprofile") and request.user.userprofile.team:
                org_name = request.user.userprofile.team.name
                org_info_html = f"""
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin: 20px 0; border-left: 4px solid #e74c3c;">
                        <p style="margin: 0; color: #666; font-size: 14px;"><strong>Organization:</strong> {org_name}</p>
                    </div>
                """

            # Format reminder time if settings exist
            reminder_time_str = ""
            timezone_str = ""
            time_info_html = ""
            if reminder_settings:
                reminder_time_str = reminder_settings.reminder_time.strftime("%I:%M %p")
                timezone_str = reminder_settings.timezone
                time_info_html = f"""
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin: 20px 0;">
                        <p style="margin: 0; color: #666; font-size: 14px;"><strong>Your Reminder Time:</strong> {reminder_time_str} ({timezone_str})</p>
                    </div>
                """

            # Plain text body
            plain_body = f"""Hello {request.user.username},

This is a test reminder for your daily check-in{f" for {org_name}" if org_name else ""}.

{f"Reminder Time: {reminder_time_str} ({timezone_str})" if reminder_time_str else ""}

Click here to check in: {request.build_absolute_uri("/add-sizzle-checkin/")}

You can manage your reminder settings at: {request.build_absolute_uri("/reminder-settings/")}

Regular check-ins help keep your team informed about your progress and any challenges you might be facing.

Thank you for keeping your team updated!

Best regards,
The BLT Team"""

            # Add HTML content
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
                    <div style="background-color: #fff3cd; padding: 10px; border-radius: 4px; margin-bottom: 20px; border-left: 4px solid #ffc107;">
                        <p style="margin: 0; color: #856404; font-size: 14px;"><strong>⚠️ This is a test reminder</strong></p>
                    </div>
                    <h2 style="color: #333; margin-bottom: 20px;">Daily Check-in Reminder</h2>
                    <p>Hello <strong>{request.user.username}</strong>,</p>
                    <p>This is a test reminder for your daily check-in{f" for <strong>{org_name}</strong>" if org_name else ""}! Please log in to update your status.</p>
                    {org_info_html}
                    {time_info_html}
                    <div style="margin: 30px 0; text-align: center;">
                        <a href="{request.build_absolute_uri("/add-sizzle-checkin/")}" 
                           style="display: inline-block; background-color: #e74c3c; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold; text-align: center; min-width: 200px;">
                           Check In Now
                        </a>
                    </div>
                    <p>Regular check-ins help keep your team informed about your progress and any challenges you might be facing.</p>
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; text-align: center;">
                        <p style="font-size: 13px; color: #666;">
                            <a href="{request.build_absolute_uri("/reminder-settings/")}" style="color: #e74c3c; text-decoration: none;">Manage your reminder settings</a>
                        </p>
                    </div>
                    <p style="margin-top: 20px;">Thank you for keeping your team updated!</p>
                    <p style="color: #666; font-size: 14px;">Best regards,<br>The BLT Team</p>
                </div>
            </body>
            </html>
            """

            # Create email with plain text body and HTML alternative
            email = EmailMultiAlternatives(
                subject="Test Daily Check-in Reminder",
                body=plain_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            email.attach_alternative(html_content, "text/html")

            # Send the email
            email.send()

            messages.success(request, "Test reminder sent successfully!")
        except Exception:
            messages.error(request, "Failed to send test reminder. Please try again later.")

    return redirect("reminder_settings")


@login_required
def connect_slack_account(request):
    """Initiate Slack OAuth flow to connect user's Slack account."""
    if not SLACK_CLIENT_ID:
        messages.error(request, "Slack integration is not configured.")
        return redirect("reminder_settings")

    redirect_uri = request.build_absolute_uri("/slack/oauth/callback/")
    state = request.user.username  # Using username as state for simplicity

    slack_oauth_url = (
        f"https://slack.com/oauth/v2/authorize?"
        f"client_id={SLACK_CLIENT_ID}&"
        f"scope=&"
        f"user_scope=chat:write&"
        f"redirect_uri={redirect_uri}&"
        f"state={state}"
    )

    return redirect(slack_oauth_url)


@login_required
def slack_oauth_callback(request):
    """Handle Slack OAuth callback and store user's Slack ID."""
    code = request.GET.get("code")
    state = request.GET.get("state")

    if not code:
        messages.error(request, "Slack connection failed. No authorization code received.")
        return redirect("reminder_settings")

    if state != request.user.username:
        messages.error(request, "Slack connection failed. Invalid state parameter.")
        return redirect("reminder_settings")

    redirect_uri = request.build_absolute_uri("/slack/oauth/callback/")

    try:
        # Exchange code for access token
        response = requests.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id": SLACK_CLIENT_ID,
                "client_secret": SLACK_CLIENT_SECRET,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )

        data = response.json()

        if not data.get("ok"):
            messages.error(request, f"Slack connection failed: {data.get('error', 'Unknown error')}")
            return redirect("reminder_settings")

        # Get the user's Slack ID
        slack_user_id = data.get("authed_user", {}).get("id")

        if slack_user_id:
            # Store Slack user ID in user profile
            profile = request.user.userprofile
            profile.slack_user_id = slack_user_id
            profile.save()

            messages.success(request, "Your Slack account has been connected successfully!")
        else:
            messages.error(request, "Failed to retrieve Slack user ID.")

    except Exception as e:
        messages.error(request, "An error occurred while connecting to Slack. Please try again.")

    return redirect("reminder_settings")


@login_required
def disconnect_slack_account(request):
    """Disconnect user's Slack account."""
    if request.method == "POST":
        try:
            profile = request.user.userprofile
            profile.slack_user_id = None
            profile.save()

            # Also disable Slack notifications in reminder settings
            reminder_settings = ReminderSettings.objects.filter(user=request.user).first()
            if reminder_settings:
                reminder_settings.slack_notifications_enabled = False
                reminder_settings.save()

            messages.success(request, "Your Slack account has been disconnected.")
        except Exception:
            messages.error(request, "Failed to disconnect Slack account. Please try again.")

    return redirect("reminder_settings")


@login_required
def send_test_slack_reminder(request):
    """Send a test reminder via Slack DM to the user."""
    if request.method == "POST":
        try:
            profile = request.user.userprofile

            if not profile.slack_user_id:
                messages.error(request, "You need to connect your Slack account first.")
                return redirect("reminder_settings")

            if not SLACK_BOT_TOKEN:
                messages.error(request, "Slack bot is not configured.")
                return redirect("reminder_settings")

            client = WebClient(token=SLACK_BOT_TOKEN)

            # Send test DM
            message = (
                f"Hello {request.user.username}! 👋\n\n"
                f"This is a test reminder for your daily check-in.\n\n"
                f"Complete your daily check-in: {request.build_absolute_uri('/add-sizzle-checkin/')}"
            )

            response = client.chat_postMessage(channel=profile.slack_user_id, text=message)

            if response.get("ok"):
                messages.success(request, "Test Slack reminder sent successfully!")
            else:
                messages.error(request, "Failed to send Slack message.")

        except Exception:
            messages.error(request, "Failed to send test Slack reminder. Please try again later.")

    return redirect("reminder_settings")
