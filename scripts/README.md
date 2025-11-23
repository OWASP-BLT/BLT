# BLT Scripts

This directory contains utility scripts for the OWASP BLT project.

## Bounty Payout PR Validation

Scripts to help find and validate PRs that implement automatic bounty payout functionality.

### Files

1. **`find_bounty_payout_pr.py`** - Automatically searches for bounty payout PRs
2. **`validate_bounty_pr.py`** - Provides validation checklist for PR #4633

### Usage

#### Validate Bounty Payout PR

Run the validation checklist to review PR #4633's implementation:

```bash
python scripts/validate_bounty_pr.py
```

This will display:
- Critical requirements checklist
- Important features to verify
- Recommended enhancements
- Key risks and mitigation strategies
- Next steps for merging the PR

#### Find Bounty Payout PRs

Search for PRs implementing bounty payout functionality:

```bash
python scripts/find_bounty_payout_pr.py
```

**Note:** Requires `gh` CLI to be installed and authenticated.

### About PR #4633

PR #4633 implements automatic bounty payouts using a GitHub Sponsors create-then-cancel approach:

- **Problem:** GitHub's one-time payment API is broken
- **Solution:** Create a subscription, then immediately cancel it
- **Result:** One-time payment without recurring charges

Key components:
- GitHub Actions workflow to detect merged PRs
- API endpoint for processing payments
- Database migrations for tracking cancellation attempts
- Repository allowlist for security
- Retry logic for failed cancellations

### Documentation

For detailed information about bounty payout implementation and validation:

- [Bounty Payout PR Validation Guide](../docs/BOUNTY_PAYOUT_PR_VALIDATION.md)
- [PR #4633 on GitHub](https://github.com/OWASP-BLT/BLT/pull/4633)

### Requirements

- Python 3.8+
- GitHub CLI (`gh`) for `find_bounty_payout_pr.py`
- Access to OWASP-BLT/BLT repository

### Contributing

If you improve these scripts or add new validation checks:

1. Test your changes thoroughly
2. Update this README
3. Submit a PR with clear description
4. Tag with `scripts` and `documentation` labels

### Support

Questions or issues with these scripts?

- Open an issue on GitHub
- Ask in the OWASP BLT Discord
- Contact the maintainers

---

**Last Updated:** 2025-11-23  
**Maintained by:** OWASP BLT Team
