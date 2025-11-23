# Celery Setup for Weekly Stats Delivery

## Overview

This document describes the Celery configuration for scheduling and delivering weekly statistics reports to organizations registered in the BLT system.

## Components

### 1. Celery Application (`blt/celery.py`)
The main Celery application configuration that connects to Django settings and autodiscovers tasks.

### 2. Task Definition (`website/tasks.py`)
Contains the `send_weekly_stats` task that:
- Retrieves all domains with registered emails
- Generates weekly statistics reports for each organization
- Sends reports via email
- Logs successes and failures

### 3. Celery Beat Schedule (`blt/settings.py`)
Configured to run the weekly stats task every Monday at 9:00 AM UTC.

## Configuration

### Environment Variables
Ensure the following environment variable is set:
- `REDISCLOUD_URL`: Redis connection URL (used as Celery broker and result backend)

### Django Settings
The following Celery settings are configured in `blt/settings.py`:
- `CELERY_BROKER_URL`: Redis URL for message broker
- `CELERY_RESULT_BACKEND`: Redis URL for storing task results
- `CELERY_BEAT_SCHEDULE`: Schedule for periodic tasks

## Running Celery

### Start Celery Worker
```bash
celery -A blt worker --loglevel=info
```

### Start Celery Beat (Scheduler)
```bash
celery -A blt beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Run Both Together (Development)
```bash
celery -A blt worker --beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## Manual Execution

### Using Management Command
```bash
python manage.py run_weekly
```

### Using Django Shell
```python
from website.tasks import send_weekly_stats

# Synchronous execution (for testing)
result = send_weekly_stats()
print(result)

# Asynchronous execution (production)
task = send_weekly_stats.delay()
print(f"Task ID: {task.id}")
```

## Monitoring

### Check Task Status
```python
from celery.result import AsyncResult
result = AsyncResult(task_id)
print(f"Status: {result.status}")
print(f"Result: {result.result}")
```

### View Scheduled Tasks
Access the Django admin panel at `/admin/django_celery_beat/` to view and manage scheduled tasks.

## Production Deployment

### Using Supervisor (Linux)
Create a supervisor configuration file for the worker and beat processes:

```ini
[program:celery-worker]
command=celery -A blt worker --loglevel=info
directory=/path/to/BLT
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/worker.log

[program:celery-beat]
command=celery -A blt beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
directory=/path/to/BLT
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/beat.log
```

### Using Docker
Add services to `docker-compose.yml`:

```yaml
celery-worker:
  build: .
  command: celery -A blt worker --loglevel=info
  depends_on:
    - redis
    - db
  environment:
    - REDISCLOUD_URL=redis://redis:6379/0

celery-beat:
  build: .
  command: celery -A blt beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
  depends_on:
    - redis
    - db
  environment:
    - REDISCLOUD_URL=redis://redis:6379/0
```

## Database Migrations

After installing django-celery-beat, run migrations:
```bash
python manage.py migrate django_celery_beat
```

## Troubleshooting

### Task Not Running
1. Check that Redis is running and accessible
2. Verify Celery worker and beat are running
3. Check logs for errors
4. Verify the schedule in Django admin

### Email Not Sending
1. Check email configuration in `blt/settings.py`
2. Verify domain email addresses are configured
3. Check logs for specific error messages

### Performance Issues
1. Consider using multiple workers: `celery -A blt worker --concurrency=4`
2. Monitor Redis memory usage
3. Implement task rate limiting if needed
