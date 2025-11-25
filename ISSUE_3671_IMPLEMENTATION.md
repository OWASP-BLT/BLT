# Issue #3671: Link GitHub Issue on Bug Card

## Summary
Added GitHub integration to bug cards to display:
- Clickable GitHub issue link
- Issue state (open/closed) with color-coded badge
- Comment count

## Changes Made

### 1. Database Model (`website/models.py`)
- Added `github_state` field (CharField, max 10 chars) to store issue state
- Added `github_comment_count` field (IntegerField, default 0) to store comment count
- Added `fetch_github_data()` method to fetch and cache GitHub data via API

### 2. Template (`website/templates/includes/_bug.html`)
- Added conditional GitHub information section that displays when `bug.github_url` exists
- GitHub link with icon (opens in new tab)
- Status badge (green for open, red for closed) with proper dark mode support
- Comment count with icon
- All styling uses Tailwind CSS classes (no inline styles)

### 3. Migration (`website/migrations/0256_add_github_fields_to_issue.py`)
- Auto-generated migration to add the two new fields to the Issue model

## How It Works

1. **Data Storage**: GitHub state and comment count are cached in the database to avoid excessive API calls
2. **Data Fetching**: Call `issue.fetch_github_data()` to update GitHub information from the API
3. **Display**: Bug cards automatically show GitHub info when `github_url` is present

## Usage

### Update GitHub data for an issue:
```python
issue = Issue.objects.get(id=123)
issue.fetch_github_data()  # Fetches and saves latest GitHub data
```

### Display on template:
The template automatically shows GitHub information if `bug.github_url` is set. No additional changes needed.

## Testing

1. Run migrations:
   ```bash
   docker-compose exec app python manage.py migrate
   ```

2. Update existing issues with GitHub URLs:
   ```bash
   docker-compose exec app python manage.py shell
   >>> from website.models import Issue
   >>> for issue in Issue.objects.exclude(github_url=''):
   ...     issue.fetch_github_data()
   ```

3. View any bug list page to see the GitHub information displayed on bug cards

## Code Quality
- ✅ Black formatting passed
- ✅ isort import sorting passed  
- ✅ ruff linting passed
- ✅ Follows project's Tailwind-only CSS guideline
- ✅ No inline JavaScript added
- ✅ Minimal changes to existing code

## Notes
- GitHub API rate limit: 60 requests/hour without token, 5000/hour with token
- Ensure `GITHUB_TOKEN` is set in environment variables for higher rate limits
- The `fetch_github_data()` method gracefully handles errors and logs warnings
