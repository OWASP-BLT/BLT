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
   - `enable_remote_postgres` - Set to `true` only if you need remote PostgreSQL access
2. Run:

```bash
ansible-playbook -i ansible/inventory.yml ansible/playbook.yml
```

## Notes

- Dependencies are installed using **uv**.
- `uv sync --frozen` installs dependencies from `uv.lock` into `.venv`.
- No requirements.txt is used.
- Systemd runs uvicorn from the uv-managed virtualenv.
- Nginx reverse proxies to uvicorn (ASGI) server on port 8000.

## Quick Certbot (optional)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain --email you@example.com --agree-tos --redirect
```
