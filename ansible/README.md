# Ansible Deployment

Minimal Ansible playbook to deploy the BLT Django project.

## Files
- `inventory.yml` - Define your server host/IP and variables (create from `inventory-sample.yml`).
- `inventory-sample.yml` - Sample inventory file with all available configuration options.
- `playbook.yml` - Executes deployment steps (clone repo, install deps, migrate, collectstatic, configure systemd + nginx).

## Usage
1. Copy `inventory-sample.yml` to `inventory.yml` and edit:
   - `ansible_host` - Your server IP or hostname
   - `ansible_user` - SSH user (e.g., ubuntu, root)
   - `ansible_ssh_private_key_file` - Path to your SSH key
   - `domain` - Your domain name
   - `postgres_db_password` - Secure PostgreSQL password
   - `postgres_host` - PostgreSQL host (default: 127.0.0.1 for local)
   - `postgres_port` - PostgreSQL port (default: 5432)
   - `enable_remote_postgres` - Set to `true` only if you need remote PostgreSQL access (WARNING: exposes DB to internet)
2. Run:
```bash
ansible-playbook -i ansible/inventory.yml ansible/playbook.yml
```

## Notes
- Installs dependencies using Poetry export to a requirements.txt, which is then installed into a virtualenv.
- Creates a systemd service `blt-uvicorn`.
- Nginx reverse proxies to uvicorn (ASGI) server on port 8000.
- Opens ports 22, 80, 443 with UFW.
- For HTTPS, you can manually install Certbot or extend the playbook.

## Quick Certbot (optional)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain --email you@example.com --agree-tos --redirect
```
