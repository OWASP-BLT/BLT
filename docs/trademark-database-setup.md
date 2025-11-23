# Trademark Database Setup

This document describes how to set up and populate the local trademark database for fast searching.

## Overview

The trademark database allows searching through millions of trademarks stored locally for faster lookups compared to using the USPTO API. The database includes indexes for efficient searching by keyword, registration number, serial number, and filing date.

## Features

- **Fast Local Searching**: Search through millions of trademarks without API rate limits
- **Indexed Database**: Optimized indexes for quick searches by keyword, registration/serial numbers
- **Pagination**: Results are paginated (50 per page) for better performance
- **Multiple Search Fields**: Search by keyword, registration number, serial number, or description

## Database Model

The `Trademark` model includes the following fields:
- `keyword` (indexed) - The trademark name/keyword
- `registration_number` (indexed) - USPTO registration number
- `serial_number` (indexed) - USPTO serial number
- `status_label` - Current status (e.g., "Live/Registered", "Dead/Abandoned")
- `status_code` - Status code
- `filing_date` (indexed) - Date the trademark was filed
- `registration_date` - Date the trademark was registered
- `expiration_date` - Date the trademark expires
- `description` - Description of the trademark goods/services

## Importing Trademark Data

### Step 1: Obtain Trademark Data

You can obtain trademark data from the USPTO in CSV format. The USPTO provides bulk data downloads at:
- [USPTO Trademark Bulk Data Products](https://www.uspto.gov/learning-and-resources/bulk-data-products)

### Step 2: Prepare CSV File

Ensure your CSV file has the following columns (header row is required):
```
keyword,registration_number,serial_number,status_label,status_code,status_date,status_definition,filing_date,registration_date,abandonment_date,expiration_date,description
```

Date formats supported:
- `YYYY-MM-DD` (recommended)
- `MM/DD/YYYY`
- `YYYY/MM/DD`
- `DD-MM-YYYY`

### Step 3: Run the Import Command

Use the `bulk_import_trademarks` management command to import the data:

```bash
# Basic import
poetry run python manage.py bulk_import_trademarks /path/to/trademarks.csv

# Import with custom batch size (default is 10000)
poetry run python manage.py bulk_import_trademarks /path/to/trademarks.csv --batch-size 5000

# Skip the header row if needed (use if your CSV doesn't have proper headers)
poetry run python manage.py bulk_import_trademarks /path/to/trademarks.csv --skip-header
```

The import process:
- Processes records in batches for better memory management
- Uses `bulk_create` for fast insertion
- Ignores conflicts (duplicate records won't cause errors)
- Logs progress every batch
- Reports total imported and skipped records

### Example Output

```
Starting bulk import from /path/to/trademarks.csv
Imported 10000 trademarks so far...
Imported 20000 trademarks so far...
...
Bulk import completed. Imported: 3000000, Skipped: 50
```

## Using the Search Interface

### Web Interface

1. Navigate to `/trademarks/search/` in your browser
2. Enter a search term (keyword, registration number, serial number, or description content)
3. Results are displayed in a paginated table
4. Click on any trademark row to view details on USPTO's official website

### API Search (Original)

The original API-based search is still available at `/trademarks/` for real-time USPTO data lookups.

## Performance Considerations

### Database Indexes

The following indexes are automatically created to optimize search performance:
- Single column indexes on: `keyword`, `registration_number`, `serial_number`, `filing_date`
- Composite indexes on: `(keyword, status_code)`, `(registration_number, serial_number)`

### Query Optimization

The search view uses:
- Case-insensitive matching with `icontains`
- `select_related()` for efficient foreign key queries
- Pagination to limit results per page
- Database-level full-text search (can be enhanced with PostgreSQL's full-text search)

### Recommended Database

For production use with millions of records:
- **PostgreSQL** is highly recommended for better full-text search capabilities
- Consider enabling PostgreSQL full-text search indexes for even faster searches
- Use connection pooling for better performance under load

## Maintenance

### Updating Trademark Data

To keep the database current:
1. Download updated trademark data from USPTO
2. Run the import command with the new data (existing records will be skipped)
3. Consider running periodic updates (e.g., monthly) via cron job

### Database Cleanup

To remove old or invalid trademarks:
```bash
poetry run python manage.py shell
>>> from website.models import Trademark
>>> # Example: Delete abandoned trademarks older than 10 years
>>> from datetime import datetime, timedelta
>>> cutoff_date = datetime.now() - timedelta(days=3650)
>>> Trademark.objects.filter(status_label__icontains='Abandoned', abandonment_date__lt=cutoff_date).delete()
```

## Troubleshooting

### Import Fails with Memory Error
- Reduce the batch size: `--batch-size 1000`
- Import data in smaller chunks

### Search is Slow
- Ensure database indexes are created (run migrations)
- For PostgreSQL, consider adding full-text search indexes
- Check database query performance with Django Debug Toolbar

### Missing Data in Search Results
- Verify the CSV import completed successfully
- Check for parsing errors in the import log
- Ensure date formats in CSV match supported formats

## Future Enhancements

Possible improvements:
- PostgreSQL full-text search integration for faster text searches
- Advanced filtering (by status, date ranges, owner information)
- Export search results to CSV
- API endpoint for programmatic access
- Autocomplete suggestions for search terms
