# Bug Review Queue

## Overview

The Bug Review Queue is a moderation system that automatically flags bug reports from new users for review before they are publicly visible. This helps maintain quality and prevent spam.

By default, accounts less than 7 days old have their bug reports auto-hidden, but this threshold is configurable.

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Number of days after account creation during which bug reports are auto-hidden
BUG_REVIEW_QUEUE_NEW_USER_DAYS=7  # Default is 7 days
```

## How It Works

### For New Users
When a user who joined within the configured threshold (default: 7 days) submits a bug report:
1. The bug is automatically marked as `is_hidden=True`
2. The bug is not visible to the public
3. The bug appears in the Review Queue for verification

### For Bug Verifiers
Users with the "Bug Verifiers" permission can:
1. Access the review queue at `/bug-review-queue/`
2. Review pending bug reports
3. Approve bugs (makes them publicly visible)
4. Reject bugs (deletes them)

## Setup

### Adding Bug Verifiers

#### Via Django Admin:
1. Navigate to the Django admin panel (`/admin/`)
2. Go to **Authentication and Authorization** → **Users**
3. Select the user you want to make a verifier
4. Scroll to **Groups** section
5. Add the user to the **"Bug Verifiers"** group
6. Save the user

#### Via Django Shell:
```python
from django.contrib.auth.models import User, Group

# Get the user
user = User.objects.get(username='username')

# Get the Bug Verifiers group
bug_verifier_group = Group.objects.get(name='Bug Verifiers')

# Add user to group
user.groups.add(bug_verifier_group)
```

### Running Migrations
The Bug Verifiers group and permission are created automatically when you run:
```bash
python manage.py migrate
```

## Admin Features

### Django Admin Panel
The Issue admin panel (`/admin/website/issue/`) includes:
- **is_hidden** column in the issue list
- **is_hidden** filter to show only hidden issues
- Bulk action: "Approve and publish selected hidden bugs"

### Quick Actions
1. Filter hidden issues: Select "Yes" in the "is_hidden" filter
2. Select issues to approve
3. Choose "Approve and publish selected hidden bugs" from the action dropdown
4. Click "Go"

## Review Queue Interface

### Accessing the Queue
Navigate to: `/bug-review-queue/`

### Features
- **Pagination**: View 20 bugs per page
- **User Information**: See submitter details and account age
- **Full Bug Details**: View description, screenshots, and metadata
- **Quick Actions**:
  - **Approve & Publish**: Makes the bug publicly visible
  - **Reject**: Deletes the bug report

### Permissions Required
Users must have the `website.can_verify_bugs` permission to access the review queue.

## API and Integration

### Checking if a Bug Needs Review
```python
from website.models import Issue
from django.utils import timezone
from datetime import timedelta

# Check if an issue is hidden
issue = Issue.objects.get(id=123)
needs_review = issue.is_hidden

# Check if a user's bugs would be auto-hidden
user_age = timezone.now() - user.date_joined
is_new_user = user_age.days < 7
```

### Programmatically Approving Bugs
```python
from website.models import Issue

# Approve a single bug
issue = Issue.objects.get(id=123)
issue.is_hidden = False
issue.save()

# Bulk approve bugs
Issue.objects.filter(is_hidden=True).update(is_hidden=False)
```

## Testing

Run the bug review queue tests:
```bash
python manage.py test website.tests.test_bug_review_queue
```

## Security Considerations

- Only users with explicit permission can access the review queue
- Regular users cannot see hidden bugs (except their own)
- Hidden bugs are excluded from public listings and searches
- The 7-day threshold prevents abuse from account creation spam

## Future Enhancements

Potential improvements to consider:
- Email notifications to verifiers when new bugs need review
- Configurable time threshold (instead of hardcoded 7 days)
- Review statistics and metrics dashboard
- Automatic approval after multiple positive reviews
- Machine learning-based spam detection
