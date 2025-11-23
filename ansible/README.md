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
   - `postgres_host` / `postgres_port` - Override if using external PostgreSQL server
   - `enable_remote_postgres` - Set to `true` only if you need remote PostgreSQL access
     - **WARNING**: This exposes PostgreSQL to the internet. See Security Considerations below.
2. Run:
```bash
ansible-playbook -i ansible/inventory.yml ansible/playbook.yml
```

## Notes
- Installs Poetry using the official installer for the app user.
- Installs dependencies using Poetry export to a requirements.txt, which is then installed into a virtualenv.
- Creates a systemd service `blt-uvicorn`.
- Nginx reverse proxies to uvicorn (ASGI) server on port 8000.
- Opens ports 22, 80, 443 with UFW (port 5432 only if remote PostgreSQL is enabled).
- For HTTPS, you can manually install Certbot or extend the playbook.

## Security Considerations
- **SECRET_KEY**: A secure random SECRET_KEY is generated once and persisted in `{{ app_dir }}/shared/secret_key`. Django now reads this from the environment variable.
- **Remote PostgreSQL Access**: If `enable_remote_postgres` is enabled, PostgreSQL will accept connections from any IP (0.0.0.0/0) using `scram-sha-256` authentication. This is a security risk. For production:
  - Keep `enable_remote_postgres: false` unless absolutely necessary
  - If remote access is needed, modify the `pg_hba.conf` rule in `playbook.yml` to restrict access to specific IP addresses/ranges instead of 0.0.0.0/0
  - Consider using SSH tunneling or VPN for database access instead

## Quick Certbot (optional)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain --email you@example.com --agree-tos --redirect
```
