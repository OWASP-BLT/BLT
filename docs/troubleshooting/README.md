# Troubleshooting Documentation

This section contains guides for troubleshooting common issues and errors in OWASP BLT.

## Known Issues

- [Staking Pool ValueError](ValueError_staking_pool.md) - Error when initializing staking pools

## Getting Help

If you encounter an issue not covered in this documentation:

1. Check the [GitHub Issues](https://github.com/OWASP-BLT/BLT/issues) for similar problems
2. Review the [Setup Guide](../setup/Setup.md) to ensure proper configuration
3. Join the [OWASP Slack](https://owasp.org/slack/invite) for community support
4. Report security issues through [GitHub Security Advisories](https://github.com/OWASP-BLT/BLT/security/advisories)

## Common Issues

### Docker Issues
- Ensure Docker and Docker Compose are installed and running
- Check that ports 8000 (Django) and 5432 (PostgreSQL) are not in use
- Run `docker-compose logs` to view error messages

### Database Issues
- Ensure PostgreSQL is running
- Run migrations: `python manage.py migrate`
- Check database credentials in `.env` file

### Static Files
- Run `python manage.py collectstatic --noinput` after changes
- Ensure Tailwind CSS is properly compiled

### Pre-commit Failures
- Run `pre-commit run --all-files` twice (first run may auto-fix issues)
- Ensure Poetry dependencies are installed: `poetry install`

[← Back to Documentation Index](../index.md)
