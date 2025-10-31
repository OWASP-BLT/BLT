# Heroku Deployment Guide for OWASP BLT

This guide will help you deploy the OWASP BLT application to Heroku.

## Prerequisites

- A Heroku account (sign up at [heroku.com](https://heroku.com))
- Heroku CLI installed ([installation guide](https://devcenter.heroku.com/articles/heroku-cli))
- Git installed on your local machine
- Google Cloud Storage account with credentials

## Quick Deploy

Click the button below to deploy to Heroku:

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

## Manual Deployment

### 1. Clone the Repository

```bash
git clone https://github.com/OWASP-BLT/BLT.git
cd BLT
```

### 2. Login to Heroku

```bash
heroku login
```

### 3. Create a New Heroku App

```bash
heroku create your-app-name
```

### 4. Add Required Buildpacks

The application uses two buildpacks:
- PostgreSQL connection pooling (pgbouncer)
- Python

```bash
heroku buildpacks:add https://github.com/heroku/heroku-buildpack-pgbouncer
heroku buildpacks:add heroku/python
```

### 5. Add PostgreSQL Database

```bash
heroku addons:create heroku-postgresql:mini
```

### 6. Configure Environment Variables

Set the required environment variables:

```bash
# Required: Google Cloud Storage credentials (as JSON string)
# SECURITY NOTE: Avoid setting sensitive credentials directly in command line
# Option 1: Use a file to avoid command history exposure
cat your-credentials.json | heroku config:set GOOGLE_CREDENTIALS="$(cat)"

# Option 2: Set via Heroku dashboard (Settings > Config Vars)
# This is the most secure method for sensitive credentials

# Optional but recommended
heroku config:set SECRET_KEY=$(openssl rand -base64 32)
heroku config:set DEBUG=False
heroku config:set ALLOWED_HOSTS=".herokuapp.com,yourdomain.com"

# Email configuration (SendGrid)
heroku config:set SENDGRID_USERNAME=your_username
heroku config:set SENDGRID_PASSWORD=your_password

# OAuth (GitHub)
heroku config:set GITHUB_CLIENT_ID=your_client_id
heroku config:set GITHUB_CLIENT_SECRET=your_client_secret

# OAuth (Google)
heroku config:set GOOGLE_CLIENT_ID=your_google_client_id
heroku config:set GOOGLE_CLIENT_SECRET=your_google_client_secret

# Sentry (optional, for error tracking)
heroku config:set SENTRY_DSN=your_sentry_dsn

# OpenAI (optional)
heroku config:set OPENAI_API_KEY=your_openai_key

# Redis (for caching and channels)
heroku addons:create rediscloud:30
# The REDISCLOUD_URL will be set automatically

# Bluesky integration (optional)
heroku config:set BLUESKY_USERNAME=your_username
heroku config:set BLUESKY_PASSWORD=your_password

# Slack integration (optional)
heroku config:set SLACK_BOT_TOKEN=your_slack_bot_token
heroku config:set SLACK_SIGNING_SECRET=your_slack_signing_secret

# GitHub token (optional)
heroku config:set GITHUB_TOKEN=your_github_token
```

### 7. Deploy to Heroku

```bash
git push heroku main
```

Or if you're on a different branch:

```bash
git push heroku your-branch:main
```

### 8. Run Database Migrations

Migrations should run automatically via the `release` command in the Procfile. If you need to run them manually:

```bash
heroku run python manage.py migrate
```

### 9. Create a Superuser

```bash
heroku run python manage.py createsuperuser
```

### 10. Open Your Application

```bash
heroku open
```

## Important Configuration Details

### Database Connection Pooling

The app uses pgbouncer for efficient database connection management. The `bin/start-pgbouncer` script handles this automatically.

### Static Files

Static files are served using WhiteNoise middleware, which is already configured in the Django settings.

### Media Files

Media files are stored in Google Cloud Storage. Make sure to:
1. Create a Google Cloud Storage bucket
2. Create a service account with access to the bucket
3. Set the `GOOGLE_CREDENTIALS` environment variable with the service account JSON

### Redis for Channels

The application uses Django Channels for WebSocket support. Redis is required for the channel layer in production:

```bash
heroku addons:create rediscloud:30
```

## Troubleshooting

### Check Logs

```bash
heroku logs --tail
```

### View Specific App Logs

```bash
heroku logs --tail --app your-app-name
```

### Restart the App

```bash
heroku restart
```

### Check Running Dynos

```bash
heroku ps
```

### Access Django Shell

```bash
heroku run python manage.py shell
```

### Database Console

```bash
heroku pg:psql
```

## Scaling

To scale your application:

```bash
# Scale web dynos
heroku ps:scale web=2

# Upgrade database
heroku addons:upgrade heroku-postgresql:standard-0
```

## CI/CD Integration

You can set up automatic deployments from GitHub:

1. Go to your Heroku Dashboard
2. Select your app
3. Go to the "Deploy" tab
4. Connect your GitHub repository
5. Enable automatic deploys from your main branch

## Security Recommendations

1. Always use HTTPS in production (automatically enforced when `DYNO` env var is present)
2. Set `DEBUG=False` in production
3. Use strong `SECRET_KEY`
4. Regularly update dependencies
5. Configure Sentry for error monitoring
6. Use environment-specific configurations

## Additional Resources

- [Heroku Python Documentation](https://devcenter.heroku.com/articles/getting-started-with-python)
- [Django on Heroku](https://devcenter.heroku.com/articles/django-app-configuration)
- [Heroku Postgres](https://devcenter.heroku.com/articles/heroku-postgresql)

## Support

For issues related to:
- BLT Application: [GitHub Issues](https://github.com/OWASP-BLT/BLT/issues)
- Heroku Platform: [Heroku Support](https://help.heroku.com/)
