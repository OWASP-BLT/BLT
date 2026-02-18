# GitHub Actions in OWASP BLT

This document provides a comprehensive overview of all GitHub Actions workflows used in the OWASP BLT (Bug Logging Tool) repository. These workflows automate various aspects of repository management, making it easier to maintain code quality, manage contributions, and ensure security—especially important in the age of AI-assisted development.

## Table of Contents

- [Overview](#overview)
- [Why GitHub Actions Matter in the Age of AI](#why-github-actions-matter-in-the-age-of-ai)
- [Workflow Categories](#workflow-categories)
  - [Code Quality & Formatting](#1-code-quality--formatting)
  - [Pull Request Management](#2-pull-request-management)
  - [CI/CD & Testing](#3-cicd--testing)
  - [Security & Analysis](#4-security--analysis)
  - [Issue Management](#5-issue-management)
  - [Automation & Maintenance](#6-automation--maintenance)
- [Best Practices](#best-practices)

## Overview

The OWASP BLT repository uses **29 GitHub Actions workflows** to automate nearly every aspect of the development lifecycle. These workflows help maintain high code quality, manage contributions from a global community, and ensure security best practices are followed.

**Total Workflows**: 29

## Why GitHub Actions Matter in the Age of AI

As AI-powered coding assistants like GitHub Copilot become more prevalent, automated workflows are more critical than ever:

1. **Quality Assurance for AI-Generated Code**: AI tools can generate code quickly, but they may not always follow project-specific conventions. Automated linting and formatting ensure consistency.

2. **Security Validation**: AI-generated code needs extra scrutiny. Automated security scanning (CodeQL) helps catch vulnerabilities before they reach production.

3. **Review Efficiency**: With more PRs being created (often with AI assistance), automated labeling, conflict detection, and status tracking help maintainers prioritize reviews.

4. **Instant Feedback**: Developers using AI tools get immediate feedback on code quality issues, enabling rapid iteration.

5. **Reduced Manual Overhead**: Automation handles repetitive tasks (formatting, labeling, conflict detection), allowing maintainers to focus on architectural decisions and code review.

---

## Workflow Categories

### 1. Code Quality & Formatting

These workflows ensure code meets project standards automatically.

#### 1.1 CI/CD Pipeline (`ci-cd.yml`)
**Purpose**: Main continuous integration and deployment workflow

**Triggers**:
- Pull request events (opened, synchronized, reopened, ready_for_review)
- Push to main branch
- Manual dispatch
- After pre-commit fix workflow completes

**Key Features**:
- **Setup Job**: Caches dependencies (Poetry, pre-commit) for faster runs
- **Pre-commit Checks**: Runs Black, isort, ruff, djLint on all files
- **Django Tests**: Executes full test suite with xvfb for UI testing
- **Docker Tests**: Validates Docker build and container functionality
- **Automated Labeling**: Adds status labels (pre-commit: passed/failed, tests: passed/failed)
- **PR Comments**: Posts detailed feedback when checks fail

**AI Relevance**: Provides instant feedback on AI-generated code quality and test coverage.

#### 1.2 Auto-Fix Pre-Commit on PRs (`auto-fix-pr-precommit.yml`)
**Purpose**: Automatically fix formatting and linting issues on pull requests

**Triggers**:
- Pull request opened, synchronized, or reopened

**Key Features**:
- Runs pre-commit hooks (Black, isort, ruff, djLint)
- Automatically commits and pushes fixes directly to the PR branch
- Handles concurrent commits with retry logic
- Skips if changes are too large (>100 files or >1000 line changes)
- Rate limiting to prevent spam (max 3 auto-fix PRs per hour)
- Verifies fixes by re-running pre-commit after applying them
- Conflict detection to avoid overwriting concurrent changes

**AI Relevance**: AI tools may generate code that doesn't match project formatting. This workflow automatically corrects it, saving developers time.

#### 1.3 Auto-Fix Pre-Commit on Main (`auto-fix-main-precommit.yml`)
**Purpose**: Fix formatting issues when code is pushed directly to main

**Triggers**:
- Push to main branch

**Key Features**:
- Creates a new PR with formatting fixes instead of pushing directly
- Prevents loops by detecting auto-fix commits
- Rate limiting and duplicate PR prevention
- Adds labels: `automated-fix`, `pre-commit`
- Comments on the original commit linking to the fix PR

**AI Relevance**: Catches formatting issues in code merged to main, maintaining consistency even when CI checks are bypassed.

#### 1.4 Pre-Commit Fix (Label-Triggered) (`pre-commit-fix.yaml`)
**Purpose**: Manually trigger pre-commit fixes by adding a label

**Triggers**:
- When `fix-pre-commit` label is added to a PR
- Manual workflow dispatch

**Key Features**:
- Runs pre-commit and commits fixes to the PR branch
- Automatically removes the trigger label after execution
- Comments on PR with list of files modified
- Can be manually triggered by maintainers

**AI Relevance**: Allows maintainers to quickly fix formatting issues in contributor PRs without manual intervention.

#### 1.5 Check Console Statements (`check-console-log.yml`)
**Purpose**: Detect and flag console statements in JavaScript files

**Triggers**:
- Pull request events affecting `.js` files

**Key Features**:
- Scans all JavaScript files for `console.*` statements
- Excludes commented console statements
- Adds `has-console-statements` label
- Posts detailed comment with file locations and line numbers
- Fails the workflow to block merge

**Security**: Prevents console statements that could expose sensitive information or clutter production logs.

**AI Relevance**: AI tools often add console.log for debugging. This workflow catches them before they reach production.

---

### 2. Pull Request Management

These workflows add intelligent metadata and checks to pull requests.

#### 2.1 Add Files Changed Label (`add-files-changed-label.yml`)
**Purpose**: Automatically label PRs based on number of files changed

**Triggers**:
- Pull request opened, synchronized, reopened, ready_for_review, or edited

**Key Features**:
- Counts files changed and adds label: `files-changed: N`
- Color-coded labels:
  - Gray (0 files)
  - Green (1 file)
  - Yellow (2-5 files)
  - Orange (6-10 files)
  - Red (11+ files)
- Automatically removes old labels when count changes

**AI Relevance**: Helps reviewers prioritize PRs—large PRs (often from bulk AI refactoring) get red labels for extra scrutiny.

#### 2.2 Add Comment Count Label (`add-comment-count-label.yml`)
**Purpose**: Track unresolved review conversations on PRs and notify developers

**Triggers**:
- Pull request events (opened, synchronize, reopened, ready_for_review, edited)
- Issue comments (created, edited, deleted)
- Pull request reviews (submitted, edited, dismissed)
- Pull request review comments (created, edited, deleted)
- Pull request review threads (resolved, unresolved)

**Key Features**:
- Counts unresolved, non-outdated conversations using GraphQL pagination
- Adds dynamic label: `unresolved-conversations: N`
- Color-coded by severity:
  - Green (0)
  - Yellow (1-3)
  - Orange (4-10)
  - Red (11+)
- **Posts notification comment** when unresolved conversations are detected
  - Comment provides clear action items for developers
  - Comment is automatically updated when conversation count changes
  - Comment is removed when all conversations are resolved
- Updates in real-time as conversations are resolved or added
- Uses unique marker (`<!-- unresolved-conversations-notification -->`) to manage notification comment
- Uses pagination to reliably find notification comment even on PRs with >100 comments

**Developer Experience**:
When conversations are added to a PR, developers immediately receive:
1. A color-coded label showing the count
2. A notification comment with:
   - Clear description of what needs attention
   - Action items (review, address, mark as resolved or ask maintainer)
   - Link to where conversations can be found

**AI Relevance**: Helps track review progress on AI-generated PRs which may need more iterations. Provides immediate, actionable feedback to developers about pending discussions.

#### 2.3 Add Changes Requested Label (`add-changes-requested-label.yml`)
**Purpose**: Flag PRs with reviewer-requested changes

**Triggers**:
- Pull request opened, synchronized, reopened
- Pull request review submitted or dismissed

**Key Features**:
- Tracks most recent review state from each reviewer
- Adds/removes `changes-requested` label (red)
- Automatically clears label when issues are addressed

**AI Relevance**: Makes it easy to see which PRs need author attention vs. maintainer review.

#### 2.4 Add Migrations Label (`add-migrations-label.yml`)
**Purpose**: Flag PRs containing database migrations and validate migration sequence

**Triggers**:
- Pull request opened, synchronized, or reopened

**Key Features**:
- Detects migration files in `website/migrations/` or `comments/migrations/`
- Adds `migrations` label (yellow) for visibility
- Removes label if migrations are removed from PR
- **Validates migration numbers are sequential**:
  - Extracts migration numbers from PR files (e.g., `0252` from `0252_description.py`)
  - Fetches existing migrations from base branch via GitHub API
  - Detects conflicts when PR migration numbers ≤ highest existing migration number
  - Posts detailed comment with fix instructions when conflicts are found
  - Fails the workflow check to prevent merge until resolved
  - Auto-removes conflict comment when migrations are regenerated correctly

**Migration Conflict Detection**:
When a PR contains migrations with numbers that overlap existing migrations (e.g., PR has `0252_*.py` but base branch already has migrations up to `0263_*.py`), the workflow will:
1. Post a comment explaining the conflict
2. Provide step-by-step fix instructions (delete migrations, rebase, regenerate)
3. Fail the workflow check to prevent accidental merge
4. Automatically remove the warning when the issue is fixed

**AI Relevance**: Critical for database changes—ensures maintainers give extra attention to migration files. Also prevents migration conflicts that can occur when AI generates migrations on stale branches, which could break the database migration sequence.

#### 2.5 Check PR Conflicts (`check-pr-conflicts.yml`)
**Purpose**: Detect and notify about merge conflicts

**Triggers**:
- Pull request opened, synchronized, reopened, or ready_for_review

**Key Features**:
- Checks `mergeable` status via GitHub API
- Adds `has-conflicts` label (red)
- Posts helpful comment with resolution instructions
- Automatically removes label and comment when conflicts are resolved

**AI Relevance**: AI-generated PRs may conflict with concurrent changes. This provides instant feedback to developers.

#### 2.6 Check Approval Status (`check-approval-status.yml`)
**Purpose**: Track workflows waiting for manual approval

**Triggers**:
- Pull request events
- Workflow run requested or completed

**Key Features**:
- Counts workflows with `status: waiting` or `conclusion: action_required`
- Labels: `checks: N waiting-approval` or `checks: all-approved`
- Color-coded: green (0), yellow (1-2), red (3+)

**AI Relevance**: Some workflows need manual approval (especially for forked PRs). This makes approval status visible at a glance.

#### 2.7 Check Peer Review (`check-peer-review.yml`)
**Purpose**: Ensure PRs have received peer review before merging

**Triggers**:
- Pull request opened, synchronized, reopened
- Pull request review submitted or dismissed

**Key Features**:
- Validates PR has at least one approved review
- Excludes reviews from: PR author, bots, specific maintainers
- Adds label: `needs-peer-review` (yellow) or `has-peer-review` (green)
- Posts comment requesting review if none found
- Fails the check until a valid review is submitted

**AI Relevance**: Enforces human review on all code changes, critical for catching issues AI might miss.

#### 2.8 Check HTML Screenshot Requirement (`check-html-screenshot.yml`)
**Purpose**: Ensure PRs with HTML changes include visual evidence

**Triggers**:
- Pull request opened, edited, synchronized, or reopened

**Key Features**:
- Detects `.html` file changes
- Checks PR description for images or videos
- Posts friendly comment requesting screenshot if missing
- Skips for bot PRs

**AI Relevance**: UI changes (even AI-generated) need visual validation. Screenshots help reviewers verify changes.

#### 2.9 Detect New Markdown Files (`detect-new-md-files.yml`)
**Purpose**: Flag PRs adding new documentation files

**Triggers**:
- Pull request opened, synchronized, or reopened

**Key Features**:
- Detects newly added `.md` files
- Posts comment asking contributors to discuss with maintainers first
- Prevents unsolicited documentation additions

**AI Relevance**: AI may suggest adding docs. This ensures documentation changes are deliberate and coordinated.

#### 2.10 Enforce Issue Number in Description (`enforce-issue-number-in-description.yml`)
**Purpose**: Ensure PRs are linked to issues

**Triggers**:
- Pull request opened, edited, reopened, or synchronized

**Key Features**:
- Uses GraphQL to check for closing issue references
- Validates PR description includes `closes #N`, `fixes #N`, etc.
- Fails if no linked issues found
- Helps track which PRs address which issues

**AI Relevance**: Maintains traceability—every PR should solve a specific problem defined in an issue.

---

### 3. CI/CD & Testing

Workflows that build, test, and validate the application.

#### 3.1 CI/CD Pipeline (`ci-cd.yml`)
*(See detailed description in Code Quality section above)*

**Additional Notes**:
- Runs Django tests with verbose output
- Tests Docker image build and container execution
- Uploads test output as artifacts for debugging
- Labels PRs based on test results

#### 3.2 Regenerate Django Migrations (`regenerate-migrations.yml`)
**Purpose**: Safely regenerate database migrations for PRs

**Triggers**:
- When `regenerate-migrations` label is added
- Manual workflow dispatch

**Key Features**:
- Security-focused: Only runs on trusted base branch code
- Copies model files from PR, not arbitrary code
- Deletes PR migrations and regenerates them
- Commits updated migrations back to PR branch
- Automatically removes trigger label

**AI Relevance**: Migrations are complex. This workflow ensures they're correctly generated even if AI-assisted changes conflict with existing migrations.

#### 3.3 Fix Poetry Lock (`fix-poetry-lock.yml`)
**Purpose**: Automatically fix poetry.lock conflicts in PRs

**Triggers**:
- When `fix-poetry-lock` label is added
- Manual workflow dispatch

**Key Features**:
- Runs `poetry lock --no-update` to resolve lock file conflicts
- Does not update dependencies to newer versions
- Commits updated poetry.lock back to PR branch
- Comments on PR with status update
- Automatically removes trigger label after execution

**AI Relevance**: When multiple contributors (or AI tools) modify dependencies, poetry.lock conflicts are common. This workflow resolves them automatically without manual intervention.

#### 3.4 CodeQL Security Analysis (`codeql.yml`)
**Purpose**: Advanced security scanning for vulnerabilities

**Triggers**:
- Push to main branch
- Pull requests to main
- Weekly schedule (Fridays at 20:40 UTC)

**Key Features**:
- Scans Python, JavaScript/TypeScript, and GitHub Actions files
- Runs CodeQL analysis for security vulnerabilities
- Reports findings to GitHub Security tab
- No manual code needed—fully automated

**Security**: Critical for catching SQL injection, XSS, code injection, and other vulnerabilities.

**AI Relevance**: AI-generated code needs extra security scrutiny. CodeQL provides deep static analysis.

---

### 4. Security & Analysis

#### 4.1 CodeQL Advanced (`codeql.yml`)
*(See detailed description in CI/CD section above)*

**Additional Security Benefits**:
- Detects security vulnerabilities in multiple languages
- Integrates with GitHub Advanced Security
- Provides actionable remediation advice
- Tracks security trends over time

---

### 5. Issue Management

Workflows that handle issue lifecycle and assignment.

#### 5.1 Auto-Assign Issues to Copilot (`assign-new-issues-to-copilot.yml`)
**Purpose**: Automatically assign new issues to GitHub Copilot account

**Triggers**:
- When a new issue is opened

**Key Features**:
- Assigns issues to the "Copilot" account for AI-assisted triage
- Helps route issues to appropriate handlers
- Provides starting point for issue tracking

**AI Relevance**: Leverages AI (GitHub Copilot) for initial issue triage and routing.

#### 5.2 Auto-Close New Issues (`close-issues.yml`)
**Purpose**: Automatically close new issues with a message

**Triggers**:
- When a new issue is opened

**Key Features**:
- Immediately closes new issues
- Posts message directing users to forum instead
- Helps focus on existing issue backlog
- Mentions $5 bounties to encourage working on existing issues

**Note**: This is temporary during high-backlog periods. It prevents issue overload while the team focuses on existing work.

**AI Relevance**: Manages contribution flow—important when AI tools make it easy to create many issues quickly.

#### 5.3 Add Last Active Label (`add-last-active-label.yml`)
**Purpose**: Automatically label issues and PRs based on days since last human activity

**Triggers**:
- Daily schedule (midnight UTC)
- Manual dispatch for testing

**Key Features**:
- Adds `last-active: Xd` labels to all open issues and PRs
- Based on last **comment** timestamp (or creation date if no comments) to track real human activity
- Ignores non-human updates like label changes to prevent false activity detection
- Automatically removes outdated last-active labels before adding new ones
- Creates labels with color-coded severity:
  - 0-2 days: Green (fresh)
  - 3-7 days: Yellow (getting old)
  - 8-14 days: Orange (needs attention)
  - 15+ days: Red (stale)
- Processes both issues and pull requests
- Runs daily to keep labels current

**AI Relevance**: Helps prioritize review and maintenance efforts by surfacing items that need attention, critical for managing high-volume AI-assisted contributions.

#### 5.4 Remove Last Active Label on Update (`remove-last-active-label-on-update.yml`)
**Purpose**: Remove last-active labels when an issue or PR receives activity

**Triggers**:
- Pull request events (opened, synchronized, reopened, ready_for_review, edited)
- Issue events (opened, reopened, edited)
- Comment events (created, edited, deleted)
- Review events (submitted, edited, dismissed)
- Review comment events (created, edited, deleted)

**Key Features**:
- Automatically removes `last-active: Xd` labels when activity occurs
- Works for both issues and pull requests
- The scheduled `add-last-active-label.yml` workflow will re-add the correct label on its next run
- Ensures labels accurately reflect current activity status
- Uses GitHub API only (no code checkout for security)

**AI Relevance**: Maintains accurate activity tracking as AI tools and developers interact with issues and PRs, ensuring the most active items are properly identified.

---

### 6. Automation & Maintenance

Workflows that keep the repository healthy and up-to-date.

#### 6.1 OWASP BLT Action (`assign-issues.yml`)
**Purpose**: Custom BLT-specific automation actions

**Triggers**:
- Issue comments
- Pull request review comments
- Daily schedule (midnight UTC)
- Manual dispatch

**Key Features**:
- Uses custom `OWASP-BLT/BLT-Action@main`
- Auto-assigns issues based on activity
- Integrates with Giphy API for engagement
- Runs daily maintenance tasks

**AI Relevance**: Automates contributor engagement, making the project more accessible to AI-assisted contributors.

#### 6.2 Auto-Approve Dependabot (`auto-approve-dependabot.yml`)
**Purpose**: Automatically approve Dependabot dependency updates

**Triggers**:
- Pull requests from Dependabot

**Key Features**:
- Two-level approval (two different users)
- Only runs for Dependabot PRs
- Uses `cognitedata/auto-approve-dependabot-action@v3.0.1`
- Speeds up dependency updates

**AI Relevance**: Reduces manual work for routine dependency updates, allowing maintainers to focus on feature PRs.

#### 6.3 Auto-Merge Dependabot (`auto-merge.yml`)
**Purpose**: Automatically merge approved Dependabot PRs

**Triggers**:
- Pull request events (opened, synchronized, reopened, ready_for_review)
- Pull request review submitted
- After "Approve dependabot" workflow completes

**Key Features**:
- Waits for approvals before merging
- Retry logic (3 attempts) to ensure approvals are recorded
- Uses squash merge strategy
- Deletes branch after merge
- Only processes Dependabot PRs

**AI Relevance**: Fully automated dependency management—from creation to merge—reducing manual overhead.

#### 6.4 Auto-Update PRs (`autoupdate.yaml`)
**Purpose**: Keep PR branches updated with base branch changes

**Triggers**:
- Push to any branch except main

**Key Features**:
- Uses `chinthakagodawita/autoupdate-action@v1`
- Updates PR branches with latest base branch commits
- Ignores merge conflicts (doesn't force update)
- Keeps PRs current with main branch

**AI Relevance**: Prevents PRs from becoming stale, especially important during rapid development with AI assistance.

#### 6.5 Bounty Payout (`bounty-payout.yml`)
**Purpose**: Automatically process bounty payments for merged PRs

**Triggers**:
- Pull request closed (merged)

**Key Features**:
- Detects issues linked in PR with `$` labels (e.g., `$50`)
- Extracts bounty amount from label
- Sends payment request to BLT API
- Supports integer and decimal amounts ($50, $25.50)
- Only processes merged PRs

**AI Relevance**: Gamifies contributions with monetary rewards, encouraging quality contributions regardless of how they're created.

#### 6.6 Remind Unresolved Conversations (`remind-unresolved-conversations.yml`)
**Purpose**: Remind PR authors about pending review discussions

**Triggers**:
- Daily schedule (midnight UTC)
- Manual dispatch

**Key Features**:
- Checks all open PRs for unresolved conversations using GraphQL API
- **Proper pagination support**: Fetches all review threads across multiple pages (100 per page)
- Only reminds if PR hasn't been updated in 24 hours
- Skips bot-created PRs (detects by user type, `[bot]` suffix, or known bot list)
- Won't remind more than once per week
- Posts friendly reminder comment tagging the author
- **Comprehensive logging**: Tracks pagination progress and thread statistics for debugging

**Technical Details**:
- Uses GraphQL query with proper `$after` parameter for cursor-based pagination
- Filters out outdated threads that no longer apply to current code
- Counts resolved, unresolved, and outdated threads separately
- Logs each page fetch and provides detailed breakdown of thread states

**AI Relevance**: Keeps contributors engaged, even when they're working with AI assistance and may forget about pending discussions. Critical for ensuring AI-generated code receives proper review attention.

#### 6.7 Update All PRs (`update-all-prs.yml`)
**Purpose**: Batch update and check all open PRs

**Triggers**:
- Manual workflow dispatch only

**Key Features**:
- Updates all open PR branches with base branch
- Checks for merge conflicts on all PRs
- Adds/removes conflict labels
- Checks workflow approval status
- Posts/updates conflict resolution comments
- Skips PRs with workflow file changes (GITHUB_TOKEN limitation)

**AI Relevance**: Provides maintainers with a way to refresh all PRs after major changes, useful after AI-assisted refactoring.

---

## Best Practices

### Security Practices

1. **Use `pull_request_target` carefully**: Many workflows use `pull_request_target` to enable write permissions for forked PRs. However, they explicitly avoid checking out PR code to prevent security risks.

2. **Validate before execution**: Workflows that do check out PR code (like pre-commit fixes) include security notes and run only trusted tools.

3. **CodeQL scanning**: Weekly security scans and PR scans catch vulnerabilities early.

4. **Bot detection**: Workflows skip or handle bot PRs differently to prevent abuse.

### Performance Optimizations

1. **Caching**: Dependencies (Poetry, pre-commit, pip) are cached to speed up workflow runs.

2. **Concurrency controls**: Many workflows use concurrency groups to cancel outdated runs.

3. **Rate limiting**: Auto-fix workflows have rate limits to prevent spam.

4. **Pagination**: All API calls properly paginate results to handle large datasets.

### Developer Experience

1. **Clear feedback**: Workflows post detailed comments with actionable next steps.

2. **Helpful labels**: Color-coded labels provide visual status at a glance.

3. **Automated fixes**: When possible, workflows fix issues automatically rather than just reporting them.

4. **Retry logic**: Workflows handle transient failures gracefully with retry mechanisms.

### Maintenance

1. **DRY principles**: Common patterns (label creation, pagination) are reused across workflows.

2. **Unique markers**: Comments use HTML markers (e.g., `<!-- pr-conflict-check -->`) to identify and update specific comments.

3. **Regex patterns**: Labels are managed with regex patterns (e.g., `/^files-changed:/i`) for dynamic updates.

4. **Graceful failures**: Workflows use `continue-on-error` and proper error handling.

---

## Conclusion

The OWASP BLT repository's GitHub Actions workflows represent a **comprehensive automation strategy** that:

✅ **Maintains code quality** through automated linting and formatting  
✅ **Enhances security** with CodeQL scanning and review requirements  
✅ **Improves review efficiency** with intelligent labeling and status tracking  
✅ **Reduces manual overhead** through automated fixes and conflict detection  
✅ **Manages contributions at scale** with automated triage and reminders  
✅ **Supports AI-assisted development** by providing instant feedback and quality gates  

In the age of AI-powered coding, these workflows are essential for maintaining high standards while enabling rapid development. They provide the guardrails needed to leverage AI tools effectively while ensuring human oversight on critical decisions.

---

**Last Updated**: December 2024  
**Total Workflows**: 29  
**Maintained By**: OWASP BLT Team
