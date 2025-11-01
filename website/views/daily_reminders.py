import os
from datetime import datetime

import pytz
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
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
            # Create email message with the correct daily check-in link
            email = EmailMessage(
                subject="Test Daily Check-in Reminder",
                body=f"""Hello {request.user.username},

This is a test reminder for your daily check-in. Please click the link below to complete your daily check-in:

{request.build_absolute_uri('/add-sizzle-checkin/')}

Best regards,
The BLT Team""",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )

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
