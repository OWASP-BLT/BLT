# Trademark Database Import Guide

This guide explains how to import and manage the trademark database for fast, local searches.

## Overview

The BLT trademark search feature now supports a local database of trademarks, enabling fast searches without relying on external API calls. The system can handle millions of trademark records efficiently.

## Features

- **Fast Local Search**: Query trademark data from a local PostgreSQL database with optimized indexes
- **Bulk Import**: Import millions of trademark records from CSV or JSON files
- **Efficient Pagination**: Browse through search results with paginated views (50 results per page)
- **Fallback to API**: Automatically falls back to USPTO API if local database has no results
- **Database Indexes**: Optimized indexes on keyword, serial_number, and registration_number fields

## Data Format

### CSV Format

The import command expects a CSV file with the following columns:

```csv
keyword,registration_number,serial_number,status_label,status_code,status_date,status_definition,filing_date,registration_date,abandonment_date,expiration_date,description,owner_name,owner_address1,owner_address2,owner_city,owner_state,owner_country,owner_postcode,owner_type,owner_label,legal_entity_type,legal_entity_type_label
```

**Example CSV row:**
```csv
APPLE,1234567,87654321,Live/Registered,6,2023-01-15,Registered,2020-05-10,2021-08-20,,,Computer hardware and software,Apple Inc.,One Apple Park Way,,Cupertino,CA,US,95014,03,Owner,03,Corporation
```

### JSON Format

Alternatively, you can use JSON format:

```json
[
  {
    "keyword": "APPLE",
    "registration_number": "1234567",
    "serial_number": "87654321",
    "status_label": "Live/Registered",
    "status_code": "6",
    "status_date": "2023-01-15",
    "status_definition": "Registered",
    "filing_date": "2020-05-10",
    "registration_date": "2021-08-20",
    "abandonment_date": "",
    "expiration_date": "",
    "description": "Computer hardware and software",
    "owner": {
      "name": "Apple Inc.",
      "address1": "One Apple Park Way",
      "address2": "",
      "city": "Cupertino",
      "state": "CA",
      "country": "US",
      "postcode": "95014",
      "owner_type": "03",
      "owner_label": "Owner",
      "legal_entity_type": "03",
      "legal_entity_type_label": "Corporation"
    }
  }
]
```

## Date Formats Supported

The import command supports multiple date formats:
- `YYYY-MM-DD` (ISO format, recommended)
- `MM/DD/YYYY` (US format)
- `YYYY/MM/DD`
- `DD-MM-YYYY`

## Import Commands

### Basic CSV Import

```bash
python manage.py import_trademarks_bulk /path/to/trademarks.csv
```

### JSON Import

```bash
python manage.py import_trademarks_bulk /path/to/trademarks.json --json
```

### Custom Batch Size

For optimal performance with large files, you can adjust the batch size (default is 1000):

```bash
python manage.py import_trademarks_bulk /path/to/trademarks.csv --batch-size 5000
```

### Clear Existing Data Before Import

To replace all existing trademark data:

```bash
python manage.py import_trademarks_bulk /path/to/trademarks.csv --clear
```

## Performance Considerations

### For 3 Million Records

When importing 3 million trademark records:

1. **Batch Size**: Use a batch size of 1000-5000 for optimal memory usage
2. **Time Estimate**: Expect 30-60 minutes for full import depending on hardware
3. **Database Resources**: Ensure PostgreSQL has adequate memory and disk space
4. **Progress Monitoring**: The command outputs progress every batch

Example for large import:
```bash
python manage.py import_trademarks_bulk /path/to/uspto_trademarks_3m.csv --batch-size 2000
```

### Database Indexes

The following indexes are automatically created to optimize search performance:
- `keyword` field index
- `registration_number` field index
- `serial_number` field index
- Composite index on `(keyword, status_label)`

These indexes ensure fast queries even with millions of records.

## Obtaining USPTO Trademark Data

### Official USPTO Sources

1. **USPTO Trademark Status & Document Retrieval (TSDR)**
   - URL: https://tsdr.uspto.gov/
   - Provides access to trademark records

2. **USPTO Bulk Data Products**
   - URL: https://www.uspto.gov/learning-and-resources/bulk-data-products
   - Download complete trademark database dumps

3. **USPTO Trademark Electronic Search System (TESS)**
   - URL: https://tess2.uspto.gov/
   - Online trademark search system

### Third-Party Data Sources

- **RapidAPI USPTO Trademark API**
  - The existing fetch_trademarks command uses this API
  - Good for incremental updates

## Search Functionality

### How Search Works

1. **Local Database First**: Searches the local trademark database using efficient SQL queries
2. **Multiple Field Search**: Searches across keyword, serial_number, registration_number, and description
3. **Case-Insensitive**: All searches are case-insensitive
4. **Pagination**: Results are paginated (50 per page)
5. **API Fallback**: If no local results found, falls back to USPTO API (if configured)

### Search Query Examples

- Search by keyword: `APPLE`
- Search by serial number: `87654321`
- Search by registration number: `1234567`
- Search by partial keyword: `APP` (finds APPLE, APPLICATION, etc.)

## Maintenance

### Updating Trademark Data

To keep the database current:

1. **Regular Updates**: Schedule periodic imports of updated trademark data
2. **Incremental Updates**: Use the existing `fetch_trademarks` command for specific organizations
3. **Full Refresh**: Periodically do a full import with `--clear` flag to ensure data accuracy

### Monitoring Database Size

Check trademark table size:
```sql
SELECT 
    COUNT(*) as trademark_count,
    pg_size_pretty(pg_total_relation_size('website_trademark')) as table_size
FROM website_trademark;
```

### Database Maintenance

For optimal performance:
```sql
-- Analyze tables for better query planning
ANALYZE website_trademark;
ANALYZE website_trademarkowner;

-- Vacuum to reclaim space
VACUUM ANALYZE website_trademark;
```

## Troubleshooting

### Common Issues

1. **Memory Errors During Import**
   - Solution: Reduce batch size with `--batch-size 500`

2. **Slow Import Speed**
   - Solution: Temporarily disable indexes, import, then recreate indexes
   - Or increase batch size to 5000+

3. **Duplicate Key Errors**
   - Solution: The command uses `ignore_conflicts=True` to skip duplicate records during import
   - Duplicate records are automatically skipped without failing the entire batch

4. **Date Parsing Errors**
   - Solution: Ensure dates are in supported formats
   - Empty date fields are allowed

### Getting Help

If you encounter issues:
1. Check the Django logs for detailed error messages
2. Verify your CSV/JSON format matches the expected structure
3. Test with the sample data file first (`trademarks_sample.csv`)

## API Configuration

The USPTO API is used as a fallback when local database has no results. To configure:

1. Set `USPTO_API` in your Django settings or environment variables
2. Get an API key from RapidAPI: https://rapidapi.com/

Without the API key, the system will only use local database results.

## Example Workflow

Here's a complete workflow for setting up a 3M trademark database:

```bash
# 1. Apply database migrations
python manage.py migrate

# 2. Download USPTO data (example)
# Download from USPTO or obtain from your data source

# 3. Import the data
python manage.py import_trademarks_bulk uspto_trademarks_3m.csv --batch-size 2000

# 4. Verify import
python manage.py shell
>>> from website.models import Trademark
>>> print(f"Total trademarks: {Trademark.objects.count()}")

# 5. Test search functionality
# Visit: http://localhost:8000/trademarks/
# Search for any trademark
```

## Performance Benchmarks

Expected performance with 3 million records:

- **Single keyword search**: < 100ms
- **Serial number lookup**: < 50ms (indexed)
- **Registration number lookup**: < 50ms (indexed)
- **Partial keyword match**: 100-500ms depending on result count
- **Paginated results**: 50-100ms per page

## Security Considerations

- Only administrators should have access to import commands
- Validate CSV/JSON files before import to prevent malicious data
- Monitor disk space usage as trademark database grows
- Regular backups of trademark data recommended

## Future Enhancements

Potential improvements:
- Full-text search using PostgreSQL's tsvector
- Advanced filtering by status, date ranges, owner
- Export functionality for filtered results
- Automated periodic updates from USPTO
- Search suggestion/autocomplete
