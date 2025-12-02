# GitHub Webhook Setup for Issue Synchronization

This guide explains how to set up GitHub webhooks to automatically synchronize issue states between GitHub repositories and the BLT platform.

## Overview

When configured, GitHub will send webhook notifications to BLT whenever issues are opened, closed, or updated. BLT will automatically update the corresponding `GitHubIssue` records to match the state on GitHub.

## Prerequisites

- Admin access to the GitHub repository or organization
- BLT server URL accessible from GitHub's servers
- GitHub webhook endpoint: `https://your-blt-domain.com/github-webhook/`

## Setting Up Webhooks

### For a Single Repository

1. **Navigate to Repository Settings**
   - Go to your GitHub repository
   - Click on **Settings** tab
   - Click on **Webhooks** in the left sidebar
   - Click **Add webhook** button

2. **Configure Webhook**
   - **Payload URL**: `https://your-blt-domain.com/github-webhook/`
   - **Content type**: `application/json`
   - **Secret**: (Optional, but recommended for production)
   - **SSL verification**: Enable SSL verification (recommended)

3. **Select Events**
   - Choose "Let me select individual events"
   - Select the following events:
     - ✅ Issues
     - ✅ Pull requests (if tracking PRs)
     - ✅ Push
     - ✅ Pull request reviews
     - ✅ Statuses
     - ✅ Forks
     - ✅ Create

4. **Activate and Save**
   - Ensure "Active" is checked
   - Click **Add webhook**

### For an Organization (All Repositories)

1. **Navigate to Organization Settings**
   - Go to your GitHub organization
   - Click on **Settings** tab
   - Click on **Webhooks** in the left sidebar
   - Click **Add webhook** button

2. **Configure Webhook** (same as above)
   - Follow the same configuration steps as for a single repository
   - This webhook will apply to all current and future repositories in the organization

## Webhook Behavior

### Issue Events

The webhook responds to the following issue actions:

- **`opened`**: When a new issue is created (logged but not currently updated in BLT)
- **`closed`**: When an issue is closed
  - Updates the `GitHubIssue.state` to "closed"
  - Sets the `GitHubIssue.closed_at` timestamp
  - Assigns "First Issue Closed" badge to the closer (if applicable)
- **`reopened`**: When a closed issue is reopened
  - Updates the `GitHubIssue.state` to "open"
- **`edited`**: When issue details are modified
  - Updates the `GitHubIssue.updated_at` timestamp

### Other Events

The webhook also handles:
- **Pull Request Events**: For tracking PR merges and contributor activity
- **Push Events**: For tracking commits
- **Review Events**: For tracking code reviews
- **Status Events**: For tracking CI build status
- **Fork Events**: For tracking repository forks
- **Create Events**: For tracking branch creation

## How It Works

1. **GitHub sends webhook**: When an issue event occurs, GitHub sends a POST request to the webhook URL
2. **BLT receives event**: The webhook handler extracts issue and repository data
3. **Find repository**: BLT looks up the repository in its database using the repository URL
4. **Find issue**: BLT finds the corresponding `GitHubIssue` record using the issue ID and repository
5. **Update state**: BLT updates the issue state and timestamps
6. **Graceful handling**: If the repository or issue isn't tracked in BLT, the webhook returns success without errors

## Important Notes

### Only Tracked Repositories
- Webhooks only update issues for repositories that exist in BLT's database
- If a repository isn't tracked in BLT, the webhook will log the event but won't create new records
- This is intentional to avoid cluttering the database with untracked issues

### Issue Synchronization
- Issues must first be created in BLT's database (usually through the BLT interface or data sync process)
- The webhook only updates existing `GitHubIssue` records
- New issues on GitHub won't automatically create new records in BLT

### Error Handling
- The webhook returns HTTP 200 even when repositories or issues aren't found
- This prevents GitHub from marking the webhook as failed
- All events are logged for debugging purposes

## Verifying Webhook Setup

After setting up the webhook, you can verify it's working:

1. **Check Recent Deliveries** (in GitHub)
   - Go to your webhook settings
   - Click on the webhook
   - View "Recent Deliveries" tab
   - Look for successful responses (HTTP 200)

2. **Test by Closing an Issue**
   - Close a tracked issue on GitHub
   - Check the BLT database to verify the `GitHubIssue.state` changed to "closed"
   - Check the `closed_at` timestamp was set

3. **Check BLT Logs**
   - Review server logs for webhook events
   - Look for messages like: `Updated GitHubIssue {id} in repo {name} to state: closed`

## Troubleshooting

### Webhook Deliveries Failing

**Problem**: GitHub shows failed deliveries

**Solutions**:
- Verify the webhook URL is correct and accessible
- Check SSL certificate is valid
- Ensure firewall rules allow GitHub's IP ranges
- Check BLT server logs for errors

### Issues Not Updating

**Problem**: Issues aren't syncing between GitHub and BLT

**Solutions**:
- Verify the repository exists in BLT's database with the correct `repo_url`
- Verify the `GitHubIssue` record exists in BLT with the correct `issue_id` and `repo` reference
- Check that the issue `type` is set to "issue" (not "pull_request")
- Review BLT server logs for any error messages

### Webhook Secret Validation

**Note**: The webhook signature validation is currently commented out in the code:

```python
# signature = request.headers.get("X-Hub-Signature-256")
# if not validate_signature(request.body, signature):
#    return JsonResponse({"status": "error", "message": "Unauthorized request"}, status=403)
```

To enable signature validation:
1. Uncomment the validation code in `website/views/user.py`
2. Implement the `validate_signature` function
3. Set up a webhook secret in both GitHub and BLT's configuration

## Security Considerations

1. **Use HTTPS**: Always use HTTPS for the webhook URL
2. **Enable SSL Verification**: Keep SSL verification enabled in GitHub webhook settings
3. **Use Webhook Secrets**: Consider implementing webhook signature validation for production
4. **Restrict IP Ranges**: Consider restricting access to GitHub's webhook IP ranges
5. **Rate Limiting**: Webhook endpoint has built-in rate limiting protection

## Related Documentation

- [GitHub Webhooks Documentation](https://docs.github.com/en/webhooks)
- [BLT Contributing Guide](../CONTRIBUTING.md)
- [BLT Setup Guide](./Setup.md)

## Support

If you encounter issues setting up webhooks:
1. Check the [BLT GitHub Issues](https://github.com/OWASP-BLT/BLT/issues)
2. Review server logs for detailed error messages
3. Create a new issue with details about your problem
