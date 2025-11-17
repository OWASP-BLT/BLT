# GNews API Setup Guide

## Overview
The Latest News feature on the Company Cyber Dashboard uses the GNews API to fetch recent news articles about companies. This guide explains how to set up and configure the GNews API integration.

## Prerequisites
- A GNews API account and token
- Access to environment variables or settings configuration

## Getting GNews API Access

1. Visit [GNews.io](https://gnews.io/)
2. Sign up for a free account
3. Navigate to your account dashboard
4. Copy your API token

## Configuration

### Environment Variables
Add your GNews API token to your environment variables:

```bash
export GNEWS_API_TOKEN="your_gnews_api_token_here"
```

### .env File (for local development)
Add the following line to your `.env` file:

```
GNEWS_API_TOKEN=your_gnews_api_token_here
```

### Settings Configuration
The GNews API token is automatically loaded from the environment variable `GNEWS_API_TOKEN` in the Django settings:

```python
# GNews API Configuration
GNEWS_API_TOKEN = os.environ.get("GNEWS_API_TOKEN")
```

## Features

### News Integration
- Fetches 3-5 recent news articles specifically about companies
- Uses targeted search queries with company names in quotes for exact matching
- Includes additional keywords (company, corporation, business, tech) for relevant results
- Displays article titles, descriptions, sources, and publication dates
- Opens articles in new tabs when clicked

### Error Handling
- Graceful handling of API failures
- Rate limit detection and logging
- Timeout protection (10 seconds)
- Fallback content when no news is available

### Performance
- Cached responses to reduce API calls
- Timeout handling to prevent slow page loads
- Detailed logging for debugging

## API Limits
- Free tier: 100 requests per day
- Paid tiers available with higher limits
- Rate limiting: Handled gracefully with appropriate error messages

## Troubleshooting

### No News Displayed
1. Check if `GNEWS_API_TOKEN` is set correctly
2. Verify API token is valid at GNews.io
3. Check Django logs for API errors
4. Ensure company name is suitable for news search

### Common Error Codes
- `401 Unauthorized`: Invalid API token
- `429 Too Many Requests`: Rate limit exceeded
- `Timeout`: Network or API response timeout

## Monitoring
Monitor the Django logs for GNews API related messages:
- Info: Successful API calls and article counts
- Warning: Rate limits and network timeouts
- Error: Authentication failures and unexpected errors

## Security Notes
- Keep your GNews API token secure
- Don't commit tokens to version control
- Use environment variables for production
- Regularly rotate API tokens if needed