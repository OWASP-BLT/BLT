# Weekly Stats Delivery

## Overview

The weekly stats delivery feature sends automated bug statistics reports to all organizations registered in the BLT system.

## Implementation

The feature is implemented as a separate Django management command:
```
website/management/commands/send_weekly_stats.py
```

This command is automatically called by the weekly cron scheduler (`run_weekly.py`).

## Usage

### Manual Execution

You can run the weekly stats command directly:
```bash
python manage.py send_weekly_stats
```

Or run all weekly tasks (including weekly stats):
```bash
python manage.py run_weekly
```

This will:
- Iterate through all domains in the system
- Generate weekly statistics for each domain (open issues, closed issues, total issues)
- Send formatted email reports to domains with configured email addresses
- Log successes and failures
- Display summary of sent/failed reports

### Automated Execution with Cron

The weekly stats are automatically run as part of the weekly cron job. To schedule weekly execution, add a cron job:

```bash
# Edit crontab
crontab -e

# Add entry to run every Monday at 9:00 AM
0 9 * * 1 cd /path/to/BLT && /path/to/python manage.py run_weekly >> /var/log/blt/weekly.log 2>&1
```

### Using with Heroku Scheduler

For Heroku deployments, add a scheduled job in the Heroku Scheduler addon:

1. Go to your app's Resources tab
2. Add or open "Heroku Scheduler"
3. Create a new job with:
   - Command: `python manage.py run_weekly`
   - Frequency: Every week on Monday at 9:00 AM UTC

## Report Contents

Each weekly report includes:

- Organization name
- Count of open issues
- Count of closed issues
- Total issue count
- Details of the 10 most recent issues:
  - Description (truncated to 100 characters)
  - View count
  - Label

## Email Configuration

The command uses Django's email settings configured in `blt/settings.py`:

- **From Address**: `DEFAULT_FROM_EMAIL` setting
- **To Address**: Domain's configured email address
- **Subject**: "OWASP BLT Weekly Report"

### Requirements

For emails to be sent, ensure:
1. Domain has an email address configured in the database
2. Django email backend is properly configured (SMTP, SendGrid, etc.)
3. Email credentials are set in environment variables

## Error Handling

The command includes comprehensive error handling:

- **Missing Email**: Domains without email addresses are skipped with a warning
- **Email Failures**: Failed email sends are logged with full error details
- **Command Errors**: Any unhandled exceptions are logged

## Logging

The command logs to the `website.management.commands.send_weekly_stats` logger:

- **INFO**: Start/completion messages and successful sends
- **WARNING**: Skipped domains (missing email)
- **ERROR**: Failed email sends with full traceback

## Testing

Test the command locally:

```bash
# Run weekly stats directly
python manage.py send_weekly_stats

# Run all weekly tasks
python manage.py run_weekly

# Test email configuration first
python manage.py shell
>>> from django.core.mail import send_mail
>>> from django.conf import settings
>>> send_mail('Test', 'Testing', settings.DEFAULT_FROM_EMAIL, ['test@example.com'])
```

## Troubleshooting

### No emails being sent

1. Check email configuration in settings.py
2. Verify SMTP credentials in environment variables
3. Check domain email addresses in database: `Domain.objects.filter(email__isnull=False)`
4. Review logs for specific error messages

### Command not found

Ensure you're in the correct directory and using the right Python environment:
```bash
cd /path/to/BLT
which python  # Should point to your virtual environment
python manage.py send_weekly_stats
```

### Permission denied errors

Ensure the user running the command has:
- Read access to the project directory
- Write access to log files (if logging to file)
- Access to the database
