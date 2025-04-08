// Define the compliance criteria (100-point checklist)
export const criteria = [
  {
    id: "gc",
    name: "General Compliance & Governance",
    checkpoints: [
      {
        id: "gc-1",
        description: "Clearly defined project goal and scope",
        recommendation: "Add a clear project description section in your README.md file"
      },
      {
        id: "gc-2",
        description: "Open-source license is included in a LICENSE file",
        recommendation: "Add a LICENSE file with an appropriate open-source license"
      },
      {
        id: "gc-3",
        description: "README file provides an overview of the project",
        recommendation: "Create a comprehensive README.md file with project overview"
      },
      {
        id: "gc-4",
        description: "Follows OWASP best practices and standards",
        recommendation: "Review and implement OWASP best practices in your development process"
      },
      {
        id: "gc-5",
        description: "Clear contribution guidelines (CONTRIBUTING.md)",
        recommendation: "Add a CONTRIBUTING.md file with guidelines for contributors"
      },
      {
        id: "gc-6",
        description: "Issue tracker is actively monitored",
        recommendation: "Enable and actively monitor the Issues section on GitHub"
      },
      {
        id: "gc-7",
        description: "Maintainers respond to pull requests within a reasonable timeframe",
        recommendation: "Establish a process to review and respond to pull requests"
      },
      {
        id: "gc-8",
        description: "Code of Conduct (CODE_OF_CONDUCT.md) is present",
        recommendation: "Add a CODE_OF_CONDUCT.md file to set community expectations"
      },
      {
        id: "gc-9",
        description: "Project roadmap or milestones are documented",
        recommendation: "Add project roadmap or milestones to communicate future plans"
      },
      {
        id: "gc-10",
        description: "The project is well-governed with active maintainers",
        recommendation: "Establish a clear governance model and ensure regular updates"
      }
    ]
  },
  {
    id: "du",
    name: "Documentation & Usability",
    checkpoints: [
      {
        id: "du-1",
        description: "Well-structured README.md with introduction and installation guide",
        recommendation: "Improve your README.md with a clear introduction and installation instructions"
      },
      {
        id: "du-2",
        description: "Clear usage examples are provided",
        recommendation: "Add usage examples to your documentation"
      },
      {
        id: "du-3",
        description: "A well-maintained wiki or detailed docs/ directory",
        recommendation: "Create a docs directory or wiki with detailed documentation"
      },
      {
        id: "du-4",
        description: "API documentation is available (Swagger/OpenAPI for APIs)",
        recommendation: "Add API documentation using Swagger/OpenAPI"
      },
      {
        id: "du-5",
        description: "Proper inline comments within the source code",
        recommendation: "Improve code comments to explain complex logic"
      },
      {
        id: "du-6",
        description: "All scripts and configuration files are documented",
        recommendation: "Document all scripts and configuration files"
      },
      {
        id: "du-7",
        description: "FAQ section or troubleshooting guide",
        recommendation: "Add a FAQ or troubleshooting section to help users"
      },
      {
        id: "du-8",
        description: "Well-defined error messages",
        recommendation: "Implement clear, actionable error messages"
      },
      {
        id: "du-9",
        description: "Clear versioning strategy (e.g., SemVer)",
        recommendation: "Adopt semantic versioning (SemVer) for your releases"
      },
      {
        id: "du-10",
        description: "Change log (CHANGELOG.md) is maintained",
        recommendation: "Create and maintain a CHANGELOG.md file"
      }
    ]
  },
  {
    id: "cq",
    name: "Code Quality & Best Practices",
    checkpoints: [
      {
        id: "cq-1",
        description: "Code follows industry-standard style guides",
        recommendation: "Implement a code style guide and linting rules"
      },
      {
        id: "cq-2",
        description: "Uses linters (ESLint, Pylint, etc.)",
        recommendation: "Add linting tools to your project"
      },
      {
        id: "cq-3",
        description: "Code is modular and maintainable",
        recommendation: "Refactor code to improve modularity"
      },
      {
        id: "cq-4",
        description: "Adheres to DRY (Don't Repeat Yourself) principle",
        recommendation: "Refactor duplicate code into reusable functions"
      },
      {
        id: "cq-5",
        description: "Secure coding practices are followed",
        recommendation: "Review code for secure coding practices"
      },
      {
        id: "cq-6",
        description: "No hardcoded credentials, secrets, or API keys",
        recommendation: "Remove hardcoded credentials and use environment variables"
      },
      {
        id: "cq-7",
        description: "Uses parameterized queries to prevent SQL injection",
        recommendation: "Implement parameterized queries for database operations"
      },
      {
        id: "cq-8",
        description: "Cryptographic functions use strong algorithms",
        recommendation: "Update cryptographic functions to use modern algorithms"
      },
      {
        id: "cq-9",
        description: "Input validation and sanitization are implemented",
        recommendation: "Implement input validation for all user inputs"
      },
      {
        id: "cq-10",
        description: "Output encoding is used to prevent XSS",
        recommendation: "Implement output encoding to prevent XSS attacks"
      }
    ]
  },
  {
    id: "sc",
    name: "Security & OWASP Compliance",
    checkpoints: [
      {
        id: "sc-1",
        description: "No known security vulnerabilities in dependencies",
        recommendation: "Implement dependency scanning and update vulnerable packages"
      },
      {
        id: "sc-2",
        description: "No third-party tracking scripts or malware",
        recommendation: "Remove unauthorized third-party scripts"
      },
      {
        id: "sc-3",
        description: "Uses secure headers (CSP, HSTS, X-Frame-Options, etc.)",
        recommendation: "Implement security headers like CSP, HSTS, X-Frame-Options"
      },
      {
        id: "sc-4",
        description: "Input validation is enforced",
        recommendation: "Strengthen input validation mechanisms"
      },
      {
        id: "sc-5",
        description: "Implements RBAC (Role-Based Access Control) where applicable",
        recommendation: "Implement role-based access control"
      },
      {
        id: "sc-6",
        description: "Secure authentication mechanisms (e.g., OAuth, JWT)",
        recommendation: "Implement secure authentication mechanisms"
      },
      {
        id: "sc-7",
        description: "Secrets are stored securely",
        recommendation: "Use environment variables or a secrets manager"
      },
      {
        id: "sc-8",
        description: "Uses HTTPS for all network communication",
        recommendation: "Enforce HTTPS for all communications"
      },
      {
        id: "sc-9",
        description: "Adheres to OWASP ASVS (Application Security Verification Standard)",
        recommendation: "Review project against OWASP ASVS requirements"
      },
      {
        id: "sc-10",
        description: "Secure cookie attributes (HttpOnly, Secure, SameSite)",
        recommendation: "Set secure attributes on cookies"
      },
      {
        id: "sc-11",
        description: "No unnecessary ports or services exposed",
        recommendation: "Close unnecessary ports and disable unused services"
      },
      {
        id: "sc-12",
        description: "Proper logging of security-related events",
        recommendation: "Implement comprehensive security event logging"
      },
      {
        id: "sc-13",
        description: "Uses least privilege principle for access control",
        recommendation: "Implement least privilege principle throughout the application"
      },
      {
        id: "sc-14",
        description: "No unsafe dependencies or outdated packages",
        recommendation: "Update outdated dependencies"
      },
      {
        id: "sc-15",
        description: "Complies with OWASP Top 10 security risks",
        recommendation: "Review and mitigate OWASP Top 10 risks"
      }
    ]
  },
  {
    id: "cicd",
    name: "CI/CD & DevSecOps",
    checkpoints: [
      {
        id: "cicd-1",
        description: "Automated unit tests are implemented",
        recommendation: "Implement automated unit tests"
      },
      {
        id: "cicd-2",
        description: "Continuous Integration (CI) is in place",
        recommendation: "Set up CI/CD pipeline with GitHub Actions or another tool"
      },
      {
        id: "cicd-3",
        description: "CI/CD pipeline includes security scanning (SAST, DAST)",
        recommendation: "Add security scanning to your CI/CD pipeline"
      },
      {
        id: "cicd-4",
        description: "Dependency scanning is automated",
        recommendation: "Add automated dependency scanning to your workflow"
      },
      {
        id: "cicd-5",
        description: "Code coverage reports are generated",
        recommendation: "Generate and review code coverage reports"
      },
      {
        id: "cicd-6",
        description: "Uses container security scanning",
        recommendation: "Implement container security scanning"
      },
      {
        id: "cicd-7",
        description: "Infrastructure as Code (IaC) security checks",
        recommendation: "Add security checks for Infrastructure as Code"
      },
      {
        id: "cicd-8",
        description: "Secure secrets management in CI/CD",
        recommendation: "Implement secure secrets management in CI/CD"
      },
      {
        id: "cicd-9",
        description: "Environment-specific configurations are properly managed",
        recommendation: "Improve environment configuration management"
      },
      {
        id: "cicd-10",
        description: "Rollback mechanisms are in place",
        recommendation: "Implement deployment rollback mechanisms"
      }
    ]
  },
  {
    id: "tv",
    name: "Testing & Validation",
    checkpoints: [
      {
        id: "tv-1",
        description: "Test cases cover edge cases and security scenarios",
        recommendation: "Add test cases for edge cases and security scenarios"
      },
      {
        id: "tv-2",
        description: "Uses unit, integration, and end-to-end (E2E) testing",
        recommendation: "Implement comprehensive testing strategy"
      },
      {
        id: "tv-3",
        description: "Mocks and stubs are used for external services",
        recommendation: "Use mocks and stubs for testing external dependencies"
      },
      {
        id: "tv-4",
        description: "Code achieves at least 80% test coverage",
        recommendation: "Increase test coverage to at least 80%"
      },
      {
        id: "tv-5",
        description: "Tests validate input sanitization",
        recommendation: "Add tests for input validation and sanitization"
      },
      {
        id: "tv-6",
        description: "Automated fuzz testing is used for security inputs",
        recommendation: "Implement fuzz testing for security-critical inputs"
      },
      {
        id: "tv-7",
        description: "Fails gracefully and logs meaningful error messages",
        recommendation: "Improve error handling and logging"
      },
      {
        id: "tv-8",
        description: "No sensitive data is exposed in logs",
        recommendation: "Review logs to ensure sensitive data is not exposed"
      },
      {
        id: "tv-9",
        description: "Uses dependency injection for better testability",
        recommendation: "Implement dependency injection patterns"
      },
      {
        id: "tv-10",
        description: "Regression tests ensure backward compatibility",
        recommendation: "Add regression tests to ensure backward compatibility"
      }
    ]
  },
  {
    id: "ps",
    name: "Performance & Scalability",
    checkpoints: [
      {
        id: "ps-1",
        description: "Code is optimized for performance",
        recommendation: "Perform code optimization for better performance"
      },
      {
        id: "ps-2",
        description: "Asynchronous processing is used where needed",
        recommendation: "Implement asynchronous processing for long-running tasks"
      },
      {
        id: "ps-3",
        description: "Implements caching strategies where appropriate",
        recommendation: "Implement caching mechanisms"
      },
      {
        id: "ps-4",
        description: "Database queries are optimized",
        recommendation: "Optimize database queries and indexes"
      },
      {
        id: "ps-5",
        description: "Uses rate limiting to prevent abuse",
        recommendation: "Implement rate limiting to prevent abuse"
      },
      {
        id: "ps-6",
        description: "No excessive memory leaks or resource consumption",
        recommendation: "Fix memory leaks and optimize resource usage"
      },
      {
        id: "ps-7",
        description: "Uses load testing tools (JMeter, k6)",
        recommendation: "Implement load testing with appropriate tools"
      },
      {
        id: "ps-8",
        description: "Supports horizontal scaling",
        recommendation: "Design for horizontal scalability"
      },
      {
        id: "ps-9",
        description: "Uses lazy loading where possible",
        recommendation: "Implement lazy loading for resource-intensive components"
      },
      {
        id: "ps-10",
        description: "Uses pagination for large datasets",
        recommendation: "Implement pagination for large datasets"
      }
    ]
  },
  {
    id: "lm",
    name: "Logging & Monitoring",
    checkpoints: [
      {
        id: "lm-1",
        description: "Logging is implemented for key events",
        recommendation: "Implement comprehensive logging"
      },
      {
        id: "lm-2",
        description: "Log levels are configurable (INFO, DEBUG, ERROR)",
        recommendation: "Add configurable log levels"
      },
      {
        id: "lm-3",
        description: "Logs do not contain sensitive data",
        recommendation: "Review logs to ensure sensitive data is not exposed"
      },
      {
        id: "lm-4",
        description: "Integrates with monitoring tools",
        recommendation: "Add monitoring tool integration"
      },
      {
        id: "lm-5",
        description: "Uses structured logging (JSON, etc.)",
        recommendation: "Implement structured logging format"
      },
      {
        id: "lm-6",
        description: "Audit logs track security-related actions",
        recommendation: "Implement audit logging for security events"
      },
      {
        id: "lm-7",
        description: "Alerts are configured for anomalies",
        recommendation: "Set up alerts for unusual activity"
      },
      {
        id: "lm-8",
        description: "Supports log rotation and archival",
        recommendation: "Implement log rotation and archival"
      },
      {
        id: "lm-9",
        description: "Incident response playbook is defined",
        recommendation: "Create an incident response playbook"
      },
      {
        id: "lm-10",
        description: "Logging configuration is separate from code",
        recommendation: "Separate logging configuration from application code"
      }
    ]
  },
  {
    id: "cs",
    name: "Community & Support",
    checkpoints: [
      {
        id: "cs-1",
        description: "Maintainers actively engage with contributors",
        recommendation: "Increase engagement with community contributors"
      },
      {
        id: "cs-2",
        description: "Clear process for reporting security vulnerabilities",
        recommendation: "Define a clear security vulnerability reporting process"
      },
      {
        id: "cs-3",
        description: "Security policy file (SECURITY.md) is available",
        recommendation: "Add a SECURITY.md file with vulnerability reporting procedures"
      },
      {
        id: "cs-4",
        description: "Community guidelines encourage constructive discussion",
        recommendation: "Establish community guidelines for constructive discussion"
      },
      {
        id: "cs-5",
        description: "Responsive to security issues raised by the community",
        recommendation: "Improve response time for security issues"
      },
      {
        id: "cs-6",
        description: "Regular project updates (at least once per year)",
        recommendation: "Establish a regular update schedule"
      },
      {
        id: "cs-7",
        description: "Provides multiple support channels",
        recommendation: "Provide additional support channels (Slack, Discord, etc.)"
      },
      {
        id: "cs-8",
        description: "Clear escalation path for security concerns",
        recommendation: "Define a clear escalation path for security concerns"
      },
      {
        id: "cs-9",
        description: "Pull request reviews are done before merging",
        recommendation: "Enforce code review before merging pull requests"
      },
      {
        id: "cs-10",
        description: "Maintains good issue tracking hygiene",
        recommendation: "Improve issue tracking and management"
      }
    ]
  },
  {
    id: "lc",
    name: "Legal & Compliance",
    checkpoints: [
      {
        id: "lc-1",
        description: "Follows data protection laws (GDPR, CCPA)",
        recommendation: "Review compliance with data protection regulations"
      },
      {
        id: "lc-2",
        description: "Third-party dependencies are properly licensed",
        recommendation: "Audit and document third-party dependency licenses"
      },
      {
        id: "lc-3",
        description: "No proprietary or restricted code is included",
        recommendation: "Remove any proprietary or restricted code"
      },
      {
        id: "lc-4",
        description: "Users are informed of data collection practices",
        recommendation: "Add clear data collection and privacy disclosures"
      },
      {
        id: "lc-5",
        description: "Project adheres to responsible disclosure policies",
        recommendation: "Implement responsible disclosure policies"
      }
    ]
  }
];
