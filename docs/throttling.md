# Website Throttling Configuration

This documentation explains the throttling configuration applied to the BLT website.

## Rate Limits

The website implements rate limiting to prevent abuse and ensure fair usage of resources. Different rate limits are applied based on user types:

| User Type | Production Rate Limit | Debug/Testing Rate Limit |
|-----------|----------------------|--------------------------|
| Anonymous | 100 requests/minute   | 1000 requests/minute     |
| Authenticated | 300 requests/minute | 3000 requests/minute    |
| Staff/Admin | 1000 requests/minute | 10000 requests/minute   |

## Implementation Details

The throttling is implemented using the `django-ratelimit` package with a custom middleware that applies to all website requests.

- The middleware is defined in `blt/middleware/throttling.py`
- Rate limit settings are configured in `blt/settings.py`
- Admin URLs are exempt from throttling
- When a rate limit is exceeded, a 429 Too Many Requests response is returned

## Configuration Settings

The following settings can be configured in `settings.py`:

```python
# Rate limit settings
RATELIMIT_RATE_ANON = '100/minute'    # Rate limit for anonymous users
RATELIMIT_RATE_USER = '300/minute'    # Rate limit for authenticated users
RATELIMIT_RATE_STAFF = '1000/minute'  # Rate limit for staff/admin users
RATELIMIT_BLOCK = True                # Whether to block requests that exceed the rate limit
RATELIMIT_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']  # HTTP methods to throttle
```

## REST API Throttling

In addition to the global website throttling, the REST API has its own throttling configuration using Django REST Framework's throttling classes.

API throttling rates are defined in `settings.py`:

```python
REST_FRAMEWORK = {
    # ... other settings ...
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",    # Rate limit for anonymous API users
        "user": "1000/day",   # Rate limit for authenticated API users
    },
}
```