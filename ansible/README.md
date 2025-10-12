# Ansible Deployment

Minimal Ansible playbook to deploy the BLT Django project.

## Files
- `inventory.yml` - Define your server host/IP and variables.
- `playbook.yml` - Executes deployment steps (clone repo, install deps, migrate, collectstatic, configure systemd + nginx).

## Usage
1. Edit `inventory.yml` and set:
   - `ansible_host`
   - `ansible_user`
   - `domain` (optional)
2. Run:
```bash
ansible-playbook -i ansible/inventory.yml ansible/playbook.yml
```

## Notes
- Installs dependencies using Poetry export to a requirements.txt installed into a virtualenv.
- Creates a systemd service `gunicorn-blt`.
- Nginx reverse proxies to Gunicorn on port 8000.
- Opens ports 22, 80, 443 with UFW.
- For HTTPS, you can manually install Certbot or extend the playbook.

## Quick Certbot (optional)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain --email you@example.com --agree-tos --redirect
```
