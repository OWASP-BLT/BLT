<h1 align="center"> 🐛 OWASP BLT </h1>
<h3 align="center">Bug Logging Tool - Gamified Crowd-Sourced QA Testing & Vulnerability Disclosure</h3>

<p align="center">
  <strong>A gamified platform for discovering and reporting bugs across websites, applications, Git repositories, and more.</strong>
</p>

<p align="center">
  <a href="https://owaspblt.org">🌐 Website</a> •
  <a href="https://github.com/OWASP-BLT/BLT/blob/main/CONTRIBUTING.md">📖 Contributing Guide</a> •
  <a href="https://owasp.org/slack/invite">💬 Join Slack</a> •
  <a href="https://github.com/OWASP-BLT/BLT/issues">🐛 Report Bug</a>
</p>

---

## 📊 Project Stats

<p align="center">
  <a href="https://github.com/OWASP-BLT/BLT/blob/main/LICENSE.md">
    <img src="https://img.shields.io/badge/license-AGPL--3.0-blue" alt="License">
  </a>
  <a href="https://github.com/OWASP-BLT/BLT">
    <img src="https://img.shields.io/github/stars/OWASP-BLT/BLT?style=social" alt="GitHub stars">
  </a>
</p>

<p align="center">
  <a href="https://github.com/OWASP-BLT/BLT/graphs/contributors">
    <img src="https://img.shields.io/github/contributors/OWASP-BLT/BLT?color=%23e74c3c" alt="Contributors">
  </a>
  <a href="https://github.com/OWASP-BLT/BLT/commits/main">
    <img src="https://img.shields.io/github/last-commit/OWASP-BLT/BLT?color=%23e74c3c" alt="Last Commit">
  </a>
  <a href="https://github.com/OWASP-BLT/BLT/issues">
    <img src="https://img.shields.io/github/issues/OWASP-BLT/BLT?color=%23e74c3c" alt="Open Issues">
  </a>
  <a href="https://github.com/OWASP-BLT/BLT/pulls">
    <img src="https://img.shields.io/github/issues-pr/OWASP-BLT/BLT?color=%23e74c3c" alt="Pull Requests">
  </a>
</p>

<p align="center">
  <a href="https://github.com/OWASP-BLT/BLT">
    <img src="https://img.shields.io/github/languages/top/OWASP-BLT/BLT?color=%23e74c3c" alt="Top Language">
  </a>
  <a href="https://github.com/OWASP-BLT/BLT">
    <img src="https://img.shields.io/github/repo-size/OWASP-BLT/BLT?color=%23e74c3c" alt="Repo Size">
  </a>
  <a href="https://github.com/OWASP-BLT/BLT/fork">
    <img src="https://img.shields.io/github/forks/OWASP-BLT/BLT?style=social" alt="Forks">
  </a>
  <img src="https://owaspblt.org/repos/blt/badge/" alt="Views">
</p>

---

## 🎯 What is OWASP BLT?

**OWASP BLT (Bug Logging Tool)** is a gamified crowd-sourced QA testing and vulnerability disclosure platform that encompasses websites, apps, git repositories, and more. 

The platform helps coders and security researchers discover organizations, repositories, and projects to test and report to, making it easier to find meaningful security work and contribute to the community.

Our team has created dozens of open-source tools to assist in our main vision, including tools specific to the OWASP foundation. We embrace the AI revolution and have developed AI-powered tools and processes for efficient coding in harmony between humans and AI. 

Built by the community for the community, BLT makes it easy for security researchers, developers, and organizations to collaborate on finding and fixing vulnerabilities.

### ✨ Key Features

- 🔍 **QA Testing & Vulnerability Disclosure** - Discover and report bugs across websites, apps, git repositories, and projects
- 🗺️ **Discover Testing Opportunities** - Find organizations, repositories, and projects to test and report to
- 🏆 **Rewards & Recognition** - Earn rewards, badges, and recognition for your contributions to software quality and security
- 👥 **Crowd-Sourced Testing** - Join a vibrant community of testers, security researchers, and developers
- 🎮 **Gamification** - Leaderboards, challenges, and competitions to make testing engaging and rewarding
- 💰 **Staking System** - Innovative blockchain-based reward system for contributors
- 🤖 **AI-Powered Tools** - Leverage AI for efficient coding, PR reviews, issue generation, and similarity scanning
- 📊 **Comprehensive Dashboard** - Track your progress, statistics, and impact across all platforms
- 🌐 **Open Source Ecosystem** - Dozens of open-source tools supporting our mission
- 🛡️ **OWASP Project** - Part of the Open Worldwide Application Security Project family

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11.2+
- PostgreSQL
- Docker & Docker Compose (recommended)

### Installation

#### Using Docker (Recommended)
```bash
# Clone the repository
git clone https://github.com/OWASP-BLT/BLT.git
cd BLT

# Configure environment
cp .env.example .env

# Build and start
docker-compose build
docker-compose up
```

Access the application at **http://localhost:8000**


##### Docker Desktop (Windows)

This project uses Linux containers.

On modern Docker Desktop (WSL 2–based), Linux containers are enabled by default.
You may not see a “Switch to Linux containers” option in the Docker tray menu — this is expected.

If Docker Desktop is running and the following command shows `OSType: linux`,
then your setup is correct and no additional action is required:

```bash
docker info | findstr OSType
```

#### Using Poetry
```bash
# Install Poetry
pip install poetry

# 1. Install dependencies first (Creates the virtual environment)
poetry install

# 2. Activate the virtual environment
poetry shell


#### Beginner-Friendly Non-Docker Setup (Codespaces for Windows Beginners)

Docker/virtualization issues on Windows? Use Poetry + SQLite in GitHub Codespaces (free cloud VS Code—no local compilation/virtualization problems!).

1. Create Codespace on main branch.
2. `cp .env.example .env`
3. `poetry install` (add `poetry run pip install psutil` if errors)
4. Edit `.env`:
   - `DATABASE_URL=sqlite:///db.sqlite3`
   - Add `SECRET_KEY=bengaluru2026-sharanyaa-random!@#`
   - Comment Postgres lines with `#`
   - Dummy: `OPENAI_API_KEY=dummy`
   - Keep `DEBUG=True`
5. `poetry run python manage.py migrate`
6. `poetry run python manage.py createsuperuser`
7. Run on free port: `poetry run python manage.py runserver 0.0.0.0:8001`
8. Open port 8001 in Ports tab.

Tested by complete beginner Sharanyaa from Bengaluru—app running perfectly in Codespaces on January 14, 2026! 🚀

# Set up database
python manage.py migrate
python manage.py loaddata website/fixtures/initial_data.json
python manage.py createsuperuser

# Run the server
python manage.py runserver
```

For detailed setup instructions, see our [Contributing Guide](https://github.com/OWASP-BLT/BLT/blob/main/CONTRIBUTING.md).

---


#### Beginner-Friendly Non-Docker Setup (Codespaces for Windows Beginners)

Docker/virtualization issues on Windows? Use Poetry + SQLite in GitHub Codespaces (free cloud—no local problems!).

1. Create Codespace on main branch.
2. `cp .env.example .env`
3. `poetry install` (add `poetry run pip install psutil` if "ModuleNotFound" errors)
4. Edit `.env`:
   - `DATABASE_URL=sqlite:///db.sqlite3`
   - Add `SECRET_KEY=your-random-bengaluru2026!@#`
   - Comment Postgres lines with `#`
   - Dummy keys: `OPENAI_API_KEY=dummy`
   - Keep `DEBUG=True`
5. Optional CSRF fix in `blt/settings.py`: Set `ALLOWED_HOSTS = ['*']` and add:
   ```python
   CSRF_TRUSTED_ORIGINS = [
       'https://*.github.dev',
       'https://*.app.github.dev',
       'http://localhost:*',
   ]

## 🤝 Contributing

We welcome contributions from everyone! Whether you're fixing bugs, adding features, improving documentation, or spreading the word, your help is appreciated.

- 📚 Read our [Contributing Guide](https://github.com/OWASP-BLT/BLT/blob/main/CONTRIBUTING.md)
- 🐛 Check out [open issues](https://github.com/OWASP-BLT/BLT/issues)
- 💡 Look for issues tagged with `good first issue` if you're new
- 🎨 Follow our coding standards (Black, isort, ruff)
- ✅ Run `pre-commit` before submitting changes

### 📊 GitHub Action Leaderboard

Our repository uses an automated leaderboard bot to recognize and gamify contributions. When you open a pull request, a leaderboard comment is automatically posted showing your monthly ranking compared to other contributors.

#### How It Works

The leaderboard bot runs automatically on every new pull request using GitHub Actions. It:

1. **Collects Monthly Statistics** - Aggregates contribution data for the current month (UTC timezone)
2. **Calculates Points** - Awards points based on various contribution types
3. **Ranks Contributors** - Sorts users by total points, with tiebreakers
4. **Posts Leaderboard** - Comments on the PR showing the contributor's rank and nearby competitors

#### Scoring System

The leaderboard awards points based on these contribution types:

| Activity | Points | Notes |
|----------|--------|-------|
| **Open PR** | +1 per PR | All currently open PRs (repo-wide, no scoring cap; new PRs blocked if 50+ open) |
| **Merged PR** | +10 per PR | PRs merged during the current month |
| **Closed PR (not merged)** | -2 per PR | PRs closed without merging during the current month |
| **Code Review** | +5 per review | First two reviews per PR, where the review was submitted during the current month |
| **Comments** | +2 per comment | Issue/PR comments during the current month (excludes comments that mention @coderabbitai) |
| **CodeRabbit Discussions** | Configurable | See below for details |

**Total Score Formula:**
```
Total = (Open PRs × 1) + (Merged PRs × 10) + (Closed PRs × -2) + (Reviews × 5) + (Comments × 2) + CodeRabbit Bonus
```

#### Ranking Logic

Contributors are sorted by:
1. **Total points** (highest first)
2. **Number of merged PRs** (tiebreaker)
3. **Number of reviews** (second tiebreaker)
4. **Alphabetical order** (final tiebreaker, case-insensitive)

Top 3 contributors receive medal emojis: 🥇 🥈 🥉

#### CodeRabbit Discussion Tracking

The bot tracks discussions with CodeRabbit AI to encourage thoughtful code review engagement. This feature is configurable:

**Environment Variables:**

- `CR_DISCUSSION_MODE`: How to handle CodeRabbit discussions
  - `visible` (default): Shows discussion count in leaderboard table
  - `hidden`: Counts toward points but hidden from table
  - `separate`: Tracked separately, not scored

- `CR_DISCUSSION_POINTS`: Points per counted discussion
  - Default: `0` (visible tracking only, no points)
  - Set to positive integer to award points

- `CR_DISCUSSION_DAILY_CAP`: Maximum discussions counted per user per UTC day
  - Default: `7`
  - Prevents gaming the system through spam

**Anti-Abuse Protection:** Daily cap per user ensures quality over quantity in AI discussions.

#### Anti-Abuse Features

The leaderboard includes several safeguards:

1. **Bot Detection** - Automatically excludes bot accounts (GitHub Apps, Dependabot, Copilot, etc.)
2. **Open PR Limit** - Auto-closes new PRs if a user has 50+ open PRs (prevents PR spam)
3. **Daily Caps** - Limits on CodeRabbit discussions prevent point farming
4. **Review Limits** - Only first two reviews per PR count (encourages reviewing different PRs)

#### Technical Details

- **Workflow File**: `.github/workflows/leaderboard-bot.yml`
- **Trigger**: Runs on `pull_request_target` when a PR is opened
- **Security**: Uses base repo permissions; does not check out or execute PR code
- **Permissions**: `contents: read`, `pull-requests: write`, `issues: write`
- **Data Source**: GitHub GraphQL API and REST API
- **Timezone**: All dates use UTC for consistency

#### Configuring the Leaderboard

To modify leaderboard behavior, edit environment variables in `.github/workflows/leaderboard-bot.yml`:

```yaml
env:
  CR_DISCUSSION_MODE: visible    # visible | hidden | separate
  CR_DISCUSSION_POINTS: '0'      # Points per discussion
  CR_DISCUSSION_DAILY_CAP: '7'   # Daily limit per user
```

#### Viewing Your Stats

Your leaderboard stats are automatically posted when you open a PR. The comment shows:

- Your current rank for the month
- The user directly above you (if not #1)
- The user directly below you (if not last)
- Medal emoji if you're in the top 3
- Detailed breakdown of your points by category

The leaderboard updates monthly, with rankings reset at the start of each month (UTC).

---

## 💬 Community & Support

- 🌐 **Website**: [owaspblt.org](https://owaspblt.org)
- 💬 **Slack**: [Join OWASP Slack](https://owasp.org/slack/invite)
- 🐦 **Twitter**: [@OWASP_BLT](https://x.com/OWASP_BLT)
- 💰 **Sponsor**: [Support the project](https://github.com/sponsors/OWASP-BLT)
- 📧 **Contact**: Reach out through GitHub issues

---

## 📈 Star History

<a href="https://star-history.com/#OWASP-BLT/BLT&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=OWASP-BLT/BLT&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=OWASP-BLT/BLT&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=OWASP-BLT/BLT&type=Date" />
 </picture>
</a>

---

## 📄 License

This project is licensed under the **AGPL-3.0 License** - see the [LICENSE.md](LICENSE.md) file for details.

---

<p align="center">
  <strong>⭐ Star this repository if you find it helpful!</strong><br>
  Made with ❤️ by the OWASP BLT Community
</p>
