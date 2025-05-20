# OWASP BLT Remote Setup Guide

This guide explains how to set up the OWASP BLT project on a remote VPS (Virtual Private Server).

## Prerequisites

- A VPS running Ubuntu 20.04 or newer (the script may work on other Debian-based distributions)
- Root access to the server
- A domain name pointed to your server IP (recommended for production use)

## Quick Setup

The easiest way to set up OWASP BLT on your server is to use the provided `remote_setup.sh` script.

### 1. Download the script

```bash
curl -O https://raw.githubusercontent.com/OWASP-BLT/BLT/main/remote_setup.sh
chmod +x remote_setup.sh
```

### 2. Run the script

For a basic setup with HTTP:

```bash
sudo ./remote_setup.sh
```

For production setup with HTTPS (recommended):

```bash
sudo ./remote_setup.sh --domain yourdomain.com --email your@email.com --https
```

## Script Options

The script supports several options to customize your installation:

```
Usage: ./remote_setup.sh [OPTIONS]

Options:
  -d, --domain DOMAIN       Domain name for the website (required for HTTPS)
  -e, --email EMAIL         Email for Let's Encrypt certificate (required for HTTPS)
  -i, --install-dir DIR     Installation directory (default: /opt/blt)
  -p, --port PORT           HTTP port (default: 8000)
  -s, --https               Enable HTTPS with Let's Encrypt
  --db-port PORT            PostgreSQL port (default: 5432)
  --db-user USER            PostgreSQL username (default: postgres)
  --db-name NAME            PostgreSQL database name (default: blt_db)
  --db-password PASSWORD    PostgreSQL password (default: random generated)
  -h, --help                Show this help message
```

## After Installation

After the script completes, you'll receive instructions for accessing your BLT installation. Make sure to:

1. Change the default admin password
2. Configure OAuth providers (GitHub, Google, etc.) as needed
3. Add a domain in the admin panel with the name 'owasp.org'

## Managing Your Installation

### Viewing Logs

```bash
cd /opt/blt
docker-compose logs -f
```

### Restarting the Application

```bash
sudo systemctl restart blt
```

### Updating to the Latest Version

```bash
cd /opt/blt
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

## Troubleshooting

If you encounter issues during setup:

1. Check the logs using `docker-compose logs`
2. Ensure your domain points to the correct IP address
3. Make sure ports 80 and 443 are open in your firewall for HTTPS
4. Check that the server has enough resources (at least 2GB RAM recommended)

For more help, visit the [OWASP Slack channel](https://owasp.org/slack/invite).