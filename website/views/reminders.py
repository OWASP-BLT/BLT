from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from website.forms import ReminderSettingsForm
from website.models import ReminderSettings, UserProfile
import pytz

@login_required
def reminder_settings(request):
    """
    View for managing user's reminder settings.
    Allows users to set their preferred reminder time, timezone, and enable/disable reminders.
    """
    try:
        settings = ReminderSettings.objects.get(user=request.user)
    except ReminderSettings.DoesNotExist:
        settings = ReminderSettings(user=request.user)

    if request.method == 'POST':
        form = ReminderSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your reminder settings have been updated successfully.')
            return redirect('reminder_settings')
    else:
        form = ReminderSettingsForm(instance=settings)

    return render(request, 'website/reminder_settings.html', {
        'form': form,
        'settings': settings
    })

@login_required
def check_reminder_status(request):
    """
    View to check if a user needs a reminder based on their settings and last check-in.
    This is used by the management command to determine who needs reminders.
    """
    try:
        settings = ReminderSettings.objects.get(user=request.user)
        if not settings.is_active:
            return False

        # Get user's timezone
        user_tz = pytz.timezone(settings.timezone)
        now = timezone.now().astimezone(user_tz)
        
        # Get user's last check-in
        try:
            profile = UserProfile.objects.get(user=request.user)
            last_checkin = profile.last_checkin
            if last_checkin:
                last_checkin = last_checkin.astimezone(user_tz)
                
                # Check if user has checked in today
                if last_checkin.date() == now.date():
                    return False
        except UserProfile.DoesNotExist:
            pass

        # Check if current time matches reminder time
        reminder_time = settings.reminder_time
        current_time = now.time()
        
        # Allow for a 5-minute window
        time_diff = abs((current_time.hour * 60 + current_time.minute) - 
                       (reminder_time.hour * 60 + reminder_time.minute))
        
        return time_diff <= 5

    except ReminderSettings.DoesNotExist:
        return False
