from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from website.forms import ReminderSettingsForm
from website.models import ReminderSettings

@login_required
def reminder_settings(request):
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