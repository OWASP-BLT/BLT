# VPS Deployment Guide

This guide covers deploying BLT on a VPS using Ansible automation with Django 6.0 Tasks framework.

## Prerequisites

### VPS Requirements
- Ubuntu 22.04 LTS or newer
- Minimum 2 GB RAM
- 20 GB disk space
- Root or sudo access
- Public IP address and domain name

### Local Machine Requirements
- Ansible 2.12 or newer
- SSH access to the VPS
- GitHub account with repository access

## Step 1: VPS Initial Setup

### 1.1 Connect to VPS
```bash
ssh root@your-vps-ip
