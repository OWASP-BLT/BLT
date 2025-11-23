# Trademark Search Feature

## Overview

The BLT platform now includes a powerful trademark search feature that allows users to search through millions of trademark records quickly and efficiently. This feature supports both local database searches and fallback to the USPTO API.

## Features

### 1. Fast Local Database Search
- Search through up to 3 million trademark records stored locally
- Optimized database indexes for sub-second query times
- Case-insensitive search across multiple fields
- Paginated results (50 per page)

### 2. Multiple Search Capabilities
Search by:
- **Keyword**: Trademark name or partial match
- **Serial Number**: Exact or partial serial number
- **Registration Number**: Exact or partial registration number
- **Description**: Full-text search in trademark descriptions

### 3. Rich Trademark Information
Each trademark result includes:
- Trademark keyword/name
- Registration and serial numbers
- Status (Live/Registered, Dead/Abandoned, etc.)
- Filing, registration, and expiration dates
- Owner information (name, address, legal entity type)
- Trademark description

### 4. Intelligent Fallback
- If no results found in local database, automatically falls back to USPTO API
- Seamless user experience with no manual switching required
- Clear indicators showing data source (local vs. API)

## Usage

### For End Users

#### Searching for Trademarks

1. Navigate to `/trademarks/` or click "Trademark Search" in the navigation
2. Enter your search query:
   - Trademark name (e.g., "APPLE")
   - Serial number (e.g., "87654321")
   - Registration number (e.g., "1234567")
3. Click "Search Trademarks"
4. Browse through paginated results
5. Click on any result to view full details on USPTO website

#### Understanding Results

- **Green Badge "Local Database"**: Results from local high-performance database
- **Status Colors**:
  - 🟢 Green: Live/Registered (active trademark)
  - 🟡 Yellow: Live/Pending (application in progress)
  - 🔴 Red: Dead/Abandoned (no longer active)

### For Administrators

#### Importing Trademark Data

The system includes a powerful bulk import command to populate the local database:

```bash
# Basic import from CSV
python manage.py import_trademarks_bulk /path/to/trademarks.csv

# Import with custom batch size for better performance
python manage.py import_trademarks_bulk /path/to/trademarks.csv --batch-size 5000

# Import from JSON file
python manage.py import_trademarks_bulk /path/to/trademarks.json --json

# Clear existing data and import fresh
python manage.py import_trademarks_bulk /path/to/trademarks.csv --clear
```

See [TRADEMARK_IMPORT_GUIDE.md](../TRADEMARK_IMPORT_GUIDE.md) for detailed import instructions.

#### Data Sources

You can obtain trademark data from:

1. **USPTO Bulk Data Products**
   - URL: https://www.uspto.gov/learning-and-resources/bulk-data-products
   - Official source for complete trademark database

2. **USPTO TESS (Trademark Electronic Search System)**
   - URL: https://tess2.uspto.gov/
   - Online search and export capabilities

3. **RapidAPI USPTO Trademark API**
   - For real-time updates and specific queries
   - Already integrated for fallback searches

## Architecture

### Database Schema

```
Trademark
├── keyword (indexed)
├── registration_number (indexed)
├── serial_number (indexed)
├── status_label
├── status_code
├── status_date
├── filing_date
├── registration_date
├── abandonment_date
├── expiration_date
├── description
└── owners (ManyToMany -> TrademarkOwner)

TrademarkOwner
├── name
├── address1, address2
├── city, state, country, postcode
├── owner_type
├── owner_label
├── legal_entity_type
└── legal_entity_type_label
```

### Performance Optimizations

1. **Database Indexes**
   - Single-field indexes on `keyword`, `registration_number`, `serial_number`
   - Composite index on `(keyword, status_label)`
   - Enables fast lookups even with millions of records

2. **Query Optimization**
   - Uses `select_related()` and `prefetch_related()` to minimize queries
   - Pagination to limit result set size
   - Efficient Q object queries for multi-field search

3. **Batch Processing**
   - Bulk insert operations during import
   - Configurable batch sizes for memory management
   - Owner deduplication with in-memory caching

## API Integration

### USPTO API Fallback

When local database has no results, the system automatically queries:
- **Availability Check**: `USPTO-trademark.p.rapidapi.com/v1/trademarkAvailable/{query}`
- **Search**: `USPTO-trademark.p.rapidapi.com/v1/trademarkSearch/{query}/active`

Configuration required:
```python
# settings.py or environment variables
USPTO_API = "your-rapidapi-key-here"
```

## Testing

Run the trademark tests:
```bash
python manage.py test website.tests.test_trademark
```

Tests cover:
- Model creation and relationships
- Search functionality (keyword, serial, registration number)
- Case-insensitive searches
- Pagination
- Database indexes
- View responses

## Maintenance

### Regular Updates

Keep the trademark database current:

```bash
# Weekly or monthly updates (recommended)
python manage.py import_trademarks_bulk /path/to/weekly_updates.csv

# Full refresh (quarterly recommended)
python manage.py import_trademarks_bulk /path/to/complete_database.csv --clear
```

### Database Maintenance

For optimal performance:
```sql
-- Analyze tables for query optimization
ANALYZE website_trademark;
ANALYZE website_trademarkowner;

-- Check table sizes
SELECT 
    pg_size_pretty(pg_total_relation_size('website_trademark')) as trademark_size,
    pg_size_pretty(pg_total_relation_size('website_trademarkowner')) as owner_size;

-- Vacuum to reclaim space
VACUUM ANALYZE website_trademark;
```

### Monitoring

Key metrics to monitor:
- **Database size**: Should stabilize around 5-10 GB for 3M records
- **Query response time**: Should be < 200ms for typical searches
- **Index usage**: Monitor with `pg_stat_user_indexes`

## Troubleshooting

### Common Issues

1. **Slow Search Performance**
   - Verify indexes exist: Check migration 0253_add_trademark_indexes
   - Run ANALYZE on tables
   - Check PostgreSQL configuration (shared_buffers, work_mem)

2. **Import Fails with Memory Error**
   - Reduce batch size: `--batch-size 500`
   - Check available RAM
   - Import in chunks if dataset is very large

3. **API Rate Limit Exceeded**
   - This only affects fallback searches when local DB has no results
   - Solution: Import more complete trademark data locally
   - Consider upgrading RapidAPI plan if needed

4. **No Results Found**
   - Check if local database is populated: `Trademark.objects.count()`
   - Verify USPTO_API key is configured
   - Check search query format

## Future Enhancements

Potential improvements for future versions:
- Full-text search using PostgreSQL's tsvector
- Advanced filtering (by date range, status, owner type)
- Export search results to CSV/PDF
- Trademark monitoring and alerts
- Image trademark support
- International trademark database integration
- Search suggestions and autocomplete
- Trademark similarity matching

## Security Considerations

- Import commands should only be accessible to administrators
- Validate CSV/JSON files before import
- Rate limit search queries to prevent abuse
- Regular backups of trademark database
- Monitor disk space usage

## Support

For questions or issues:
1. Check [TRADEMARK_IMPORT_GUIDE.md](../TRADEMARK_IMPORT_GUIDE.md) for detailed import instructions
2. Review test cases in `website/tests/test_trademark.py`
3. Check Django logs for detailed error messages
4. Open an issue on GitHub with details

## Credits

- USPTO for trademark data
- RapidAPI for USPTO API access
- OWASP BLT development team
