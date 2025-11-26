# Trademark Export Guide

This guide explains how to use the `export_all_trademarks` management command to gather all ~3 million trademarks from the USPTO API into a single CSV file.

## Overview

The `export_all_trademarks` command fetches all trademarks from the USPTO API via RapidAPI and exports them to a CSV file. It includes:

- **Rate Limiting**: Configurable delays between API requests to respect rate limits
- **Pagination**: Handles large datasets using the API's scroll mechanism
- **Resume Support**: Can resume from where it left off if interrupted
- **Progress Tracking**: Saves progress and provides ETA estimates
- **Error Handling**: Retries with exponential backoff on failures
- **CSV Format**: Compatible with the `import_trademarks_bulk` command

## Prerequisites

1. **USPTO API Key**: You need a RapidAPI key for the USPTO Trademark API
   - Sign up at https://rapidapi.com/
   - Subscribe to the USPTO Trademark API
   - Set the `USPTO_API` environment variable or add it to your `.env` file

2. **Disk Space**: Ensure you have sufficient disk space
   - 3M records ≈ 2-5 GB CSV file (depending on data completeness)

3. **Time**: The export will take several hours
   - With 1 second delay: ~833 hours (based on API rate limits)
   - With proper API plan and optimized settings: 6-24 hours

## Basic Usage

### Simple Export

```bash
python manage.py export_all_trademarks trademarks_all.csv
```

This uses default settings:
- 1 second delay between requests
- 100 records per batch

### Custom Rate Limiting

To respect API rate limits, adjust the delay:

```bash
# Slower, safer (2 second delay)
python manage.py export_all_trademarks trademarks_all.csv --delay 2

# Faster (0.5 second delay) - only if your API plan allows
python manage.py export_all_trademarks trademarks_all.csv --delay 0.5
```

### Custom Batch Size

Adjust how many records are fetched per API call:

```bash
python manage.py export_all_trademarks trademarks_all.csv --batch-size 200
```

### Resume Interrupted Export

If the export is interrupted, you can resume:

```bash
python manage.py export_all_trademarks trademarks_all.csv --resume
```

The command automatically saves progress to `trademarks_all.csv.progress`.

### Test with Limited Records

For testing, limit the number of records:

```bash
# Export only 1000 records for testing
python manage.py export_all_trademarks test_trademarks.csv --max-records 1000 --delay 0.5
```

## Understanding Rate Limits

### RapidAPI Rate Limits

The USPTO Trademark API on RapidAPI typically has these limits:

- **Free Tier**: 100 requests/month (not suitable for 3M records)
- **Basic Tier**: 10,000 requests/month
- **Pro Tier**: 100,000 requests/month
- **Ultra/Mega Tier**: Higher limits

### Calculating Export Time

With 100 records per batch and 3M total records:
- Total API calls needed: 30,000 calls
- With 1 second delay: ~8.3 hours
- With 2 second delay: ~16.7 hours

**Recommendation**: Use a delay of 1-2 seconds to be safe with rate limits.

## Output Format

The CSV file has the following columns:

```
keyword,registration_number,serial_number,status_label,status_code,status_date,
status_definition,filing_date,registration_date,abandonment_date,expiration_date,
description,owner_name,owner_address1,owner_address2,owner_city,owner_state,
owner_country,owner_postcode,owner_type,owner_label,legal_entity_type,
legal_entity_type_label
```

**Note**: If a trademark has multiple owners, it will have multiple rows (one per owner).

## Progress Tracking

The command creates a progress file named `{output_file}.progress` that tracks:

- Current start index
- Total records fetched
- Last scroll ID (for API pagination)
- Last updated timestamp

Example progress file:
```json
{
  "start_index": 50000,
  "total_fetched": 49823,
  "last_scroll_id": "abc123...",
  "last_updated": "2024-01-15T10:30:45.123456"
}
```

## Monitoring Progress

The command outputs progress information:

```
Fetching batch starting at index 10000...
Fetched 100 records. Total: 10100/3000000 (15.2 records/sec, ETA: 54.3h)
```

This shows:
- Records in current batch
- Total records fetched
- Total records available
- Fetch rate (records/second)
- Estimated time to completion

## Error Handling

The command handles various error scenarios:

### API Rate Limit Exceeded

If you hit rate limits, you'll see:
```
API request failed: 429 Client Error: Too Many Requests
```

**Solution**: Increase the delay or wait for rate limit reset, then resume:
```bash
python manage.py export_all_trademarks trademarks_all.csv --resume --delay 3
```

### Network Errors

Temporary network issues are retried automatically with exponential backoff.

### Interrupted Export

If interrupted (Ctrl+C), progress is saved:
```
Export interrupted by user. Progress saved to trademarks_all.csv.progress
```

Resume with:
```bash
python manage.py export_all_trademarks trademarks_all.csv --resume
```

## After Export: Importing the Data

Once the export is complete, import the CSV into your local database:

```bash
python manage.py import_trademarks_bulk trademarks_all.csv --batch-size 2000
```

This will populate your local trademark database for fast searches.

## Best Practices

1. **Start with a Test Run**: Export 1000-10000 records first to verify everything works

```bash
python manage.py export_all_trademarks test.csv --max-records 10000 --delay 1
```

2. **Monitor the First Hour**: Watch the first hour of export to ensure:
   - No rate limit errors
   - Reasonable progress rate
   - No repeated errors

3. **Run in Background**: Use `nohup` or `screen` for long exports:

```bash
# Using nohup
nohup python manage.py export_all_trademarks trademarks_all.csv --delay 1 > export.log 2>&1 &

# Using screen
screen -S trademark_export
python manage.py export_all_trademarks trademarks_all.csv --delay 1
# Press Ctrl+A, then D to detach
```

4. **Check Available Disk Space**:

```bash
df -h
```

5. **Verify API Key**: Test your API key first:

```bash
python manage.py fetch_trademarks
```

## Troubleshooting

### Issue: "USPTO_API key is not configured"

**Solution**: Set the environment variable:
```bash
export USPTO_API="your-rapidapi-key"
# Or add to .env file
echo "USPTO_API=your-rapidapi-key" >> .env
```

### Issue: Progress file corrupted

**Solution**: Delete progress file and start fresh:
```bash
rm trademarks_all.csv.progress
python manage.py export_all_trademarks trademarks_all.csv
```

### Issue: CSV file is too large

**Solution**: The command writes incrementally, so large files are handled properly. If needed, split the import:

```bash
# Split CSV into chunks
split -l 500000 trademarks_all.csv trademark_chunk_

# Import each chunk
for file in trademark_chunk_*; do
    python manage.py import_trademarks_bulk "$file"
done
```

### Issue: Slow export rate

**Solution**: 
1. Check your API plan limits
2. Reduce delay if your plan allows: `--delay 0.5`
3. Verify network connection
4. Check if API is experiencing issues

## Alternative: Official USPTO Data

For the most complete dataset, you can also download directly from USPTO:

1. **USPTO Bulk Data**: https://www.uspto.gov/learning-and-resources/bulk-data-products
   - Download the complete trademark database
   - May require format conversion

2. **TSDR (Trademark Status & Document Retrieval)**: https://tsdr.uspto.gov/
   - Export search results in bulk

## Support

For issues:
1. Check the export log file
2. Verify your API key is valid
3. Check RapidAPI dashboard for rate limit status
4. Review the progress file for the last successful position

## Advanced Configuration

### Customize CSV Format

Edit `export_all_trademarks.py` to modify the CSV columns in the `write_csv_header()` and `write_trademark_to_csv()` methods.

### Adjust Error Retry Logic

The command retries up to 5 times with exponential backoff. Modify `max_consecutive_errors` in the script if needed.

### Change API Endpoint

If USPTO API changes, update the `url` in the `fetch_trademark_batch()` method.

## Summary of Commands

```bash
# Basic export
python manage.py export_all_trademarks trademarks_all.csv

# With custom settings
python manage.py export_all_trademarks trademarks_all.csv --delay 1.5 --batch-size 100

# Resume interrupted export
python manage.py export_all_trademarks trademarks_all.csv --resume

# Test with limited records
python manage.py export_all_trademarks test.csv --max-records 5000

# Import the exported data
python manage.py import_trademarks_bulk trademarks_all.csv --batch-size 2000
```

## Estimated Timeline

For a complete 3M record export:

| Delay Setting | API Calls | Estimated Time |
|---------------|-----------|----------------|
| 0.5 seconds   | 30,000    | ~4 hours       |
| 1.0 seconds   | 30,000    | ~8 hours       |
| 2.0 seconds   | 30,000    | ~16 hours      |

**Note**: Actual time may vary based on:
- Network speed
- API response time
- Rate limit resets
- Error retries

Start with 1.0 second delay and adjust based on rate limit errors.
