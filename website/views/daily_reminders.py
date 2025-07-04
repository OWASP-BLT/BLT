from datetime import datetime

import pytz
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render
from django.utils import timezone

from website.forms import ReminderSettingsForm
from website.models import ReminderSettings


@login_required
def reminder_settings(request):
    settings, created = ReminderSettings.objects.get_or_create(
        user=request.user,
        defaults={
            "reminder_time": timezone.now().time(),  # Set default time to current time
            "timezone": "UTC",  # Set default timezone
            "is_active": False,  # Set default active
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

    return render(request, "website/reminder_settings.html", {"form": form, "settings": settings})


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
