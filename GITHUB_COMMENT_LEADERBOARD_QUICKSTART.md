# GitHub Comment Leaderboard - Quick Start

## What This Feature Does

This feature adds a leaderboard that shows users with the most comments on GitHub issues, PRs, and discussions. It starts with the BLT repository and can be expanded to all repositories in the projects section.

## How to Use

### 1. Set Up GitHub Token

Make sure your `.env` file has a GitHub token configured:

```bash
GITHUB_TOKEN=your_github_token_here
```

### 2. Fetch Comment Data

Run the management command to fetch comment data from GitHub:

```bash
# For BLT repository only (default)
poetry run python manage.py fetch_github_comments

# For all repositories in the database
poetry run python manage.py fetch_github_comments --all-repos
```

### 3. View the Leaderboard

Open your browser and go to:
- **Web**: http://localhost:8000/leaderboard/
- **API**: http://localhost:8000/api/v1/leaderboard/?leaderboard_type=github_comments

## What You'll See

The leaderboard displays:
- User avatar
- Username with link to their profile
- GitHub profile link
- Total number of comments

## Expanding to More Repositories

### Step 1: Add Repository to Database

Make sure the repository is in the `Repo` model. You can add it through:
1. Django admin at `/admin/website/repo/`
2. Or through the project management interface

### Step 2: Fetch Comments

Run the fetch command with the `--all-repos` flag:

```bash
poetry run python manage.py fetch_github_comments --all-repos
```

### Step 3: Schedule Regular Updates

To keep the leaderboard updated, set up a cron job or scheduled task:

```bash
# Example: Update every day at 2 AM
0 2 * * * cd /path/to/blt && poetry run python manage.py fetch_github_comments --all-repos
```

## Troubleshooting

### "No GitHub comment data available!"

This means no comment data has been fetched yet. Run:
```bash
poetry run python manage.py fetch_github_comments
```

### GitHub API Rate Limit Errors

- The fetch command includes rate limiting delays
- Make sure your GitHub token has sufficient rate limits
- Consider running the command during low-traffic hours

### Comments Not Showing for Some Users

Comments are linked to users in two ways:
1. **By UserProfile**: If a BLT user has the same GitHub username
2. **By Contributor**: If the GitHub user is in the Contributor table

To see more users on the leaderboard:
- Encourage users to set their GitHub profile in BLT
- Or run the contributor fetch command first

## Implementation Details

See the full documentation at:
- Technical documentation: `docs/github_comment_leaderboard.md`
- UI/UX documentation: `docs/github_comment_leaderboard_ui.md`

## Testing

Run the test suite:
```bash
poetry run python manage.py test website.test_github_comment_leaderboard
```

## Support

For issues or questions:
1. Check the full documentation
2. Review the management command help: `python manage.py fetch_github_comments --help`
3. Check the Django admin logs for error messages
