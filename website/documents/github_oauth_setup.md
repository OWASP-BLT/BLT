# GitHub OAuth Setup for BLT

This document provides instructions for setting up GitHub OAuth authentication for both development and production environments in the OWASP BLT application.

## Prerequisites

- GitHub account with permissions to create OAuth applications
- Access to the BLT server environment variables
- Administrative access to the Django admin panel

## Setting Up a GitHub OAuth App

1. Log in to your GitHub account and navigate to **Settings** > **Developer settings** > **OAuth Apps**
2. Click **New OAuth App**
3. Fill in the details:
   - **Application name**: `OWASP BLT` (or a name of your choice)
   - **Homepage URL**: `https://blt.owasp.org` (or your development URL)
   - **Application description**: (Optional) A description of the app
   - **Authorization callback URL**: This is critical and must match exactly with your application's callback URL
     - For production: `https://blt.owasp.org/accounts/github/login/callback/`
     - For development: `http://127.0.0.1:8000/accounts/github/login/callback/`
4. Click **Register application**
5. On the next screen, note your **Client ID**
6. Click **Generate a new client secret** and note the **Client Secret** (you won't be able to see it again)

## Configuring BLT Environment Variables

Add the following to your `.env` file:

```
GITHUB_CLIENT_ID=your_client_id_here
GITHUB_CLIENT_SECRET=your_client_secret_here
CALLBACK_URL_FOR_GITHUB=https://blt.owasp.org/accounts/github/login/callback/
```

For development, the callback URL would be:
```
CALLBACK_URL_FOR_GITHUB=http://127.0.0.1:8000/accounts/github/login/callback/
```

## Setting Up the Database

After configuring your environment variables, run the management command to set up the GitHub OAuth provider in the database:

```bash
python manage.py setup_github_oauth
```

For production servers with a specific domain:

```bash
python manage.py setup_github_oauth --domain blt.owasp.org
```

## Checking Your Configuration

You can check if your configuration is correctly set up without modifying any data:

```bash
python manage.py setup_github_oauth --check-only
```

## Troubleshooting

### The redirect_uri is not associated with this application

This error occurs when the callback URL in your GitHub OAuth app doesn't match the one your application is using. To fix this:

1. Verify the callback URL in your GitHub OAuth app settings
2. Ensure it matches exactly with your `CALLBACK_URL_FOR_GITHUB` environment variable
3. Make sure the protocol (http/https) matches as well

### OAuth State Parameter Mismatch

This is a security feature. If you see this error:

1. Clear your browser cookies and try again
2. Make sure the application is properly setting the state parameter in the session

### Debug With the Check-Only Flag

Use the `--check-only` flag with the setup_github_oauth command to diagnose issues:

```bash
python manage.py setup_github_oauth --check-only
```

## Advanced: Multiple Environments

If you need to support both development and production environments:

1. Create separate GitHub OAuth applications for each environment
2. Use environment variables to determine which credentials to use
3. Update the site domain in the database according to the environment

## Security Considerations

- Never commit OAuth credentials to your repository
- Always use HTTPS for production environments
- Implement proper state parameter validation to prevent CSRF attacks
- Regularly audit your OAuth application permissions on GitHub 