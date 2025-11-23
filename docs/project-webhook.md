# Project Webhook Integration

## Overview

The Project Webhook feature allows external systems to trigger automatic recalculation of contributor statistics when a project is updated. This ensures that contributor stats remain current and accurate without requiring manual intervention.

## How It Works

When configured, projects can receive webhook notifications from external systems (e.g., CI/CD pipelines, GitHub Actions, project management tools). Upon receiving a valid webhook request, BLT automatically recalculates contributor statistics for all repositories associated with the project.

## Configuration

### Prerequisites

- Project must be created in BLT
- Project must have at least one repository associated with it
- You need administrator access to the project to configure webhooks

### Setting Up a Webhook

1. **Add Webhook Fields to Your Project**
   
   You need to set two fields on your Project model:
   - `webhook_url`: The URL endpoint that will receive webhook notifications (for documentation purposes)
   - `webhook_secret`: A secret key used for HMAC-SHA256 signature verification

   ```python
   from website.models import Project
   
   project = Project.objects.get(slug='your-project-slug')
   project.webhook_url = 'https://your-external-system.com/webhook'
   project.webhook_secret = 'your-secret-key-here'
   project.save()
   ```

2. **Generate a Strong Secret Key**
   
   Use a cryptographically secure random string for your webhook secret:
   
   ```python
   import secrets
   secret = secrets.token_urlsafe(32)
   print(secret)  # Use this as your webhook_secret
   ```

## Using the Webhook

### Endpoint

```
POST /project/<project-slug>/webhook/
```

### Authentication

The webhook uses HMAC-SHA256 signature verification to ensure requests are authentic. Every request must include an `X-Webhook-Signature` header containing the signature.

### Generating the Signature

The signature is calculated as follows:

```python
import hmac
import hashlib

def generate_signature(secret, payload):
    """Generate HMAC-SHA256 signature for webhook payload"""
    signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"
```

### Example Request

**Using Python:**

```python
import hmac
import hashlib
import json
import requests

# Configuration
project_slug = 'my-project'
webhook_url = f'https://blt.owasp.org/project/{project_slug}/webhook/'
webhook_secret = 'your-secret-key'

# Prepare payload (can be empty or contain metadata)
payload = json.dumps({
    'event': 'project_updated',
    'timestamp': '2024-01-01T00:00:00Z',
    'source': 'ci-pipeline'
})

# Generate signature
signature = hmac.new(
    webhook_secret.encode('utf-8'),
    payload.encode('utf-8'),
    hashlib.sha256
).hexdigest()

# Make request
headers = {
    'Content-Type': 'application/json',
    'X-Webhook-Signature': f'sha256={signature}'
}

response = requests.post(webhook_url, data=payload, headers=headers)
print(response.status_code)
print(response.json())
```

**Using cURL:**

```bash
#!/bin/bash

PROJECT_SLUG="my-project"
WEBHOOK_SECRET="your-secret-key"
PAYLOAD='{"event":"project_updated","timestamp":"2024-01-01T00:00:00Z"}'

# Generate signature
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | sed 's/^.* //')

# Make request
curl -X POST "https://blt.owasp.org/project/$PROJECT_SLUG/webhook/" \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: sha256=$SIGNATURE" \
  -d "$PAYLOAD"
```

### Response Format

**Success Response (200 OK):**

```json
{
  "status": "success",
  "message": "Contributor stats recalculation triggered",
  "project": "My Project",
  "repositories_updated": [
    "repo1",
    "repo2",
    "repo3"
  ]
}
```

**Partial Success Response (200 OK):**

When some repositories fail to update:

```json
{
  "status": "partial_success",
  "message": "Contributor stats recalculation triggered",
  "project": "My Project",
  "repositories_updated": ["repo1", "repo2"],
  "errors": [
    "Failed to update stats for repo3: API rate limit exceeded"
  ]
}
```

**Error Responses:**

- **400 Bad Request** - Webhook not configured
  ```json
  {
    "status": "error",
    "message": "Webhook not configured for this project"
  }
  ```

- **401 Unauthorized** - Missing signature
  ```json
  {
    "status": "error",
    "message": "Missing webhook signature"
  }
  ```

- **403 Forbidden** - Invalid signature
  ```json
  {
    "status": "error",
    "message": "Invalid webhook signature"
  }
  ```

- **404 Not Found** - Project doesn't exist
  ```json
  {
    "status": "error",
    "message": "Project not found"
  }
  ```

- **405 Method Not Allowed** - Wrong HTTP method
  ```json
  {
    "error": "Method not allowed"
  }
  ```

- **500 Internal Server Error** - Unexpected error
  ```json
  {
    "status": "error",
    "message": "An unexpected error occurred"
  }
  ```

## Integration Examples

### GitHub Actions

Trigger the webhook after a successful deployment:

```yaml
name: Deploy and Update Stats

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Deploy application
        run: |
          # Your deployment steps here
          
      - name: Trigger BLT Webhook
        env:
          WEBHOOK_SECRET: ${{ secrets.BLT_WEBHOOK_SECRET }}
        run: |
          PAYLOAD='{"event":"deployment","branch":"main","commit":"${{ github.sha }}"}'
          SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | sed 's/^.* //')
          
          curl -X POST "https://blt.owasp.org/project/my-project/webhook/" \
            -H "Content-Type: application/json" \
            -H "X-Webhook-Signature: sha256=$SIGNATURE" \
            -d "$PAYLOAD"
```

### GitLab CI/CD

```yaml
trigger_blt_webhook:
  stage: deploy
  script:
    - apk add --no-cache curl openssl
    - PAYLOAD='{"event":"deployment","pipeline":"'$CI_PIPELINE_ID'"}'
    - SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | sed 's/^.* //')
    - |
      curl -X POST "https://blt.owasp.org/project/my-project/webhook/" \
        -H "Content-Type: application/json" \
        -H "X-Webhook-Signature: sha256=$SIGNATURE" \
        -d "$PAYLOAD"
  only:
    - main
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any
    
    environment {
        WEBHOOK_SECRET = credentials('blt-webhook-secret')
        PROJECT_SLUG = 'my-project'
    }
    
    stages {
        stage('Deploy') {
            steps {
                // Your deployment steps
            }
        }
        
        stage('Trigger BLT Webhook') {
            steps {
                script {
                    def payload = """{"event":"deployment","job":"${env.JOB_NAME}","build":"${env.BUILD_NUMBER}"}"""
                    
                    sh """
                        SIGNATURE=\$(echo -n '${payload}' | openssl dgst -sha256 -hmac '${WEBHOOK_SECRET}' | sed 's/^.* //')
                        
                        curl -X POST 'https://blt.owasp.org/project/${PROJECT_SLUG}/webhook/' \\
                            -H 'Content-Type: application/json' \\
                            -H "X-Webhook-Signature: sha256=\$SIGNATURE" \\
                            -d '${payload}'
                    """
                }
            }
        }
    }
}
```

## Security Considerations

1. **Keep Your Secret Key Safe**
   - Never commit webhook secrets to version control
   - Use environment variables or secure secret management systems
   - Rotate secrets periodically

2. **Use HTTPS**
   - Always use HTTPS for webhook endpoints in production
   - Never send webhook secrets over unencrypted connections

3. **Validate Signatures**
   - The webhook endpoint always validates signatures
   - Rejected requests are logged for security monitoring

4. **Monitor Webhook Activity**
   - Check logs for failed webhook attempts
   - Look for patterns of invalid signature attempts
   - Set up alerts for repeated failures

## Troubleshooting

### Common Issues

**Problem: 401 Unauthorized - Missing webhook signature**
- Solution: Ensure you're including the `X-Webhook-Signature` header in your request

**Problem: 403 Forbidden - Invalid webhook signature**
- Solution: Verify that:
  - You're using the correct webhook secret
  - The signature is calculated correctly
  - The payload matches exactly (including whitespace)

**Problem: 404 Not Found - Project not found**
- Solution: Check that:
  - The project slug is correct
  - The project exists in BLT
  - The URL is formatted correctly

**Problem: Webhook succeeds but stats don't update**
- Solution: Check that:
  - The project has repositories associated with it
  - The repositories have valid GitHub URLs
  - GitHub API rate limits haven't been exceeded

### Debug Mode

To debug webhook issues, check the server logs for entries containing:
- "Webhook received for project"
- "Updating contributor stats for repo"
- "Webhook processing completed"

## API Rate Limits

The webhook triggers GitHub API calls to recalculate contributor statistics. Be aware of:

- **GitHub API Rate Limits**: 5,000 requests per hour for authenticated requests
- **Recommendation**: Don't trigger webhooks more frequently than every 15 minutes
- **Best Practice**: Trigger webhooks only when meaningful changes occur (e.g., after deployments, major updates)

## Support

For issues or questions about the webhook feature:
- Open an issue on the [BLT GitHub repository](https://github.com/OWASP-BLT/BLT)
- Contact the BLT team via the OWASP Slack channel

## Related Documentation

- [Project Management](/docs/features.md#project-management)
- [GitHub Integration](/docs/features.md#github-integration)
- [API Documentation](/swagger/)
