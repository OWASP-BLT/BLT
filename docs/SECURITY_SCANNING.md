# Security Scanning Documentation

This document describes the security scanning tools and workflows implemented in the OWASP BLT project.

## Overview

The BLT project uses multiple layers of automated security scanning to detect vulnerabilities, security issues, and potential threats in the codebase, dependencies, and infrastructure.

## Security Scanning Tools

### 1. CodeQL (GitHub Native)

**Purpose**: Advanced semantic code analysis for security vulnerabilities

**Configuration**: `.github/workflows/codeql.yml`

**Features**:
- Scans Python, JavaScript/TypeScript, and GitHub Actions
- Uses `security-extended` and `security-and-quality` query suites
- Runs on every push, pull request, and weekly schedule
- Results appear in GitHub Security tab

**Languages Scanned**:
- Python (Django backend)
- JavaScript/TypeScript (frontend)
- GitHub Actions (workflow security)

### 2. Bandit

**Purpose**: Python-specific security linter

**Configuration**: `.bandit`

**Features**:
- Detects common security issues in Python code
- Checks for hardcoded passwords, SQL injection risks, etc.
- Excludes tests and migrations from scanning
- Reports are uploaded as workflow artifacts

**Example Issues Detected**:
- Use of `assert` in production code
- Insecure cryptographic functions
- SQL injection vulnerabilities
- Hardcoded secrets

**Running Locally**:
```bash
# Install Bandit
pip install bandit[toml]

# Run scan
bandit -r website/ blt/

# Use configuration file
bandit -r website/ blt/ -c .bandit
```

### 3. Dependency Scanning

**Tools**: pip-audit, Dependabot, OSV Scanner

**Configuration**: 
- `.github/dependabot.yml`
- Workflow: `.github/workflows/security-scanning.yml`

**Features**:
- **pip-audit**: Scans Python dependencies for known vulnerabilities
- **Dependabot**: Automated dependency updates with security patches
- **OSV Scanner**: Cross-ecosystem vulnerability scanning using Google's OSV database

**Ecosystems Monitored**:
- Python packages (daily scans)
- Docker base images (weekly scans)
- GitHub Actions (weekly scans)

**Running pip-audit Locally**:
```bash
# Install pip-audit
pip install pip-audit

# Scan installed packages
poetry run pip-audit

# Get detailed report
poetry run pip-audit --desc
```

### 4. Semgrep

**Purpose**: Static Application Security Testing (SAST)

**Configuration**: Auto-configured in workflow

**Features**:
- Language-agnostic security rules
- Detects security patterns and anti-patterns
- Uses community and pro rules
- Fast and accurate analysis

**Running Locally**:
```bash
# Install Semgrep
pip install semgrep

# Run with auto-config
semgrep scan --config=auto .

# Run with specific rulesets
semgrep scan --config=p/security-audit .
```

### 5. Gitleaks

**Purpose**: Secret detection and prevention

**Configuration**: `.gitleaks.toml`

**Features**:
- Scans for hardcoded secrets, API keys, passwords
- Checks entire git history
- Configurable allowlists for false positives
- Prevents secret leakage

**Types of Secrets Detected**:
- AWS keys
- GitHub tokens
- API keys and tokens
- Private SSH keys
- Database passwords
- OAuth tokens

**Running Locally**:
```bash
# Install Gitleaks
brew install gitleaks  # macOS
# or download from https://github.com/gitleaks/gitleaks/releases

# Scan entire repository
gitleaks detect --source . -v

# Use custom config
gitleaks detect --config .gitleaks.toml -v
```

### 6. Trivy

**Purpose**: Vulnerability scanning for infrastructure and dependencies

**Configuration**: Workflow automation

**Features**:
- **Repository Scan**: Scans filesystem for vulnerabilities
- **Docker Image Scan**: Scans Docker images for CVEs
- Detects misconfigurations
- Integrates with GitHub Security tab (SARIF reports)

**Vulnerability Levels**:
- CRITICAL: Immediate action required
- HIGH: Should be fixed soon
- MEDIUM: Fix when possible

**Running Locally**:
```bash
# Install Trivy
brew install trivy  # macOS
# or see https://aquasecurity.github.io/trivy/latest/getting-started/installation/

# Scan repository
trivy fs .

# Scan Docker image
docker build -t blt-app .
trivy image blt-app

# Scan with specific severity
trivy fs --severity CRITICAL,HIGH .
```

## Workflow Configuration

### Security Scanning Workflow

**File**: `.github/workflows/security-scanning.yml`

**Triggers**:
- Every push to `main` branch
- Every pull request to `main` branch
- Weekly schedule (Mondays at 8:00 AM UTC)
- Manual workflow dispatch

**Jobs**:
1. **Bandit**: Python security linting
2. **Dependency Check**: pip-audit vulnerability scanning
3. **Semgrep**: SAST analysis
4. **GitLeaks**: Secret scanning
5. **Trivy Repo**: Repository vulnerability scan
6. **Trivy Docker**: Docker image vulnerability scan
7. **OSV Scanner**: Cross-ecosystem vulnerability detection
8. **Security Summary**: Aggregated results

### CodeQL Workflow

**File**: `.github/workflows/codeql.yml`

**Triggers**:
- Every push to `main` branch
- Every pull request to `main` branch
- Weekly schedule (Fridays at 8:40 PM UTC)

## Viewing Security Results

### GitHub Security Tab

1. Navigate to the repository
2. Click on the "Security" tab
3. Select "Code scanning" for CodeQL and Trivy results
4. Select "Dependabot" for dependency alerts

### Workflow Artifacts

Security scan reports are uploaded as workflow artifacts:
1. Go to the Actions tab
2. Select a completed workflow run
3. Download artifacts from the bottom of the page

**Available Artifacts**:
- `bandit-report.json`: Bandit security findings
- `pip-audit-report.json`: Dependency vulnerabilities
- `semgrep-report.json`: Semgrep analysis results
- `osv-scanner-results.json`: OSV vulnerability database results

### Pull Request Comments

Some security checks provide inline comments on pull requests:
- CodeQL alerts for new issues
- Dependency vulnerability warnings

## Best Practices

### For Developers

1. **Run security scans locally** before pushing code
2. **Fix high and critical issues** immediately
3. **Review security alerts** in pull requests
4. **Keep dependencies updated** through Dependabot
5. **Never commit secrets** - use environment variables

### For Maintainers

1. **Review security scan results** weekly
2. **Triage and prioritize** security findings
3. **Update security tools** regularly
4. **Configure allowlists** for false positives
5. **Document security decisions** in issues

## Configuration Files

- `.bandit` - Bandit security linter configuration
- `.gitleaks.toml` - Gitleaks secret scanning configuration
- `.github/dependabot.yml` - Dependabot configuration
- `.github/workflows/security-scanning.yml` - Security scanning workflow
- `.github/workflows/codeql.yml` - CodeQL analysis workflow

## Troubleshooting

### False Positives

If a security tool reports a false positive:

1. **Bandit**: Add `# nosec` comment with explanation
   ```python
   password = get_from_env()  # nosec B105 - not a hardcoded password
   ```

2. **Gitleaks**: Add path or regex to `.gitleaks.toml` allowlist

3. **Semgrep**: Create `.semgrepignore` file or use inline comments

4. **CodeQL**: Dismiss alert in GitHub Security tab with justification

### Performance Issues

If scans take too long:

1. **Bandit**: Exclude unnecessary directories in `.bandit`
2. **Trivy**: Use `--skip-dirs` or `--skip-files` flags
3. **Semgrep**: Use specific rulesets instead of `--config=auto`

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [GitHub Security Features](https://docs.github.com/en/code-security)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Semgrep Rules](https://semgrep.dev/explore)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Gitleaks Documentation](https://github.com/gitleaks/gitleaks)

## Support

For questions or issues with security scanning:
1. Check existing GitHub issues
2. Create a new issue with the `security` label
3. Contact the security team

---

*This documentation is maintained alongside the security scanning workflows and configurations.*
