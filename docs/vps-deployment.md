# VPS Deployment Guide for BLT using Ansible Automation with Django 6.0 Tasks

> [!WARNING]
> **Maintainer-Owned Deployment Guide**
> 
> This guide is a **proposal/template** for production VPS deployment. All production deployments must be performed by project maintainers with appropriate infrastructure access, credentials, and authorization. Contributors should use this as reference documentation only.
> 
> See environment configuration template at: [`docs/examples/.env.production.example`](examples/.env.production.example)

---

## ⚠️ Ownership & Access

**This deployment is maintainer-owned and requires privileged access.**

The following steps **must be performed by project maintainers** with appropriate access:

### Maintainer-Only Responsibilities

1. **Infrastructure Access**
   - VPS provisioning and root/sudo access
   - DNS management and domain configuration
   - SSL certificate management

2. **Secrets Management**
   - `SECRET_KEY` generation and secure storage
   - Database credentials configuration
   - API keys and OAuth client secrets (GitHub, OpenAI, etc.)
   - Email service credentials
   - Sentry DSN and monitoring tokens

3. **Deployment Execution**
   - Ansible inventory configuration
   - Initial deployment and service setup
   - Production database migrations
   - Backup and disaster recovery setup

4. **Ongoing Operations**
   - Security updates and patches
   - Monitoring and incident response
   - Access control and user management

### For Contributors

If you're a contributor:
- Use this guide as **reference documentation** only
- Do **not** attempt to deploy to production infrastructure
- For testing, set up a local development environment or personal VPS
- Consult with maintainers before proposing infrastructure changes

### Maintainer Contact

For deployment-related questions or access requests, contact the repository maintainers through GitHub issues with the `infrastructure` label.

---

## Table of Contents

1. [Prerequisites](`#prerequisites`)
2. [Initial Setup](`#initial-setup`)
   - [Connect to VPS](`#1-connect-to-vps`)
   - [System Update](`#2-system-update`)
   - [Install Dependencies](`#3-install-system-dependencies`)
3. [Database Setup](`#database-setup`)
4. [Redis Setup](`#redis-setup`)
5. [Application Deployment](`#application-deployment`)
6. [Web Server Configuration](`#web-server-configuration`)
7. [SSL Certificate Setup](`#ssl-certificate-setup`)
8. [Systemd Services](`#systemd-services`)
9. [Monitoring and Logging](`#monitoring-and-logging`)
10. [Security Hardening](`#security-hardening`)
11. [Backup and Disaster Recovery](`#backup-and-disaster-recovery`)
12. [Troubleshooting](`#troubleshooting`)
13. [Performance Tuning](`#performance-tuning`)
14. [CI/CD Integration](`#cicd-integration`)
15. [Deployment Checklist](`#deployment-checklist`)
16. [Contributing to This Guide](`#contributing-to-this-guide`)

---

## Prerequisites

### VPS Requirements
- Ubuntu 22.04 LTS or later
- Minimum 2GB RAM (4GB recommended)
- 20GB disk space minimum
- Root or sudo access
- Public IP address

### Local Machine Requirements
- Ansible 2.9+
- SSH access to VPS
- Git

### Domain Requirements
- Domain name configured with DNS pointing to VPS IP
- Access to DNS management

---

## Initial Setup

### 1. Connect to VPS

```bash
# Replace with your VPS IP and user
ssh root@your-vps-ip

# Or if using SSH key
ssh -i /path/to/private-key root@your-vps-ip
