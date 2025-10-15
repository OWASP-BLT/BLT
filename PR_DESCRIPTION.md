Fixes #3941

## Summary

This PR implements automatic bounty payment processing when a pull request is merged that closes an issue with a bounty label. The system detects merged PRs, extracts linked issues, verifies bounty labels, and initiates payment through the GitHub Sponsors API.

## Changes

### Database
- Added `preferred_payment_method` field to UserProfile model to store user's payment preference (GitHub Sponsors or Bitcoin Cash)
- Created migration `0247_userprofile_preferred_payment_method.py`

### Backend API
- Created new endpoint `/api/bounty_payout/` in `website/views/organization.py`
- Accepts POST requests with issue URL and optional PR URL
- Validates issue has bounty label and assignee
- Checks if user exists in BLT with linked GitHub account
- Prevents duplicate payments by checking existing transaction IDs
- Returns appropriate error messages for various failure cases
- Added optional authentication via `X-BLT-API-TOKEN` header
- Added URL route in `blt/urls.py`

### GitHub Actions
- Created workflow `.github/workflows/auto-bounty-payout.yml`
- Triggers when PR is merged (not just closed)
- Extracts linked issues from PR body using regex patterns
- Checks each issue for dollar-amount labels ($5, $10, etc.)
- Calls BLT API endpoint with issue details
- Posts comment on issue confirming payment initiation or reporting errors

## Implementation Details

The workflow looks for PR descriptions containing "Fixes #123", "Closes #456", or "Resolves #789" patterns to identify linked issues. For each linked issue with a bounty label, it makes an API call to process the payment.

The API endpoint validates the request, fetches issue details from GitHub, verifies the assignee has a BLT account with connected GitHub profile, checks their payment preference, and records the transaction. Currently uses placeholder transaction IDs pending full GitHub Sponsors GraphQL API integration.

## Improvements Over Previous Attempt (PR #4236)

Based on CodeRabbit's review of the previous implementation, this version addresses several critical issues:
- Uses curl for API calls instead of github.request() which only works for GitHub's own API
- Properly reads authentication headers using request.headers.get() instead of making HTTP requests
- No duplicate class definitions
- Consistent data types throughout
- Correct migration dependencies
- Added duplicate payment prevention

## Known Limitations

- GitHub Sponsors API integration uses placeholder transaction IDs. Full GraphQL API implementation will be added in future work.
- Only GitHub Sponsors payment method is currently implemented. Bitcoin Cash support is planned.
- Requires BLT_API_TOKEN to be configured in settings and GitHub repository secrets.
- Workflow API URL needs to be updated to production URL before deployment.

## Testing

All Python files compile without syntax errors. Migration dependency has been verified against latest migration (0246). Error handling covers all expected failure cases including missing assignee, invalid issue URL, user not found, and duplicate payments.

Manual testing required after deployment to verify end-to-end workflow.

## Deployment Notes

1. Run migration: `python manage.py migrate`
2. Add BLT_API_TOKEN to Django settings
3. Add BLT_API_TOKEN to GitHub repository secrets
4. Update API URL in workflow file (line 74) to production URL
5. Restart application server

This is my first contribution to the project. I've tried to follow the existing code patterns and address feedback from previous attempts. Happy to make any changes based on review feedback.
