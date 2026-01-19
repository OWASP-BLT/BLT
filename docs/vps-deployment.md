# VPS Deployment Guide

This guide covers deploying BLT on a VPS using Ansible automation with Django 6.0 Tasks framework.

**Note:** This is a proposal/template for maintainer-owned VPS migration. Actual deployment should be performed by project maintainers who have access to production credentials and infrastructure.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
   - [Connect to VPS](#1-connect-to-vps)
   - [System Update](#2-system-update)
   - [Install Dependencies](#3-install-system-dependencies)
3. [Database Setup](#database-setup)
4. [Redis Setup](#redis-setup)
5. [Application Deployment](#application-deployment)
6. [Web Server Configuration](#web-server-configuration)
7. [SSL Certificate Setup](#ssl-certificate-setup)
8. [Django 6.0 Tasks & Systemd Services](#systemd-services)
9. [Monitoring and Logging](#monitoring-and-logging)
10. [Security Hardening](#security-hardening)
11. [Backup and Disaster Recovery](#backup-and-disaster-recovery)
12. [Troubleshooting](#troubleshooting)
13. [Performance Tuning](#performance-tuning)
14. [CI/CD Integration](#cicd-integration)

---

## Prerequisites

### VPS Requirements
- Ubuntu 22.04 LTS or newer
- Minimum 2 GB RAM (4 GB recommended)
- 20 GB disk space
- Root or sudo access
- Public IP address and domain name

### Local Machine Requirements
- Ansible 2.12 or newer
- SSH access to the VPS
- GitHub account with repository access

### Domain Requirements
- Domain name pointed to VPS IP address
- DNS A records configured for primary domain and www subdomain

---

## Initial Setup

### 1. Connect to VPS

```bash
ssh root@your-vps-ip
2. System Update
# Update package lists and upgrade existing packages
sudo apt update && sudo apt upgrade -y

# Install essential build tools
sudo apt install -y build-essential git curl wget vim
3. Install System Dependencies
# Install Python 3.12 and pip
sudo apt install -y python3.12 python3.12-venv python3-pip

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib libpq-dev

# Install Redis
sudo apt install -y redis-server

# Install Nginx
sudo apt install -y nginx

# Install Certbot for SSL
sudo apt install -y certbot python3-certbot-nginx

# Install additional tools
sudo apt install -y htop net-tools ufw fail2ban