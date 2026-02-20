# OWASP BLT - URL Endpoints and Components Documentation

This document provides a comprehensive list of all URL endpoints, pages, and their corresponding components in the OWASP BLT (Bug Logging Tool) application.

**Last Updated:** 2026-02-13  
**Django Version:** 5.1+  
**Total Endpoints:** ~180+  
**Main URL Configuration:** `blt/urls.py`

---

## Table of Contents

1. [Core & Home](#1-core--home)
2. [Authentication & Social Login](#2-authentication--social-login)
3. [Issues & Bugs](#3-issues--bugs)
4. [Organizations & Domain Management](#4-organizations--domain-management)
5. [Bug Hunts & Bounties](#5-bug-hunts--bounties)
6. [Leaderboards & Scoring](#6-leaderboards--scoring)
7. [User Management & Profiles](#7-user-management--profiles)
8. [Teams & Gamification](#8-teams--gamification)
9. [Education & Courses](#9-education--courses)
10. [Blog](#10-blog)
11. [Projects & Repositories](#11-projects--repositories)
12. [GitHub Integration](#12-github-integration)
13. [Slack Integration](#13-slack-integration)
14. [Bitcoin/BACON Tokens](#14-bitcoinbacon-tokens)
15. [Jobs & Employment](#15-jobs--employment)
16. [Staking & Competitive Pools](#16-staking--competitive-pools)
17. [Hackathons](#17-hackathons)
18. [Adventures](#18-adventures)
19. [Simulation & Labs](#19-simulation--labs)
20. [Discussion & Messaging](#20-discussion--messaging)
21. [Comments System](#21-comments-system)
22. [Notifications](#22-notifications)
23. [Queue & Transactions](#23-queue--transactions)
24. [Open Source Sorting Hat (OSSH)](#24-open-source-sorting-hat-ossh)
25. [Security & Incidents](#25-security--incidents)
26. [Additional Features](#26-additional-features)
27. [API Endpoints](#27-api-endpoints)
28. [Third-Party Integrations](#28-third-party-integrations)
29. [Debug Endpoints](#29-debug-endpoints)

---

## 1. Core & Home

**Component:** `website/views/core.py`

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/` | `home` | `home` | Main homepage |
| `/500/` | `TemplateView.as_view(template_name='500.html')` | `500` | Custom 500 error page |
| `/set-theme/` | `set_theme` | `set_theme` | Toggle dark/light theme |
| `/robots.txt` | `robots_txt` | `robots_txt` | SEO robots.txt |
| `/stats-dashboard/` | `stats_dashboard` | `stats_dashboard` | System statistics dashboard |
| `/test-sentry/` | `test_sentry` | `test_sentry` | Sentry error tracking test |
| `/check_owasp_compliance/` | `check_owasp_compliance` | `check_owasp_compliance` | OWASP compliance checker |

---

## 2. Authentication & Social Login

**Components:** 
- `website/views/user.py`
- Third-party: `dj_rest_auth`, `allauth`

### Basic Authentication

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `^auth/registration/` | `dj_rest_auth.registration.urls` | `auth_registration` | User registration API |
| `^auth/` | `dj_rest_auth.urls` | `auth_base` | Base authentication endpoints |
| `accounts/` | `allauth.urls` | `accounts` | Django-allauth account management |
| `accounts/delete/` | `UserDeleteView` | `user_deletion` | User account deletion |
| `rest-auth/password/reset/confirm/<uidb64>/<token>` | `PasswordResetConfirmView` | `password_reset_confirm` | Password reset confirmation |
| `authenticate/` | `CustomObtainAuthToken` | `authenticate` | Token authentication |
| `auth/delete` | `AuthApiViewset` | `auth-delete-api` | Delete auth API |

### Social Authentication

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `auth/facebook` | `FacebookLogin` | `facebook_login` | Facebook OAuth login |
| `auth/facebook/connect/` | `FacebookConnect` | `facebook_connect` | Connect Facebook account |
| `auth/github/` | `GithubLogin` | `github_login` | GitHub OAuth login |
| `auth/github/connect/` | `GithubConnect` | `github_connect` | Connect GitHub account |
| `auth/google/` | `GoogleLogin` | `google_login` | Google OAuth login |
| `auth/google/connect/` | `GoogleConnect` | `google_connect` | Connect Google account |
| `accounts/github/login/callback/` | `github_views.oauth2_callback` | `github_callback` | GitHub OAuth callback |
| `/auth/github/url/` | `github_views.oauth2_login` | `github_oauth_login` | GitHub OAuth URL generator |
| `socialaccounts/` | `SocialAccountListView` | `social_account_list` | List connected social accounts |
| `socialaccounts/<id>/disconnect/` | `CustomSocialAccountDisconnectView` | `social_account_disconnect` | Disconnect social account |

---

## 3. Issues & Bugs

**Component:** `website/views/issue.py`

### Issue Management

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `^issues/` | `newhome` | `issues` | Browse all issues |
| `^issue/` | `IssueCreate` | `issue` | Create new issue |
| `^issue/<slug>/` | `IssueView` | `issue_view` | View specific issue |
| `^issue/edit/` | `IssueEdit` | `edit_issue` | Edit issue |
| `^issue/update/` | `UpdateIssue` | `update_issue` | Update issue details |
| `^report/` | `IssueCreate` | `report` | Report a bug |
| `^all_activity/` | `AllIssuesView` | `all_activity` | View all activity |
| `^label_activity/` | `SpecificIssuesView` | `all_activitys` | Filter by label |
| `^resolve/<id>/` | `resolve` | `resolve` | Mark issue as resolved |

### Issue Interactions

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `^like_issue/<id>/` | `like_issue` | `like_issue` | Like an issue |
| `^dislike_issue/<id>/` | `dislike_issue` | `dislike_issue` | Dislike an issue |
| `^flag_issue/<id>/` | `flag_issue` | `flag_issue` | Flag inappropriate issue |
| `^save_issue/<id>/` | `save_issue` | `save_issue` | Save issue to bookmarks |
| `^unsave_issue/<id>/` | `unsave_issue` | `unsave_issue` | Remove from bookmarks |
| `^vote_count/<id>/` | `vote_count` | `vote_count` | Get vote count |
| `^create_github_issue/<id>/` | `create_github_issue` | `create_github_issue` | Create GitHub issue |
| `^remove_user_from_issue/<id>/` | `remove_user_from_issue` | `remove_user_from_issue` | Remove user assignment |

### Content & Comments

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/content/<id>/comment/` | `comment_on_content` | `comment_on_content` | Add comment to content |
| `/content/<id>/comment/update/<id>/` | `update_content_comment` | `update_content_comment` | Update comment |
| `/content/comment/delete/` | `delete_content_comment` | `delete_content_comment` | Delete comment |

### Issue API Endpoints

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/api/v1/search/` | `search_issues` | `search_issues` | Search issues API |
| `/api/v1/createissues/` | `IssueCreate` | `issuecreate` | Create issue API |
| `/api/v1/delete_issue/<id>/` | `delete_issue` | `delete_api_issue` | Delete issue API |
| `/api/v1/issue/update/` | `UpdateIssue` | `update_api_issue` | Update issue API |
| `/api/v1/bugs/check-duplicate/` | `CheckDuplicateBugApiView` | `api_check_duplicate_bug` | Check for duplicates |
| `/api/v1/bugs/find-similar/` | `FindSimilarBugsApiView` | `api_find_similar_bugs` | Find similar bugs |
| `/api/v1/flag_issue/` | `FlagIssueApiView` | `api_flag_issue` | Flag issue API |
| `/api/load-more-issues/` | `load_more_issues` | `load_more_issues` | Pagination for issues |

---

## 4. Organizations & Domain Management

**Component:** `website/views/organization.py`

### Organization Management

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/organization/` | `RegisterOrganizationView` | `register_organization` | Register new organization |
| `/organization/view` | `Organization_view` | `organization_view` | View organization |
| `/organizations/` | `OrganizationListView` | `organizations` | List all organizations |
| `/organization/<slug>/` | `OrganizationDetailView` | `organization_detail` | Organization detail page |
| `/organization/<slug>/update-repos/` | `update_organization_repos` | `update_organization_repos` | Update org repositories |

### Organization Dashboard

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/organization/dashboard/` | `dashboard_view` | `organization_dashboard` | Main dashboard |
| `/dashboard/organization/` | `organization_dashboard` | `organization_dashboard_home` | Dashboard home |
| `/dashboard/admin/organization` | `admin_organization_dashboard` | `admin_organization_dashboard` | Admin dashboard |
| `/dashboard/admin/organization/addorupdate` | `add_or_update_organization` | `add_or_update_organization` | Add/update org |
| `/organization/<id>/dashboard/analytics/` | `OrganizationDashboardAnalyticsView` | `organization_analytics` | Analytics dashboard |
| `/organization/<id>/dashboard/integrations/` | `OrganizationDashboardIntegrations` | `organization_manage_integrations` | Manage integrations |
| `/organization/<id>/dashboard/bugs/` | `OrganizationDashboardManageBugsView` | `organization_manage_bugs` | Manage bugs |
| `/organization/<id>/dashboard/team-overview/` | `OrganizationDashboardTeamOverviewView` | `organization_team_overview` | Team overview |
| `/organization/<id>/dashboard/domains/` | `OrganizationDashboardManageDomainsView` | `organization_manage_domains` | Manage domains |
| `/organization/<id>/dashboard/roles/` | `OrganizationDashboardManageRolesView` | `organization_manage_roles` | Manage roles |
| `/organization/<id>/dashboard/bughunts/` | `OrganizationDashboardManageBughuntView` | `organization_manage_bughunts` | Manage bug hunts |
| `/organization/<id>/dashboard/add_bughunt/` | `AddHuntView` | `add_bughunt` | Add new bug hunt |
| `/organization/<id>/dashboard/add_domain/` | `AddDomainView` | `add_domain` | Add new domain |
| `/organization/<id>/dashboard/add_slack_integration/` | `AddSlackIntegrationView` | `add_slack_integration` | Add Slack integration |

### Domain Management

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/domains/` | `DomainListView` | `domains` | List all domains |
| `/domain/<slug>/` | `DomainDetailView` | `domain` | Domain detail page |
| `/domain/<id>/subscribe/` | `subscribe_to_domains` | `subscribe_to_domains` | Subscribe to domain |
| `/organization/domain/<id>/` | `DomainView` | `view_domain` | View domain |
| `/add_domain_to_organization/` | `add_domain_to_organization` | `add_domain_to_organization` | Link domain to org |
| `/dashboard/organization/domain/addorupdate` | `add_or_update_domain` | `add_or_update_domain` | Add/update domain |
| `/dashboard/organization/domain/<id>/` | `organization_dashboard_domain_detail` | `organization_dashboard_domain_detail` | Domain detail |

---

## 5. Bug Hunts & Bounties

**Component:** `website/views/bounty.py`

### Bug Hunt Management

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/start/` | `HuntCreate` (template) | `start_hunt` | Start hunt page |
| `^hunt/` | `HuntCreate` | `hunt` | Create hunt |
| `^hunt/<id>` | `ShowBughuntView` | `show_bughunt` | View specific hunt |
| `^bounties/` | `Listbounties` | `hunts` | List all bounties |
| `/bounties/payouts/` | `BountyPayoutsView` | `bounty_payouts` | View payouts |

### Organization Hunt Dashboard

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/dashboard/organization/hunt/create$` | `CreateHunt` | `create_hunt` | Create hunt |
| `/dashboard/organization/hunt/drafts$` | `DraftHunts` | `draft_hunts` | Draft hunts |
| `/dashboard/organization/hunt/upcoming$` | `UpcomingHunts` | `upcoming_hunts` | Upcoming hunts |
| `/dashboard/organization/hunt/ongoing$` | `OngoingHunts` | `ongoing_hunts` | Ongoing hunts |
| `/dashboard/organization/hunt/previous$` | `PreviousHunts` | `previous_hunts` | Previous hunts |
| `/dashboard/organization/hunt/<id>/edit` | `organization_dashboard_hunt_edit` | `organization_dashboard_hunt_edit` | Edit hunt |
| `/dashboard/organization/hunt/previous/<id>/` | `organization_hunt_results` | `organization_hunt_results` | Hunt results |

### User Hunt Dashboard

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/dashboard/user/hunt/<id>/` | `view_hunt` | `view_hunt` | View hunt |
| `/dashboard/user/hunt/<id>/submittion/` | `submit_bug` | `submit_bug` | Submit bug |
| `/dashboard/user/hunt/<id>/results/` | `hunt_results` | `hunt_results` | View results |

### Bug Acceptance

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/organization/accept_bug/<id>/<id>/` | `accept_bug` | `accept_bug` | Accept bug with reward |
| `/organization/accept_bug/<id>/` | `accept_bug` | `accept_bug_no_reward` | Accept bug without reward |

### Bounty API

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/api/v1/hunt/` | `BugHuntApiViewset` | `hunt_details` | Hunt API v1 |
| `/api/v2/hunts/` | `BugHuntApiViewsetV2` | `hunts_detail_v2` | Hunt API v2 |

---

## 6. Leaderboards & Scoring

**Component:** `website/views/core.py`

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `^leaderboard/` | `GlobalLeaderboardView` | `leaderboard_global` | Global leaderboard |
| `^leaderboard/monthly/` | `SpecificMonthLeaderboardView` | `leaderboard_specific_month` | Monthly leaderboard |
| `^leaderboard/each-month/` | `EachmonthLeaderboardView` | `leaderboard_eachmonth` | All months leaderboard |
| `/scoreboard/` | `ScoreboardView` | `scoreboard` | Scoreboard view |
| `^api/v1/leaderboard/` | `LeaderboardApiViewSet` | `leaderboard` | Leaderboard API |

---

## 7. User Management & Profiles

**Component:** `website/views/user.py`

### Profile Management

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `^dashboard/user/` | `user_dashboard` | `user` | User dashboard |
| `^profile/<slug>/` | `UserProfileDetailView` | `profile` | View user profile |
| `/profile/edit/` | `profile_edit` | `profile_edit` | Edit profile |
| `^accounts/profile/` | `profile` | `account_profile` | Account profile |
| `/users/` | `users_view` | `users` | List all users |

### User Interactions

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `^follow/<user>/` | `follow_user` | `follow_user` | Follow user |
| `/invite-friend/` | `invite_friend` | `invite_friend` | Invite friend |
| `/referral/` | `referral_signup` | `referral_signup` | Referral signup |
| `^api/v1/invite_friend/` | `InviteFriendApiViewset` | `api_invite_friend` | Invite friend API |

### User Stats

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/contributor-stats/` | `contributor_stats_view` | `contributor_stats` | Contributor statistics |
| `^contributors/` | `contributors_view` | `contributors` | List contributors |
| `/api/v1/contributors/` | `contributors` | `api_contributor` | Contributors API |
| `^api/v1/count/` | `issue_count` | `api_count` | Issue count API |
| `/api/v1/userscore/` | `get_score` | `get_score` | Get user score |

### User Wallet

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/api/v1/createwallet/` | `create_wallet` | `create_wallet` | Create wallet |
| `/update_bch_address/` | `update_bch_address` | `update_bch_address` | Update BCH address |

---

## 8. Teams & Gamification

**Component:** `website/views/teams.py`

### Team Management

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/teams/overview/` | `TeamOverview` | `team_overview` | Team overview |
| `/teams/search-users/` | `search_users` | `search_users` | Search users |
| `/teams/create-team/` | `create_team` | `create_team` | Create team |
| `/teams/join-requests/` | `join_requests` | `join_requests` | View join requests |
| `/teams/add-member/` | `add_member` | `add_member` | Add team member |
| `/teams/delete-team/` | `delete_team` | `delete_team` | Delete team |
| `/teams/leave-team/` | `leave_team` | `leave_team` | Leave team |
| `/teams/kick-member/` | `kick_member` | `kick_member` | Kick member |

### Team Features

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/teams/give-kudos/` | `GiveKudosView` | `give_kudos` | Give kudos |
| `/teams/challenges/` | `TeamChallenges` | `team_challenges` | Team challenges |
| `/teams/leaderboard/` | `TeamLeaderboard` | `team_leaderboard` | Team leaderboard |
| `/user_challenges/` | `UserChallengeListView` | `user_challenges` | User challenges |

---

## 9. Education & Courses

**Component:** `website/views/education.py`

### Course Management

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `^education/` | `education_home` | `education` | Education home |
| `/education/instructor_dashboard/` | `instructor_dashboard` | `instructor_dashboard` | Instructor dashboard |
| `/education/create-standalone-lecture/` | `create_standalone_lecture` | `create_standalone_lecture` | Create lecture |
| `/education/view-course/<id>/` | `view_course` | `view_course` | View course |
| `/education/view-lecture/<id>/` | `view_lecture` | `view_lecture` | View lecture |

### Course Enrollment

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/education/enroll/<id>/` | `enroll` | `enroll` | Enroll in course |
| `/education/study_course/<id>/` | `study_course` | `study_course` | Study course |
| `/education/mark-lecture-complete/` | `mark_lecture_complete` | `mark_lecture_complete` | Mark complete |
| `/education/get-course-content/<id>/` | `get_course_content` | `get_course_content` | Get content |

### Content Management

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/education/course-content-management/<id>/` | `course_content_management` | `course_content_management` | Manage content |
| `/education/add-lecture/<id>/` | `add_lecture` | `add_lecture` | Add lecture |
| `/education/edit-lecture/<id>/` | `edit_lecture` | `edit_lecture` | Edit lecture |
| `/education/delete-lecture/<id>/` | `delete_lecture` | `delete_lecture` | Delete lecture |
| `/education/add-section/<id>/` | `add_section` | `add_section` | Add section |
| `/education/edit-section/<id>/` | `edit_section` | `edit_section` | Edit section |
| `/education/delete-section/<id>/` | `delete_section` | `delete_section` | Delete section |
| `/education/reorder-content/<id>/` | `reorder_content` | `reorder_content` | Reorder content |
| `/education/publish-course/<id>/` | `publish_course` | `publish_course` | Publish course |

---

## 10. Blog

**Component:** `website/views/blog.py`

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/blog/` | `PostListView` | `post_list` | List blog posts |
| `/blog/new/` | `PostCreateView` | `post_form` | Create new post |
| `/blog/<slug>/` | `PostDetailView` | `post_detail` | View blog post |
| `/blog/<slug>/edit/` | `PostUpdateView` | `post_update` | Edit blog post |
| `/blog/<slug>/delete/` | `PostDeleteView` | `post_delete` | Delete blog post |

---

## 11. Projects & Repositories

**Component:** `website/views/project.py`

### Project Management

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `^projects/` | `ProjectView` | `project_list` | List projects |
| `^projects/compact/` | `ProjectCompactListView` | `project_compact_list` | Compact list |
| `/project/<slug>/` | `ProjectsDetailView` | `project_detail` | Project details |
| `/project/<slug>/delete/` | `delete_project` | `delete_project` | Delete project |
| `/projects/create/` | `create_project` | `create_project` | Create project |
| `/projects/<slug>/badge/` | `ProjectBadgeView` | `project-badge` | Project badge |

### Project API

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/api/v1/projects/` | `ProjectViewSet` | `projects_api` | Projects API |
| `/api/v1/tags` | `TagApiViewset` | `tags-api` | Tags API |

### Repository Management

**Component:** `website/views/repo.py`

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/repo_list/` | `RepoListView` | `repo_list` | List repositories |
| `/add_repo` | `add_repo` | `add_repo` | Add repository |

---

## 12. GitHub Integration

**Component:** `website/views/core.py`, `website/views/social.py`

### GitHub Issues

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/github-issues/` | `GitHubIssuesView` | `github_issues` | List GitHub issues |
| `/github-issues/<id>/` | `GitHubIssueDetailView` | `github_issue_detail` | View issue |
| `/create-github-issue/` | `GithubIssueView` | `create_github_issue` | Create issue |
| `/get-github-issue/` | `get_github_issue` | `get_github_issue` | Get issue |
| `/github-webhook/` | `github_webhook` | `github-webhook` | GitHub webhook |

### GSoC Integration

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/gsoc/` | `GsocView` | `gsoc` | GSoC home |
| `/gsoc/refresh/` | `refresh_gsoc_project` | `refresh_gsoc_project` | Refresh GSoC data |
| `/gsoc/pr-report/` | `gsoc_pr_report` | `gsoc_pr_report` | PR report |

---

## 13. Slack Integration

**Component:** `website/views/slack_handlers.py`, `website/views/slackbot.py`

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/slack/` | `slack_landing_page` | `slack_landing_page` | Slack landing |
| `/slack/commands/` | `slack_commands` | `slack_commands` | Slack commands |
| `/slack/events` | `slack_events` | `slack_events` | Slack events |
| `/oauth/slack/callback/` | `SlackCallbackView` | `slack_oauth_callback` | OAuth callback |
| `^dashboard/organization/slack-channels$` | `slack_channels_list` | `slack_channels_list` | List channels |
| `/dashboard/organization/slack-channels/link` | `link_slack_channel_to_project` | `link_slack_channel_to_project` | Link channel |

---

## 14. Bitcoin/BACON Tokens

**Component:** `website/views/bitcoin.py`

### BACON System

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `^bacon/` | `bacon_view` | `bacon` | BACON home |
| `/bacon-requests/` | `bacon_requests_view` | `bacon_requests` | View requests |
| `/api/bacon/submit/` | `BaconSubmissionView` | `bacon_submit` | Submit request |
| `/batch-send-bacon-tokens/` | `batch_send_bacon_tokens_view` | `batch_send_bacon_tokens` | Batch send |
| `/update-submission-status/<id>/` | `update_submission_status` | `update_submission_status` | Update status |
| `/distribute_bacon/<id>/` | `distribute_bacon` | `distribute_bacon` | Distribute BACON |

### Transactions

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/pending-transactions/` | `pending_transactions_view` | `pending_transactions` | Pending transactions |
| `/initiate-transaction/` | `initiate_transaction` | `initiate_transaction` | Initiate transaction |
| `/api/get-wallet-balance/` | `get_wallet_balance` | `get_wallet_balance` | Get balance |

---

## 15. Jobs & Employment

**Component:** `website/views/organization.py`

### Public Job Listings

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/jobs/` | `public_job_list` | `public_job_list` | List jobs |
| `/jobs/<id>/` | `job_detail` | `job_detail` | Job details |

### Organization Job Management

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/organization/<id>/dashboard/jobs/` | `OrganizationDashboardManageJobsView` | `organization_manage_jobs` | Manage jobs |
| `/organization/<id>/jobs/create/` | `create_job` | `create_job` | Create job |
| `/organization/<id>/jobs/<job_id>/edit/` | `edit_job` | `edit_job` | Edit job |
| `/organization/<id>/jobs/<job_id>/delete/` | `delete_job` | `delete_job` | Delete job |
| `/organization/<id>/jobs/<job_id>/toggle/` | `toggle_job_status` | `toggle_job_status` | Toggle status |

### Jobs API

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/api/v1/jobs/public/` | `PublicJobListViewSet` | `api_public_jobs` | Public jobs API |
| `/api/v1/organization/<id>/jobs/stats/` | `OrganizationJobStatsViewSet` | `api_organization_job_stats` | Job stats API |

---

## 16. Staking & Competitive Pools

**Component:** `website/views/staking_competitive.py`

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/staking/` | `staking_home` | `staking_home` | Staking home |
| `/staking/pool/<id>/` | `pool_detail` | `pool_detail` | Pool details |
| `/staking/pool/<id>/join/` | `stake_in_pool` | `stake_in_pool` | Join pool |
| `/staking/my-stakes/` | `my_staking` | `my_staking` | My stakes |
| `/staking/leaderboard/` | `staking_leaderboard` | `staking_leaderboard` | Staking leaderboard |
| `/staking/create/` | `create_staking_pool` | `create_staking_pool` | Create pool |

---

## 17. Hackathons

**Component:** `website/views/hackathon.py`

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/hackathons/` | `HackathonListView` | `hackathons` | List hackathons |
| `/hackathons/create/` | `HackathonCreateView` | `hackathon_create` | Create hackathon |
| `/hackathons/<slug>/` | `HackathonDetailView` | `hackathon_detail` | View hackathon |
| `/hackathons/<slug>/edit/` | `HackathonUpdateView` | `hackathon_update` | Edit hackathon |
| `/hackathons/<slug>/add-sponsor/` | `HackathonSponsorCreateView` | `hackathon_sponsor_create` | Add sponsor |
| `/hackathons/<slug>/add-prize/` | `HackathonPrizeCreateView` | `hackathon_prize_create` | Add prize |
| `/hackathons/<slug>/refresh-all-repos/` | `refresh_all_hackathon_repositories` | `refresh_all_hackathon_repositories` | Refresh repos |
| `/hackathons/<slug>/add-org-repos/` | `add_org_repos_to_hackathon` | `add_org_repos_to_hackathon` | Add org repos |

---

## 18. Adventures

**Component:** `website/views/adventure.py`

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/adventures/` | `AdventureListView` | `adventure_list` | List adventures |
| `/adventures/<slug>/` | `AdventureDetailView` | `adventure_detail` | View adventure |
| `/adventures/<slug>/start/` | `start_adventure` | `start_adventure` | Start adventure |
| `/adventures/<slug>/task/<id>/submit/` | `submit_task` | `submit_task` | Submit task |

---

## 19. Simulation & Labs

**Component:** `website/views/Simulation.py`

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/simulation/` | `dashboard` | `simulation_dashboard` | Simulation home |
| `/simulation/lab/<id>/` | `lab_detail` | `lab_detail` | Lab details |
| `/simulation/lab/<id>/task/<id>/` | `task_detail` | `task_detail` | Task details |
| `/simulation/lab/<id>/task/<id>/submit/` | `submit_answer` | `submit_answer` | Submit answer |

---

## 20. Discussion & Messaging

**Component:** `website/views/social.py`

### Discussion Rooms

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/discussion-rooms/` | `RoomsListView` | `rooms_list` | List rooms |
| `/discussion-rooms/create/` | `RoomCreateView` | `room_create` | Create room |
| `/discussion-rooms/join-room/<id>/` | `join_room` | `join_room` | Join room |
| `/discussion-rooms/delete-room/<id>/` | `delete_room` | `delete_room` | Delete room |
| `/api/room-messages/<id>/` | `room_messages_api` | `room_messages_api` | Room messages API |

### Private Messaging

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/messaging/` | `messaging_home` | `messaging` | Messaging home |
| `/messaging/start-thread/<id>/` | `start_thread` | `start_thread` | Start thread |
| `/api/messaging/<id>/messages/` | `view_thread` | `thread_messages` | View messages |
| `/api/messaging/set-public-key/` | `set_public_key` | `set_public_key` | Set public key |
| `/api/messaging/<id>/get-public-key/` | `get_public_key` | `get_public_key` | Get public key |
| `/api/messaging/thread/<id>/delete/` | `delete_thread` | `delete_thread` | Delete thread |
| `/api/send-message/` | `send_message_api` | `send_message_api` | Send message API |

### Video Calls

**Component:** `website/views/video_call.py`

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/video_call/` | `video_call` | `video_call` | Video call interface |

---

## 21. Comments System

**Component:** `comments` app

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `^issue/comment/add/` | `comments.views.add_comment` | `add_comment` | Add comment |
| `^issue/comment/delete/` | `comments.views.delete_comment` | `delete_comment` | Delete comment |
| `^comment/autocomplete/` | `comments.views.autocomplete` | `autocomplete` | Autocomplete |
| `^issue/<pk>/comment/edit/` | `comments.views.edit_comment` | `edit_comment` | Edit comment |
| `^issue/<pk>/comment/reply/` | `comments.views.reply_comment` | `reply_comment` | Reply to comment |

---

## 22. Notifications

**Component:** `website/views/core.py`

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/notifications/fetch/` | `fetch_notifications` | `fetch_notifications` | Fetch notifications |
| `/notifications/mark_all_read` | `mark_as_read` | `mark_all_read` | Mark all as read |
| `/notifications/delete_notification/<id>` | `delete_notification` | `delete_notification` | Delete notification |

---

## 23. Queue & Transactions

**Component:** `website/views/queue.py`

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/queue/` | `queue_list` | `queue_list` | List queue items |
| `/queue/create/` | `queue_list` | `queue_create` | Create queue item |
| `/queue/<id>/edit/` | `queue_list` | `queue_edit` | Edit queue item |
| `/queue/<id>/delete/` | `queue_list` | `queue_delete` | Delete queue item |
| `/queue/<id>/launch/` | `queue_list` | `queue_launch` | Launch transaction |
| `/queue/<id>/update-txid/` | `update_txid` | `queue_update_txid` | Update transaction ID |
| `/queue/launch-control/` | `queue_list` | `queue_launch_page` | Launch control page |

---

## 24. Open Source Sorting Hat (OSSH)

**Component:** `website/views/ossh.py`

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/open-source-sorting-hat/` | `ossh_home` | `ossh_home` | OSSH home |
| `/open-source-sorting-hat/results` | `ossh_results` | `ossh_results` | View results |
| `/get-github-data/` | `get_github_data` | `get_github_data` | Get GitHub data |
| `/get-recommended-repos/` | `get_recommended_repos` | `get_recommended_repos` | Get recommended repos |
| `/get-recommended-communities/` | `get_recommended_communities` | `get_recommended_communities` | Get communities |
| `/get-recommended-articles/` | `get_recommended_articles` | `get_recommended_articles` | Get articles |
| `/get-recommended-discussion-channels/` | `get_recommended_discussion_channels` | `get_recommended_discussion_channels` | Get discussion channels |

---

## 25. Security & Incidents

**Component:** `website/views/security_incidents.py`

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/security/dashboard/` | `SecurityDashboardView` | `security_dashboard` | Security dashboard |
| `/security/incidents/add/` | `SecurityIncidentCreateView` | `security_incident_add` | Report incident |
| `/security/incidents/<id>/` | `SecurityIncidentDetailView` | `security_incident_detail` | View incident |
| `/security/incidents/<id>/edit/` | `SecurityIncidentUpdateView` | `security_incident_edit` | Edit incident |

---

## 26. Additional Features

**Component:** Various (`website/views/core.py`, `website/views/daily_reminders.py`)

### Activity Management

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/activity/like/<id>/` | `like_activity` | `like_activity` | Like activity |
| `/activity/dislike/<id>/` | `dislike_activity` | `dislike_activity` | Dislike activity |
| `/activity/approve/<id>/` | `approve_activity` | `approve_activity` | Approve activity |
| `/activity/delete/<id>/` | `delete_activity` | `delete_activity` | Delete activity |

### Badges

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/badges/` | `badge_list` | `badges` | List badges |
| `/badges/<id>/users/` | `badge_user_list` | `badge_user_list` | Badge users |
| `/assign-badge/<username>/` | `assign_badge` | `assign_badge` | Assign badge |

### Bidding System

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/generate_bid_image/<amount>/` | `generate_bid_image` | `generate_bid_image` | Generate bid image |
| `/bidding/` | `SaveBiddingData` | `BiddingData` | Save bidding data |
| `/select_bid/` | `select_bid` | `select_bid` | Select bid |
| `/get_unique_issues/` | `get_unique_issues` | `get_unique_issues` | Get unique issues |
| `/change_bid_status/` | `change_bid_status` | `change_bid_status` | Change bid status |
| `/fetch-current-bid/` | `fetch_current_bid` | `fetch_current_bid` | Fetch current bid |

### Time Tracking (Sizzle)

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/sizzle/` | `sizzle` | `sizzle` | Sizzle home |
| `/check-in/` | `checkIN` | `checkIN` | Check in |
| `/add-sizzle-checkin/` | `add_sizzle_checkIN` | `add_sizzle_checkin` | Add check-in |
| `/sizzle-docs/` | `sizzle_docs` | `sizzle-docs` | Sizzle docs |
| `/api/timelogsreport/` | `TimeLogListAPIView` | `timelogsreport` | Time log report API |
| `/time-logs/` | `TimeLogListView` | `time_logs` | View time logs |
| `/sizzle-daily-log/` | `sizzle_daily_log` | `sizzle_daily_log` | Daily log |
| `/user-sizzle-report/<username>/` | `user_sizzle_report` | `user_sizzle_report` | User report |
| `/delete_time_entry/` | `delete_time_entry` | `delete_time_entry` | Delete entry |
| `/blt-tomato/` | `blt_tomato` | `blt-tomato` | BLT Tomato |

### PR & Contributions

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/Submitpr/` | `submit_pr` | `submit_pr` | Submit PR |
| `/submit-roadmap-pr/` | `submit_roadmap_pr` | `submit-roadmap-pr` | Submit roadmap PR |
| `/view-pr-analysis/` | `view_pr_analysis` | `view_pr_analysis` | View PR analysis |
| `/contribute/` | `ContributeView` | `contribution_guidelines` | Contribution guide |
| `/select_contribution/` | `select_contribution` | `select_contribution` | Select contribution |

### Reports & Analytics

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/weekly-report/` | `weekly_report` | `weekly_report` | Weekly report |
| `/page-vote/` | `page_vote` | `page_vote` | Page voting |

### Trademark Search

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/trademarks/` | `trademark_search` | `trademark_search` | Trademark search |
| `/api/trademarks/search/` | `trademark_search_api` | `api_trademark_search` | Trademark API |

### Bounty Management

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/bounty_payout/` | `bounty_payout` | `bounty_payout` | Bounty payout |

### Search History

| Path | View Function | URL Name | Description |
|------|--------------|----------|-------------|
| `/api/v1/search-history/` | `SearchHistoryApiView` | `search_history_api` | Search history API |

---

## 27. API Endpoints

**Component:** `website/api/views.py`

### DRF Router Endpoints

These endpoints use Django REST Framework's DefaultRouter and provide standard CRUD operations:

| Base Path | ViewSet | Description |
|-----------|---------|-------------|
| `/api/v1/issues/` | `IssueViewSet` | Issue CRUD operations |
| `/api/v1/userissues/` | `UserIssueViewSet` | User-specific issues |
| `/api/v1/profile/` | `UserProfileViewSet` | User profile management |
| `/api/v1/domain/` | `DomainViewSet` | Domain management |
| `/api/v1/timelogs/` | `TimeLogViewSet` | Time log entries |
| `/api/v1/activitylogs/` | `ActivityLogViewSet` | Activity tracking |
| `/api/v1/organizations/` | `OrganizationViewSet` | Organization management |
| `/api/v1/jobs/` | `JobViewSet` | Job postings |
| `/api/v1/security-incidents/` | `SecurityIncidentViewSet` | Security incidents |

Each router endpoint supports:
- `GET /api/v1/{resource}/` - List all
- `POST /api/v1/{resource}/` - Create new
- `GET /api/v1/{resource}/{id}/` - Retrieve one
- `PUT /api/v1/{resource}/{id}/` - Update
- `PATCH /api/v1/{resource}/{id}/` - Partial update
- `DELETE /api/v1/{resource}/{id}/` - Delete

---

## 28. Third-Party Integrations

### Django Packages

| Path | Package | Description |
|------|---------|-------------|
| `^captcha/` | `django-simple-captcha` | CAPTCHA functionality |
| `^i18n/` | `django.conf.urls.i18n` | Internationalization |
| `^tz_detect/` | `tz_detect` | Timezone detection |
| `^ratings/` | `star_ratings` | Star rating system |

### API Documentation

| Path | View | Description |
|------|------|-------------|
| `^swagger(.json\|.yaml)$` | `schema_view` | Swagger schema |
| `^swagger/` | `schema_view.with_ui('swagger')` | Swagger UI |
| `^redoc/` | `schema_view.with_ui('redoc')` | ReDoc UI |

---

## 29. Debug Endpoints

**Component:** `website/api/views.py`

⚠️ **These endpoints are only available when `DEBUG=True`**

| Path | View | Description |
|------|------|-------------|
| `/api/debug/system-stats/` | `DebugSystemStatsApiView` | System statistics |
| `/api/debug/cache-info/` | `DebugCacheInfoApiView` | Cache information |
| `/api/debug/populate-data/` | `DebugPopulateDataApiView` | Populate test data |
| `/api/debug/clear-cache/` | `DebugClearCacheApiView` | Clear cache |
| `^__debug__/` | Django Debug Toolbar | Debug toolbar |

---

## URL Pattern Categories Summary

| Category | Endpoint Count | Primary Component |
|----------|----------------|-------------------|
| Issues & Bugs | 25+ | `website/views/issue.py` |
| Organizations | 40+ | `website/views/organization.py` |
| Authentication | 16 | Various + third-party |
| Bug Hunts | 15+ | `website/views/bounty.py` |
| Education | 15+ | `website/views/education.py` |
| Teams | 12 | `website/views/teams.py` |
| User Management | 20+ | `website/views/user.py` |
| Jobs | 10+ | `website/views/organization.py` |
| GitHub Integration | 10+ | `website/views/core.py` |
| Messaging | 10+ | `website/views/social.py` |
| API Endpoints | 9 viewsets | `website/api/views.py` |
| Other Features | 50+ | Various |

**Total: ~180+ URL patterns**

---

## Notes

1. **URL Pattern Format**: Patterns use both Django's `path()` (with `<type:name>` syntax) and legacy `url()` (with regex `^pattern$`).

2. **API Versioning**: The application uses `/api/v1/` for most API endpoints, with some newer endpoints using `/api/v2/`.

3. **Authentication Required**: Most dashboard and management endpoints require authentication.

4. **Organization Permissions**: Organization-specific endpoints (with `<id>` in path) require appropriate organization membership.

5. **Debug Mode**: Several endpoints are conditionally included only when `DEBUG=True`.

6. **Third-Party URLs**: Integration with allauth, dj-rest-auth, and other packages adds additional URL patterns not explicitly shown in `urls.py`.

7. **WebSocket Support**: Real-time features use Django Channels (see `consumers.py` for WebSocket routing).

---

## Maintenance

This documentation should be updated when:
- New URL patterns are added
- Existing patterns are modified or removed
- View functions are renamed or refactored
- New components/modules are created

---

**Generated for:** OWASP BLT  
**Repository:** https://github.com/OWASP-BLT/BLT  
**Documentation Date:** February 2026
