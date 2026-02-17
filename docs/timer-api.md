# Timer API Documentation

Complete API documentation for the automated timer system for GitHub issue tracking.

## Table of Contents

- [Authentication](#authentication)
- [Endpoints](#endpoints)
- [Models](#models)
- [Webhooks](#webhooks)
- [Examples](#examples)
- [Error Handling](#error-handling)

## Authentication

All API endpoints require authentication using one of the following methods:

### Token Authentication
```bash
Authorization: Token YOUR_API_TOKEN
```

### Session Authentication
Use Django session cookies (for web interface).

## Endpoints

### List Timers

Get a list of timers for the authenticated user.

**Endpoint:** `GET /api/timelogs/`

**Query Parameters:**
- `end_time__isnull=true` - Get only active timers
- `github_issue_number=123` - Filter by issue number
- `github_repo=owner/repo` - Filter by repository

**Response:**
```json
{
  "count": 10,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "user": 1,
      "organization": null,
      "start_time": "2024-01-15T10:00:00Z",
      "end_time": null,
      "duration": null,
      "github_issue_url": "https://github.com/owner/repo/issues/123",
      "github_issue_number": 123,
      "github_repo": "owner/repo",
      "is_paused": false,
      "paused_duration": null,
      "last_pause_time": null,
      "active_duration": 3600.5,
      "created": "2024-01-15T10:00:00Z"
    }
  ]
}
```

### Get Timer Details

Get details of a specific timer.

**Endpoint:** `GET /api/timelogs/{id}/`

**Response:** Same as single timer object above.

### Start Timer

Start a new timer.

**Endpoint:** `POST /api/timelogs/start/`

**Request Body:**
```json
{
  "github_issue_url": "https://github.com/owner/repo/issues/123",
  "github_issue_number": 123,
  "github_repo": "owner/repo",
  "organization_url": "https://example.com"
}
```

**Note:** All fields are optional. If `organization_url` is provided, the timer will be associated with that organization.

**Response:** `201 Created`
```json
{
  "id": 1,
  "user": 1,
  "organization": 1,
  "start_time": "2024-01-15T10:00:00Z",
  "end_time": null,
  "duration": null,
  "github_issue_url": "https://github.com/owner/repo/issues/123",
  "github_issue_number": 123,
  "github_repo": "owner/repo",
  "is_paused": false,
  "paused_duration": null,
  "last_pause_time": null,
  "active_duration": 0,
  "created": "2024-01-15T10:00:00Z"
}
```

### Stop Timer

Stop an active timer.

**Endpoint:** `POST /api/timelogs/{id}/stop/`

**Response:** `200 OK`
```json
{
  "id": 1,
  "user": 1,
  "organization": 1,
  "start_time": "2024-01-15T10:00:00Z",
  "end_time": "2024-01-15T11:30:00Z",
  "duration": "1:30:00",
  "github_issue_url": "https://github.com/owner/repo/issues/123",
  "github_issue_number": 123,
  "github_repo": "owner/repo",
  "is_paused": false,
  "paused_duration": "0:15:00",
  "last_pause_time": null,
  "active_duration": 4500,
  "created": "2024-01-15T10:00:00Z"
}
```

### Pause Timer

Pause an active timer.

**Endpoint:** `POST /api/timelogs/{id}/pause/`

**Response:** `200 OK`
```json
{
  "id": 1,
  "user": 1,
  "start_time": "2024-01-15T10:00:00Z",
  "end_time": null,
  "is_paused": true,
  "last_pause_time": "2024-01-15T10:30:00Z",
  ...
}
```

**Error Responses:**
- `400 Bad Request` - Timer already paused or already completed
- `403 Forbidden` - User doesn't own this timer
- `404 Not Found` - Timer doesn't exist

### Resume Timer

Resume a paused timer.

**Endpoint:** `POST /api/timelogs/{id}/resume/`

**Response:** `200 OK`
```json
{
  "id": 1,
  "user": 1,
  "start_time": "2024-01-15T10:00:00Z",
  "end_time": null,
  "is_paused": false,
  "paused_duration": "0:15:00",
  "last_pause_time": null,
  ...
}
```

**Error Responses:**
- `400 Bad Request` - Timer not paused or already completed
- `403 Forbidden` - User doesn't own this timer
- `404 Not Found` - Timer doesn't exist

### Update Timer

Update timer details.

**Endpoint:** `PATCH /api/timelogs/{id}/`

**Request Body:**
```json
{
  "github_issue_url": "https://github.com/owner/repo/issues/456",
  "github_issue_number": 456
}
```

**Response:** `200 OK` with updated timer object.

### Delete Timer

Delete a timer.

**Endpoint:** `DELETE /api/timelogs/{id}/`

**Response:** `204 No Content`

## Models

### TimeLog

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| user | ForeignKey | User who owns the timer |
| organization | ForeignKey | Associated organization (optional) |
| start_time | DateTime | When timer started |
| end_time | DateTime | When timer stopped (null if active) |
| duration | Duration | Total duration (end_time - start_time - paused_duration) |
| github_issue_url | URL | Full GitHub issue URL |
| github_issue_number | Integer | GitHub issue number |
| github_repo | String | Repository in owner/repo format |
| is_paused | Boolean | Whether timer is currently paused |
| paused_duration | Duration | Total time spent paused |
| last_pause_time | DateTime | When timer was last paused |
| created | DateTime | When record was created |

### Computed Fields

| Field | Type | Description |
|-------|------|-------------|
| active_duration | Float | Current active duration in seconds (excludes paused time) |

## Webhooks

### GitHub Timer Webhook

Endpoint for receiving GitHub events to automatically manage timers.

**Endpoint:** `POST /api/github-timer-webhook/`

**Headers:**
- `X-GitHub-Event: issues` or `X-GitHub-Event: project_v2_item`
- `X-Hub-Signature-256: sha256=<hmac_signature>` (Required for security)
- `Content-Type: application/json`

**Security:**

This endpoint requires HMAC-SHA256 signature verification to prevent unauthorized requests.

1. Configure `GITHUB_WEBHOOK_SECRET` in your Django settings
2. GitHub will send the signature in the `X-Hub-Signature-256` header
3. The signature is computed as: `sha256=` + HMAC-SHA256(secret, raw_request_body)
4. Requests with missing or invalid signatures will receive HTTP 401 Unauthorized

**Supported Events:**

#### Issue Assigned
```json
{
  "action": "assigned",
  "issue": {
    "number": 123,
    "html_url": "https://github.com/owner/repo/issues/123"
  },
  "assignee": {
    "login": "username"
  },
  "repository": {
    "full_name": "owner/repo"
  }
}
```

**Action:** Starts a timer for the assigned user.

#### Issue Closed
```json
{
  "action": "closed",
  "issue": {
    "number": 123,
    "html_url": "https://github.com/owner/repo/issues/123"
  },
  "repository": {
    "full_name": "owner/repo"
  }
}
```

**Action:** Stops all active timers for this issue.

#### Issue Unassigned
```json
{
  "action": "unassigned",
  "issue": {
    "number": 123,
    "html_url": "https://github.com/owner/repo/issues/123"
  },
  "repository": {
    "full_name": "owner/repo"
  }
}
```

**Action:** Pauses all active timers for this issue.

## Examples

### Start a Timer with cURL

```bash
curl -X POST https://your-blt-instance.com/api/timelogs/start/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "github_issue_url": "https://github.com/owner/repo/issues/123",
    "github_issue_number": 123,
    "github_repo": "owner/repo"
  }'
```

### Get Active Timers

```bash
curl https://your-blt-instance.com/api/timelogs/?end_time__isnull=true \
  -H "Authorization: Token YOUR_API_TOKEN"
```

### Pause a Timer

```bash
curl -X POST https://your-blt-instance.com/api/timelogs/1/pause/ \
  -H "Authorization: Token YOUR_API_TOKEN"
```

### Python Example

```python
import requests

API_URL = "https://your-blt-instance.com/api/timelogs"
TOKEN = "YOUR_API_TOKEN"

headers = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

# Start timer
response = requests.post(
    f"{API_URL}/start/",
    headers=headers,
    json={
        "github_issue_url": "https://github.com/owner/repo/issues/123",
        "github_issue_number": 123,
        "github_repo": "owner/repo"
    }
)
timer = response.json()
timer_id = timer["id"]

# Pause timer
requests.post(f"{API_URL}/{timer_id}/pause/", headers=headers)

# Resume timer
requests.post(f"{API_URL}/{timer_id}/resume/", headers=headers)

# Stop timer
response = requests.post(f"{API_URL}/{timer_id}/stop/", headers=headers)
final_timer = response.json()
print(f"Duration: {final_timer['duration']}")
```

### JavaScript Example

```javascript
const API_URL = 'https://your-blt-instance.com/api/timelogs';
const TOKEN = 'YOUR_API_TOKEN';

const headers = {
    'Authorization': `Token ${TOKEN}`,
    'Content-Type': 'application/json'
};

// Start timer
const response = await fetch(`${API_URL}/start/`, {
    method: 'POST',
    headers: headers,
    body: JSON.stringify({
        github_issue_url: 'https://github.com/owner/repo/issues/123',
        github_issue_number: 123,
        github_repo: 'owner/repo'
    })
});

const timer = await response.json();
const timerId = timer.id;

// Pause timer
await fetch(`${API_URL}/${timerId}/pause/`, {
    method: 'POST',
    headers: headers
});

// Resume timer
await fetch(`${API_URL}/${timerId}/resume/`, {
    method: 'POST',
    headers: headers
});

// Stop timer
const stopResponse = await fetch(`${API_URL}/${timerId}/stop/`, {
    method: 'POST',
    headers: headers
});

const finalTimer = await stopResponse.json();
console.log(`Duration: ${finalTimer.duration}`);
```

## Error Handling

### Common Error Responses

#### 400 Bad Request
```json
{
  "detail": "Cannot pause a completed time log."
}
```

#### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

#### 403 Forbidden
```json
{
  "detail": "You don't have permission to pause this time log."
}
```

#### 404 Not Found
```json
{
  "detail": "Time log not found."
}
```

#### 500 Internal Server Error
```json
{
  "detail": "An unexpected error occurred while starting the time log."
}
```

### Best Practices

1. **Always check response status codes** before processing data
2. **Handle network errors** gracefully with try-catch blocks
3. **Validate timer state** before performing actions (check `is_paused`, `end_time`)
4. **Use active_duration** for real-time display instead of calculating manually
5. **Store timer_id** locally to avoid repeated API calls
6. **Implement retry logic** for failed requests
7. **Cache active timer** to reduce API calls

### Rate Limiting

The API implements method-based rate limiting to prevent abuse:
- **GET requests:** 100 requests per minute
- **POST requests:** 50 requests per minute  
- **Other methods (PUT, PATCH, DELETE):** 30 requests per minute

Rate limits are applied uniformly regardless of authentication status.

If you exceed the rate limit, you'll receive a `429 Too Many Requests` response.

## Support

For issues or questions:
- GitHub Issues: https://github.com/OWASP-BLT/BLT/issues
- Documentation: https://github.com/OWASP-BLT/BLT/tree/main/docs
