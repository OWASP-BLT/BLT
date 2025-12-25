# Security Policy

## Reporting Security Issues

Please report security issues for BLT through [GitHub Security Advisories](https://github.com/OWASP-BLT/BLT/security/advisories/new).

For more details on our security disclosure process, please see our [Contributing Guidelines](CONTRIBUTING.md).

## Automated Security Scanning

This repository uses multiple automated security scanning tools to detect and prevent vulnerabilities:

- **CodeQL**: Advanced semantic code analysis
- **Bandit**: Python security linting
- **Semgrep**: Static application security testing (SAST)
- **Gitleaks**: Secret detection and prevention
- **Trivy**: Vulnerability scanning for code and Docker images
- **Dependabot**: Automated dependency updates with security patches
- **OSV Scanner**: Cross-ecosystem vulnerability detection

For detailed information about our security scanning setup, see [Security Scanning Documentation](docs/SECURITY_SCANNING.md).

## Security Best Practices

When contributing to BLT:

1. **Never commit secrets** - Use environment variables and the `.env` file
2. **Keep dependencies updated** - Review and merge Dependabot PRs promptly
3. **Fix security issues** - Address high and critical security findings immediately
4. **Run security scans locally** - Test your code before pushing
5. **Follow secure coding practices** - See [OWASP guidelines](https://owasp.org/)
