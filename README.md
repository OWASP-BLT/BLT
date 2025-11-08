<h1 align="center"> 🐛 OWASP BLT </h1>
<h3 align="center">Bug Logging Tool - Democratizing Bug Bounties</h3>

<p align="center">
  <strong>A community-driven platform for discovering, reporting, and tracking security vulnerabilities</strong>
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
  <a href="https://github.com/OWASP-BLT/BLT/actions">
    <img src="https://github.com/OWASP-BLT/BLT/actions/workflows/auto-merge.yml/badge.svg" alt="Build Status">
  </a>
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

**OWASP BLT (Bug Logging Tool)** is an open-source platform that democratizes bug bounties and security research. Built by the community for the community, BLT makes it easy for security researchers, developers, and organizations to collaborate on finding and fixing security vulnerabilities.

### ✨ Key Features

- 🔍 **Bug Discovery & Reporting** - Discover and report security vulnerabilities across various applications and websites
- 🏆 **Rewards & Recognition** - Earn rewards, badges, and recognition for your contributions to web security
- 👥 **Community Driven** - Join a vibrant community of security researchers and developers
- 🎮 **Gamification** - Leaderboards, challenges, and competitions to make security research engaging
- 💰 **Staking System** - Innovative blockchain-based reward system for contributors
- 📊 **Comprehensive Dashboard** - Track your progress, statistics, and impact
- 🔥 **Sizzle Plugin** - Daily check-ins, time tracking, and team productivity tools ([Learn more](sizzle/README.md))
- 🌐 **Open Source** - Built with transparency and collaboration at its core
- 🛡️ **OWASP Project** - Part of the Open Worldwide Application Security Project family

---

## � Featured Plugins

BLT includes powerful plugins to enhance team productivity and collaboration:

### Sizzle - Daily Check-ins & Time Tracking
A comprehensive productivity plugin featuring:
- 📝 **Daily Status Reports** - Structured team check-ins and progress tracking
- ⏰ **Time Tracking** - Log work sessions with GitHub issue integration  
- 🔔 **Smart Reminders** - Configurable daily reminder notifications
- 📊 **Team Analytics** - Monitor productivity and engagement metrics
- 🎯 **Streak Tracking** - Maintain daily check-in streaks for motivation

**📖 [View Sizzle Documentation](sizzle/README.md)** | **🌐 Access at**: `/sizzle/`

---

## �🚀 Quick Start

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

**🔥 Sizzle Plugin**: Access the productivity tools at **http://localhost:8000/sizzle/**

#### Using Poetry
```bash
# Install dependencies
pip install poetry
poetry shell
poetry install

# Set up database
python manage.py migrate
python manage.py loaddata website/fixtures/initial_data.json
python manage.py createsuperuser

# Run the server
python manage.py runserver
```

For detailed setup instructions, see our [Contributing Guide](https://github.com/OWASP-BLT/BLT/blob/main/CONTRIBUTING.md).

---

## 🤝 Contributing

We welcome contributions from everyone! Whether you're fixing bugs, adding features, improving documentation, or spreading the word, your help is appreciated.

- 📚 Read our [Contributing Guide](https://github.com/OWASP-BLT/BLT/blob/main/CONTRIBUTING.md)
- 🐛 Check out [open issues](https://github.com/OWASP-BLT/BLT/issues)
- 💡 Look for issues tagged with `good first issue` if you're new
- 🎨 Follow our coding standards (Black, isort, ruff)
- ✅ Run `pre-commit` before submitting changes

---

## 💬 Community & Support

- 🌐 **Website**: [owaspblt.org](https://owaspblt.org)
- 💬 **Slack**: [Join OWASP Slack](https://owasp.org/slack/invite)
- 🐦 **Twitter**: [@OWASP_BLT](https://twitter.com/OWASP_BLT)
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
