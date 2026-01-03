# Duplicate Email Migration Guide

## Overview

This guide covers the safe migration process for making email addresses unique in the Django User model. The migration includes enhanced safety checks to prevent accidental deletion of high-activity users.

## ⚠️ CRITICAL: Backup Your Database First!

**BEFORE running any migration, create a complete database backup:**

```bash
# PostgreSQL
pg_dump your_database_name > backup_$(date +%Y%m%d_%H%M%S).sql

# MySQL
mysqldump -u username -p database_name > backup_$(date +%Y%m%d_%H%M%S).sql

# SQLite
cp your_database.db backup_$(date +%Y%m%d_%H%M%S).db
```

## Safety Features

### 1. High-Activity User Protection

The migration will **automatically halt** if it detects users with high activity that would be deleted:

- **Issues reported**: 5 or more
- **Points earned**: 100 or more  
- **Recent login**: Within last 30 days

### 2. Preserves Most Recent Account

Unlike the original migration that kept the oldest account, this version keeps the **newest account** (highest ID), which is more likely to be the active one.

### 3. Comprehensive Analysis Tools

Use the enhanced analysis command to understand what will happen:

```bash
# Basic analysis
python manage.py analyze_duplicate_emails

# Detailed analysis with activity metrics
python manage.py analyze_duplicate_emails --detailed --show-activity

# Export analysis to CSV for review
python manage.py analyze_duplicate_emails --export-csv duplicate_analysis.csv

# Show only high-activity users that would be flagged
python manage.py analyze_duplicate_emails --high-activity-only
```

## Pre-Migration Process

### Step 1: Analyze Current State

```bash
python manage.py analyze_duplicate_emails --show-activity
```

This will show:
- All duplicate email situations
- Activity levels for each user
- Which users would be kept vs deleted
- Any high-activity users that would block the migration

### Step 2: Resolve High-Activity Conflicts

If high-activity users are detected, use the resolution tool:

```bash
# List all duplicate situations with details
python manage.py resolve_duplicate_emails --list

# Contact users asking them to update their emails
python manage.py resolve_duplicate_emails --contact-users

# Update a specific user's email
python manage.py resolve_duplicate_emails --update-email 123 new_email@example.com

# Merge one user's data into another (use carefully!)
python manage.py resolve_duplicate_emails --merge-users 123 456
```

### Step 3: Manual Review Options

For each duplicate email situation, you have several options:

1. **Contact Users**: Ask them to update their email addresses
2. **Update Email**: Manually change one user's email
3. **Merge Accounts**: Combine data from multiple accounts (advanced)
4. **Manual Decision**: Decide which account should be kept based on activity

## Running the Migration

### Option 1: Safe Migration (Recommended)

```bash
# Run the enhanced safe migration
python manage.py migrate website 0264
```

This migration will:
- Check for high-activity users
- Halt if any are found
- Provide detailed logging
- Only proceed if safe

### Option 2: Original Migration (Not Recommended)

```bash
# Run the original migration (less safe)
python manage.py migrate website 0260
```

## What the Migration Does

### User Deletion Logic

For each duplicate email:
1. **Keeps**: The user with the **highest ID** (newest account)
2. **Deletes**: All other users with that email
3. **Deletes**: All related data via Django's CASCADE behavior

### Data That Gets Deleted

When a user is deleted, the following related data is also removed:
- Issues reported by the user
- Points earned by the user
- Comments made by the user
- User profile information
- Forum posts and votes
- All other related records (via CASCADE)

### Database Changes

1. **Removes duplicate users** (except newest for each email)
2. **Creates unique index** on email field:
   - PostgreSQL/SQLite: Partial index excluding empty/NULL emails
   - MySQL: Converts empty strings to NULL, then creates unique index

## Post-Migration Verification

After successful migration:

```bash
# Verify no duplicates remain
python manage.py analyze_duplicate_emails

# Check database constraints
python manage.py dbshell
# Then run: \d auth_user (PostgreSQL) or DESCRIBE auth_user; (MySQL)
```

## Rollback Considerations

### ⚠️ Important Limitations

- **Deleted users cannot be restored** from the migration
- **MySQL rollback is not supported** (empty strings converted to NULL)
- **Always restore from backup** if you need to rollback

### Rollback Process

```bash
# Rollback migration (removes unique constraint only)
python manage.py migrate website 0263

# Restore from backup if you need deleted users back
# PostgreSQL
psql your_database_name < backup_file.sql

# MySQL  
mysql -u username -p database_name < backup_file.sql
```

## Troubleshooting

### Migration Blocked by High-Activity Users

```
Migration halted: X high-activity users detected. Manual review required.
```

**Solution**: Use the resolution tools to handle these users manually before re-running the migration.

### Email Already Exists Error

After migration, if you get "email already exists" errors:

1. Check for remaining duplicates: `python manage.py analyze_duplicate_emails`
2. Verify unique constraint was created properly
3. Check application code for email validation logic

### Performance Issues

For large databases:
- Run during low-traffic periods
- Consider using `--fake` flag for testing
- Monitor database locks and performance

## Best Practices

1. **Always backup first** - Cannot be emphasized enough
2. **Test on staging** - Run the full process on a copy of production data
3. **Communicate with users** - Let them know about the cleanup process
4. **Monitor after migration** - Watch for any issues with user authentication
5. **Document decisions** - Keep records of manual interventions made

## Support

If you encounter issues:

1. Check the migration logs for detailed error messages
2. Verify your database backup is complete and restorable
3. Use the analysis tools to understand the current state
4. Consider manual resolution for complex cases

## Migration Files

- `0264_make_email_unique_safe.py` - Enhanced safe migration
- `0260_make_email_unique.py` - Original migration (deprecated)
- `analyze_duplicate_emails.py` - Analysis management command
- `resolve_duplicate_emails.py` - Resolution management command