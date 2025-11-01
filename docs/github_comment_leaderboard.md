# GitHub Comment Leaderboard

## Overview

The GitHub Comment Leaderboard tracks and displays users with the most comments on GitHub issues, pull requests, and discussions. This feature helps recognize community members who actively engage in discussions and provide feedback.

## Features

- **Comment Tracking**: Tracks comments from GitHub issues, PRs, and discussions
- **Leaderboard Display**: Shows top commenters with their comment counts
- **User Association**: Links comments to BLT user profiles when possible
- **Repository Support**: Supports tracking across multiple repositories
- **API Access**: Provides API endpoints for programmatic access

## Database Model

The `GitHubComment` model stores comment data with the following fields:

- `comment_id`: Unique GitHub comment ID
- `user_profile`: Link to BLT UserProfile (if available)
- `contributor`: Link to Contributor (if no UserProfile)
- `body`: Comment text content
- `comment_type`: Type of comment (issue/pull_request/discussion)
- `created_at`: Comment creation timestamp
- `updated_at`: Comment last update timestamp
- `url`: GitHub URL to the comment
- `repo`: Associated repository
- `github_issue`: Associated GitHubIssue (if available)

## Management Command

### Fetching Comment Data

Use the `fetch_github_comments` management command to populate comment data from GitHub:

```bash
# Fetch comments for the default BLT repository
python manage.py fetch_github_comments

# Fetch comments for a specific repository
python manage.py fetch_github_comments --repo owner/repository

# Fetch comments from all repositories in the database
python manage.py fetch_github_comments --all-repos
```

**Note**: This command requires the `GITHUB_TOKEN` setting to be configured for GitHub API access.

### Rate Limiting

The command includes built-in rate limiting to respect GitHub API limits:
- 0.5 second delay between issue/PR fetches
- 0.3 second delay between comment page fetches

## Viewing the Leaderboard

### Web Interface

The GitHub Comment Leaderboard is displayed on the global leaderboard page at `/leaderboard/`.

The leaderboard shows:
- User's avatar and username
- Link to user's profile
- GitHub icon linking to their GitHub profile
- Total comment count

### API Access

Access comment leaderboard data via the API:

```bash
# Get GitHub comment leaderboard
GET /api/v1/leaderboard/?leaderboard_type=github_comments
```

Response format:
```json
{
  "count": 100,
  "next": "...",
  "previous": null,
  "results": [
    {
      "user_profile__user__id": 1,
      "user_profile__user__username": "example_user",
      "user_profile__user__email": "user@example.com",
      "user_profile__github_url": "https://github.com/example_user",
      "total_comments": 150
    }
  ]
}
```

## Admin Interface

The GitHubComment model is registered in the Django admin interface with:

- List display: ID, comment_id, user_profile, contributor, comment_type, created_at, repo
- Filters: comment_type, created_at, repo
- Search: username, contributor name, body, URL
- Date hierarchy: created_at

## Expanding to More Repositories

### Adding New Repositories

To track comments from additional repositories:

1. Add the repository to the `Repo` model in the database
2. Run the fetch command with `--all-repos` flag

```bash
python manage.py fetch_github_comments --all-repos
```

### Automated Updates

Consider setting up a cron job or scheduled task to periodically fetch new comments:

```bash
# Example cron entry (daily at 2 AM)
0 2 * * * cd /path/to/blt && python manage.py fetch_github_comments --all-repos
```

## Testing

Run the test suite for the GitHub comment leaderboard:

```bash
python manage.py test website.test_github_comment_leaderboard
```

Tests cover:
- Model creation and relationships
- Leaderboard display functionality
- Comment counting accuracy
- Proper ordering by comment count

## Future Enhancements

Potential improvements for future development:

1. **Discussion Comments**: Add support for GitHub Discussions API
2. **Real-time Updates**: Implement webhooks for real-time comment tracking
3. **Filtering Options**: Add filters by time period, repository, or comment type
4. **Comment Quality Metrics**: Track helpful reactions, replies, etc.
5. **Notification System**: Alert users when they reach comment milestones

## Troubleshooting

### No Data Showing

If the leaderboard is empty:
1. Verify `GITHUB_TOKEN` is configured in settings
2. Run the fetch command: `python manage.py fetch_github_comments`
3. Check for errors in the command output
4. Verify repositories exist in the Repo model

### API Rate Limits

If you encounter GitHub API rate limits:
1. Check your token's rate limit status
2. Increase delays in the fetch command
3. Use a GitHub token with higher rate limits
4. Schedule fetches during low-traffic periods

## Related Models

- `GitHubIssue`: Stores GitHub issues and PRs
- `GitHubReview`: Stores PR review data
- `UserProfile`: BLT user profiles
- `Contributor`: GitHub contributors
- `Repo`: Repository information
