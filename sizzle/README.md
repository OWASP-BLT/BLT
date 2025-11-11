# Sizzle

A pluggable Django app for daily check-ins, time tracking, and team activity monitoring. Track your team's progress, manage daily status reports, and visualize productivity with built-in leaderboards and streak tracking.

## Features

- **Daily Check-ins**: Team members submit daily status reports
- **Time Logging**: Track time spent on tasks and projects
- **Leaderboards**: Gamified rankings based on activity
- **Streak Tracking**: Monitor consecutive check-in streaks
- **Reminders**: Automated daily reminder system (email/Slack)
- **Analytics**: View individual and team reports
- **Slack Integration**: Post check-ins directly to Slack (optional)

## Requirements

- Python >= 3.8
- Django >= 4.0
- pytz

## Installation

### 1. Install via pip

```
pip install django-sizzle
```

Or install from source:
```
git clone https://github.com/OWASP-BLT/django-sizzle.git
cd django-sizzle
pip install -e .
```

### 2. Add to INSTALLED_APPS

In your Django project's `settings.py`:

```
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Your apps
    'myapp',
    
    # Add Sizzle
    'sizzle',
]
```

### 3. Include Sizzle URLs

In your main `urls.py`:

```
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Add Sizzle URLs
    path('sizzle/', include('sizzle.urls')),
    
    # Your other URLs
]
```

### 4. Add Context Processor (For Template Integration)

Add the context processor to your `settings.py` to enable seamless template integration:

```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Your templates directory
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                
                # Add Sizzle context processor for template integration
                'sizzle.context_processors.sizzle_context',
            ],
        },
    },
]
```

### 5. Configure Template Integration (Optional)

To integrate Sizzle with your project's existing layout:

```python
# In settings.py - Tell Sizzle which base template to extend from your project
SIZZLE_PARENT_BASE = 'base.html'  # Your main project template

# If your project has sidenav/navigation that Sizzle should include
SIZZLE_SHOW_SIDENAV = True  # Default: True
```

### 6. Run Migrations

```
python manage.py migrate sizzle
```

This creates three database tables:
- `sizzle_dailystatusreport`: Stores daily check-in reports
- `sizzle_timelog`: Stores time tracking entries
- `sizzle_remindersettings`: Stores user reminder preferences

### 7. Collect Static Files

```
python manage.py collectstatic
```

### 8. Create Superuser (if needed)

```
python manage.py createsuperuser
```

## Quick Start

### Access Sizzle

Start your development server:
```
python manage.py runserver
```

Visit these URLs:
- Main dashboard: `http://localhost:8000/sizzle/`
- Submit check-in: `http://localhost:8000/sizzle/check-in/`
- View time logs: `http://localhost:8000/sizzle/time-logs/`
- Admin panel: `http://localhost:8000/admin/`

### Submit Your First Check-in

1. Log in to your Django app
2. Navigate to `/sizzle/check-in/`
3. Fill out the daily status form
4. Submit to track your streak!

## Configuration

### Basic Settings

Add these to your `settings.py` to customize Sizzle:

```
# Optional: Customize the base template (see Template Customization below)
SIZZLE_BASE_TEMPLATE = 'sizzle/base.html'  # Default

# Optional: Sizzle-specific settings
SIZZLE_SETTINGS = {
    'ENABLE_SLACK_INTEGRATION': False,  # Set to True if using Slack
    'ENABLE_EMAIL_REMINDERS': True,     # Send email reminders
    'DEFAULT_REMINDER_TIME': '09:00',   # Daily reminder time (24-hour format)
    'STREAK_TRACKING_ENABLED': True,    # Track consecutive check-in streaks
    'TIMEZONE': 'UTC',                  # Timezone for check-ins
}
```

### Slack Integration (Optional)

If you want Slack notifications:

1. Install Slack dependencies:
```
pip install django-sizzle[slack]
```

2. Add Slack configuration to `settings.py`:
```
SIZZLE_SETTINGS = {
    'ENABLE_SLACK_INTEGRATION': True,
}

# You'll need these from your Slack app
SLACK_BOT_TOKEN = 'xoxb-your-bot-token'
SLACK_SIGNING_SECRET = 'your-signing-secret'
```

3. Run the Slack time log command:
```
python manage.py slack_daily_timelogs
```

### Email Reminders

To enable email reminders for check-ins:

1. Configure Django email settings in `settings.py`:
```
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

2. Set up a cron job to send daily reminders:
```
# Add to crontab (example: 9 AM daily)
0 9 * * * cd /path/to/project && python manage.py send_daily_reminders
```

## Template Customization

Sizzle provides its own minimal base template (`sizzle/base.html`) so it works out-of-the-box. However, you'll likely want to integrate it with your site's design.

### Option 1: Override Sizzle's Base Template

Create `your_project/templates/sizzle/base.html`:

```
{% extends "your_site_base.html" %}

{% block your_content_block %}
    {# Sizzle templates expect these blocks: #}
    {% block title %}{% endblock %}
    {% block content %}{% endblock %}
{% endblock %}

{% block extra_css %}
    {% load static %}
    <link rel="stylesheet" href="{% static 'sizzle/css/sizzle.css' %}">
{% endblock %}
```

Make sure your template loader can find it:
```
# settings.py
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Your project templates
        'APP_DIRS': True,  # Important: Finds sizzle/templates/
        ...
    },
]
```

### Option 2: Use Settings to Specify Base Template

In `settings.py`:
```
SIZZLE_BASE_TEMPLATE = 'my_site/base.html'
```

Then create `my_site/base.html` with these required blocks:
```
{% block title %}{% endblock %}
{% block content %}{% endblock %}
```

### Required Template Blocks

All Sizzle templates expect these blocks in your base template:

- `{% block title %}` - Page title
- `{% block content %}` - Main content area
- `{% block extra_head %}` - Additional CSS/meta tags (optional)
- `{% block extra_js %}` - Additional JavaScript (optional)

## Database Models

### DailyStatusReport

Stores daily check-in submissions.

**Fields**:
- `user` (ForeignKey): User who submitted the report
- `content` (TextField): Check-in message/status
- `created_at` (DateTimeField): Submission timestamp
- `streak_count` (IntegerField): Current streak days

**Example usage**:
```
from sizzle.models import DailyStatusReport

# Get today's check-ins
today_reports = DailyStatusReport.objects.filter(
    created_at__date=timezone.now().date()
)
```

### TimeLog

Tracks time spent on tasks.

**Fields**:
- `user` (ForeignKey): User logging time
- `organization` (ForeignKey, nullable): Associated organization (if any)
- `hours` (DecimalField): Hours worked
- `date` (DateField): Date of work
- `task_description` (TextField): What was worked on

**Example usage**:
```
from sizzle.models import TimeLog

# Log time
TimeLog.objects.create(
    user=request.user,
    hours=3.5,
    date=timezone.now().date(),
    task_description="Fixed login bug"
)
```

### ReminderSettings

User preferences for reminders.

**Fields**:
- `user` (OneToOneField): User
- `reminder_time` (TimeField): Preferred reminder time
- `enabled` (BooleanField): Whether reminders are active
- `slack_enabled` (BooleanField): Send via Slack

## Management Commands

Sizzle includes several management commands for automated tasks:

### Daily Check-in Reminders
Send in-app notifications to remind users to submit their daily check-in.

```bash
python manage.py daily_checkin_reminder
```

**What it does:**
- Finds all users in organizations where `check_ins_enabled=True`
- Creates Notification objects for each user
- Links to `/add-sizzle-checkin/` URL

**Dependencies:**
- UserProfile model (has team field)
- Notification model (website app)
- Organization's `check_ins_enabled` flag

**Cron setup:**
```bash
0 9 * * * cd /path/to/project && python manage.py daily_checkin_reminder
```

### Email Reminder System
Send email reminders to users based on their personal ReminderSettings.

```bash
python manage.py cron_send_reminders
```

**What it does:**
- Checks each user's ReminderSettings for:
  - `enabled=True`
  - `reminder_time` matches current time
  - `reminder_days` includes today
- Checks if user hasn't checked in today (`UserProfile.last_check_in`)
- Sends personalized email reminders
- Logs all activity to `logs/reminder_emails.log`

**Advanced features:**
- Respects timezone settings
- Configurable days of week
- Tracks reminder history
- Random delays to avoid email spam detection

**Cron setup (runs every hour):**
```bash
0 * * * * cd /path/to/project && python manage.py cron_send_reminders
```

### Slack Daily Timelogs
Post daily timelog summaries to Slack channels.

```bash
python manage.py slack_daily_timelogs
```

**What it does:**
- Runs every hour (checks `current_hour_utc`)
- For each SlackIntegration where:
  - `daily_updates=True`
  - `daily_update_time` matches current hour
- Fetches all TimeLog entries from last 24 hours for that organization
- Formats summary message with:
  - Task names
  - Start/end times
  - GitHub issue URLs
  - Total time worked
- Posts to configured Slack channel

**Dependencies:**
- SlackIntegration model
- Organization model
- TimeLog model
- slack-bolt Python package
- Valid Slack bot tokens

**Example output:**
```
### Time Log Summary ###

Task: Bug fix - Issue #123
Start: 2024-11-08 09:00:00
End: 2024-11-08 11:30:00
Issue URL: https://github.com/org/repo/issues/123

Task: Feature development - Issue #456
Start: 2024-11-08 13:00:00
End: 2024-11-08 16:00:00
Issue URL: https://github.com/org/repo/issues/456

Total Time: 5 hours, 30 minutes, 0 seconds
```

**Cron setup (runs every hour):**
```bash
0 * * * * cd /path/to/project && python manage.py slack_daily_timelogs
```

### Run All Sizzle Daily Tasks
Master command that runs all Sizzle-related daily tasks.

```bash
python manage.py run_sizzle_daily
```

**What it does:**
- Calls `daily_checkin_reminder`
- Calls `cron_send_reminders`
- Provides centralized logging and error handling

**Cron setup (once daily):**
```bash
0 9 * * * cd /path/to/project && python manage.py run_sizzle_daily
```

## URLs Reference

| URL Pattern | View | Description |
|-------------|------|-------------|
| `/sizzle/` | `sizzle` | Main dashboard |
| `/sizzle/check-in/` | `checkIN` | Check-in list |
| `/sizzle/add-sizzle-checkin/` | `add_sizzle_checkIN` | Submit new check-in |
| `/sizzle/check-in/<id>/` | `checkIN_detail` | View specific check-in |
| `/sizzle/time-logs/` | `TimeLogListView` | View time logs |
| `/sizzle/api/timelogsreport/` | `TimeLogListAPIView` | Time log API |
| `/sizzle/sizzle-daily-log/` | `sizzle_daily_log` | Daily log view |
| `/sizzle/user-sizzle-report/<username>/` | `user_sizzle_report` | User report |

## Dependencies

### Required (Core)

These are installed automatically with `pip install django-sizzle`:

- **Django** (>= 4.0): Web framework
- **pytz** (>= 2023.3): Timezone handling

### Optional Dependencies

Install with extras for additional features:

**Slack Integration**:
```
pip install django-sizzle[slack]
```
Includes: `slack-bolt >= 1.18.0`

**Development Tools**:
```
pip install django-sizzle[dev]
```
Includes: `pytest`, `pytest-django`, `black`, `flake8`

## External Dependencies

Sizzle relies on these Django built-in models (you must have them):

- **User model**: `django.contrib.auth.models.User`
- **Organization model** (optional): If you have an Organization model, TimeLog can reference it
- **UserProfile model** (optional): If you track `last_check_in` field

**Note**: Sizzle works standalone, but integrates better if your project has these models.

## Troubleshooting

### "No module named 'sizzle'"
Make sure you added `'sizzle'` to `INSTALLED_APPS` in `settings.py`.

### "TemplateDoesNotExist: sizzle/base.html"
Run `python manage.py collectstatic` and ensure `APP_DIRS: True` in `TEMPLATES` settings.

### Templates look unstyled
1. Run `python manage.py collectstatic`
2. Make sure `STATIC_URL` is configured in `settings.py`
3. Check browser console for 404 errors on CSS files

### Migrations not applying
```
# Check pending migrations
python manage.py showmigrations sizzle

# Apply them
python manage.py migrate sizzle
```

## Development

### Running Tests

```
# Install dev dependencies
pip install django-sizzle[dev]

# Run tests
pytest
```

### Code Style

We use Black and isort for code formatting:

```
black sizzle/
isort sizzle/
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `pytest`
5. Format code: `black sizzle/ && isort sizzle/`
6. Submit a pull request

## License

This project is licensed under the AGPL-3.0 License - see LICENSE file for details.

## Credits

Developed as part of the OWASP Bug Logging Tool (BLT) project.

## Support

- GitHub Issues: https://github.com/OWASP-BLT/BLT/issues
- OWASP BLT: https://owasp.org/www-project-bug-logging-tool/

## Changelog

### Version 0.1.0 (2025-11-08)
- Initial release
- Daily check-in functionality
- Time logging
- Streak tracking
- Email reminders
- Slack integration (optional)
- REST API endpoints
    