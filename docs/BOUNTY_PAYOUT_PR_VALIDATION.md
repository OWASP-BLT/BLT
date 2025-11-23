# Bounty Payout PR Validation Guide

## Overview

This document provides guidance on finding and validating PRs that implement automatic bounty payout functionality using GitHub Sponsors. It specifically references **PR #4633**, which implements a create-then-cancel GitHub Sponsors subscription approach for one-time bounty payments.

## Background

### The Problem

GitHub Sponsors API does not currently support one-time payments directly. The `oneTimePayment` mutation that existed in the GraphQL API is broken (see [GitHub Community Discussion #138161](https://github.com/orgs/community/discussions/138161)).

### The Solution (PR #4633)

PR #4633 implements a workaround by:
1. Creating a GitHub Sponsors subscription
2. Immediately canceling it
3. Tracking cancellation attempts and failures

This allows for "one-time" payments through the Sponsors platform while preventing recurring charges.

## Key Components of a Valid Bounty Payout Implementation

### 1. GitHub Actions Workflow

**File:** `.github/workflows/auto-bounty-payout.yml`

**Required Features:**
- Triggers on PR close/merge events
- Extracts linked issues from PR body (using "Fixes #123", "Closes #456", etc.)
- Validates PR is actually merged (not just closed)
- Calls bounty payout API endpoint for each linked issue
- Posts results as comments on the issue

**Critical Checks:**
```yaml
if: github.event.pull_request.merged == true
```

### 2. API Endpoint

**File:** `website/views/organization.py`

**Function:** `process_bounty_payout(request)`

**Required Features:**
- CSRF exempt (called by GitHub Actions)
- API token authentication
- Validates issue has bounty label
- Checks assignee exists and has BLT account
- Prevents duplicate payments
- **Creates GitHub Sponsors subscription**
- **Immediately attempts to cancel the subscription**
- Records transaction ID and cancellation status
- Returns detailed success/failure response

**Critical Security Features:**
- Repository allowlist (`BLT_ALLOWED_BOUNTY_REPOS`)
- Duplicate payment prevention
- Input validation
- Proper error handling

### 3. Database Models

**Required Fields on `GitHubIssue` model:**

```python
# Existing field
sponsors_tx_id = models.CharField(max_length=255, null=True, blank=True)

# New fields for cancellation tracking
sponsors_cancellation_failed = models.BooleanField(default=False)
sponsors_cancellation_attempts = models.IntegerField(default=0)
sponsors_cancellation_last_attempt = models.DateTimeField(null=True, blank=True)
```

**Required Fields on `UserProfile` model:**

```python
preferred_payment_method = models.CharField(
    max_length=20,
    choices=[('sponsors', 'GitHub Sponsors'), ('bch', 'Bitcoin Cash')],
    default='sponsors',
    null=True,
    blank=True
)
```

### 4. GitHub GraphQL Mutations

**Create Sponsorship:**
```graphql
mutation($sponsorableId: ID!, $amount: Int!) {
  createSponsorship(input: {
    sponsorLogin: "DonnieBLT",
    sponsorableId: $sponsorableId,
    amount: $amount,
    isRecurring: false
  }) {
    sponsorship {
      id
    }
  }
}
```

**Cancel Sponsorship:**
```graphql
mutation($sponsorshipId: ID!) {
  cancelSponsorship(input: {
    sponsorshipId: $sponsorshipId
  }) {
    sponsorship {
      id
    }
  }
}
```

### 5. Configuration

**Environment Variables:**

```bash
# API authentication
BLT_API_TOKEN=your_secret_token

# GitHub Sponsors configuration
GITHUB_SPONSOR_USERNAME=DonnieBLT
GITHUB_TOKEN=ghp_your_github_token_with_sponsors_scope

# Repository allowlist
BLT_ALLOWED_BOUNTY_REPO_1=OWASP-BLT/BLT
BLT_ALLOWED_BOUNTY_REPO_2=OWASP-BLT/BLT-Extension
BLT_ALLOWED_BOUNTY_REPO_3=OWASP-BLT/BLT-Flutter
```

## Validation Checklist

Use this checklist when reviewing a bounty payout PR:

### ✅ Must Have (Critical)

- [ ] GitHub Actions workflow exists and triggers on PR merge
- [ ] API endpoint exists with proper authentication
- [ ] **Sponsors cancellation logic is implemented**
- [ ] Database migrations for new fields
- [ ] Repository allowlist to prevent unauthorized payouts
- [ ] Duplicate payment prevention
- [ ] Error handling for API failures
- [ ] Logging for debugging

### ⚠️ Should Have (Important)

- [ ] Retry logic for failed cancellations
- [ ] Admin interface fields for monitoring
- [ ] Cancellation attempt tracking
- [ ] Documentation updates
- [ ] Environment variable examples
- [ ] Security validation (no secrets in code)

### 💡 Nice to Have (Enhancement)

- [ ] Automated tests for the workflow
- [ ] Monitoring/alerting for failed cancellations
- [ ] Dashboard for payment status
- [ ] Support for multiple payment methods
- [ ] Rate limiting on API endpoint

## Known Risks and Mitigation

### Risk 1: Cancellation Failure

**Problem:** If cancellation fails, the user will be charged monthly.

**Mitigation in PR #4633:**
- Immediate cancellation attempt after creation
- Retry logic with exponential backoff
- Database tracking of cancellation attempts
- Admin interface to manually review failures
- Email alerts (recommended addition)

### Risk 2: Unauthorized Payouts

**Problem:** Malicious actors could trigger payouts on their own repos.

**Mitigation in PR #4633:**
- Repository allowlist in settings
- API token authentication
- Workflow only runs on trusted repos
- Payment method validation

### Risk 3: Duplicate Payments

**Problem:** Same issue could be paid multiple times.

**Mitigation in PR #4633:**
- Check for existing `sponsors_tx_id` or `bch_tx_id`
- Database unique constraints
- Transaction ID recording

## How to Use the Validation Script

The repository includes a script to automatically find and validate bounty payout PRs:

```bash
# Make the script executable
chmod +x scripts/find_bounty_payout_pr.py

# Run the validation
python scripts/find_bounty_payout_pr.py
```

The script will:
1. Search for PR #4633 (or other bounty payout PRs)
2. Validate the implementation against the checklist
3. Report critical issues, warnings, and recommendations
4. Provide an overall assessment

## Current Status of PR #4633

As of the last check:

- **State:** Open (not merged)
- **Has merge conflicts:** Yes
- **Implementation status:**
  - ✅ GitHub Actions workflow
  - ✅ API endpoint with authentication
  - ✅ Sponsors create/cancel logic
  - ✅ Database migrations
  - ✅ Repository allowlist
  - ✅ Error handling and retry logic
  - ✅ Cancellation tracking fields
  - ❌ Needs conflict resolution

## Recommendations for Merging

Before merging PR #4633, ensure:

1. **Resolve merge conflicts** with main branch
2. **Test the workflow** in a safe environment:
   - Use a test repository
   - Use a test GitHub Sponsors account
   - Verify cancellation works correctly
3. **Configure environment variables** in production:
   - Set `BLT_API_TOKEN`
   - Set `GITHUB_TOKEN` with sponsors scope
   - Configure repository allowlist
4. **Set up monitoring**:
   - Alert on cancellation failures
   - Monitor `sponsors_cancellation_failed` field
   - Review failed payments weekly
5. **Document the process** for maintainers
6. **Create a rollback plan** in case of issues

## Alternative Approaches

If the create-then-cancel approach proves unreliable, consider:

1. **Manual Payment Processing:**
   - Keep automation for detection
   - Manual approval before payment
   - Lower risk, higher effort

2. **Bitcoin Cash Only:**
   - Remove GitHub Sponsors integration
   - Use only BCH payments
   - Simpler, but fewer users have BCH

3. **Wait for GitHub API Fix:**
   - Monitor the GitHub issue
   - Use placeholder tracking
   - No risk, but indefinite wait

## References

- PR #4633: https://github.com/OWASP-BLT/BLT/pull/4633
- GitHub Sponsors API Issue: https://github.com/orgs/community/discussions/138161
- GitHub GraphQL API Docs: https://docs.github.com/en/graphql
- Django CSRF Exemption: https://docs.djangoproject.com/en/stable/ref/csrf/

## Questions or Issues?

If you have questions about this implementation or find issues:

1. Comment on PR #4633
2. Open a new issue with the `bounty` label
3. Contact the maintainers in Discord

---

**Last Updated:** 2025-11-23  
**Maintained by:** OWASP BLT Team
