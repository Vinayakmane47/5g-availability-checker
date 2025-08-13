# Bulk 5G Availability Checker

This tool expands your 5G availability database by automatically checking addresses in Melbourne CBD for 5G availability using the Telstra website.

## What it does

1. **Fetches addresses** from Melbourne CBD using OpenStreetMap data
2. **Checks 5G availability** for each address using the Telstra website
3. **Saves results** to `results.csv` for use by your web application
4. **Avoids duplicates** by checking against existing results
5. **Handles errors gracefully** and continues processing
6. **Retries failed addresses** with exponential backoff
7. **Processes in batches** to avoid overwhelming the system

## Quick Start

### Option 1: Use the convenience script
```bash
# Run with default settings (300 addresses, 2 workers, 30 per batch)
./run_bulk_checker.sh

# Or do a dry run first to see what would be checked
./run_bulk_checker.sh --dry-run

# Retry addresses that failed in previous runs
./run_bulk_checker.sh --retry-failed
```

### Option 2: Use the Python script directly
```bash
# Basic usage with enhanced error handling
python bulk_checker.py

# With custom settings
python bulk_checker.py --workers 3 --limit 500 --batch-size 50

# Dry run to see what would be checked
python bulk_checker.py --dry-run --limit 100

# Only retry failed addresses
python bulk_checker.py --retry-failed
```

## Command Line Options

- `--workers N`: Number of concurrent workers (default: 3)
- `--limit N`: Maximum number of addresses to check (default: 1000)
- `--batch-size N`: Number of addresses to process in each batch (default: 50)
- `--dry-run`: Show what would be checked without actually checking
- `--retry-failed`: Only retry addresses that failed in previous runs

## Enhanced Error Handling

### Retry Mechanism
- **Automatic retries**: Each address is retried up to 3 times if it fails
- **Exponential backoff**: 2, 4, 8 second delays between retries
- **Specific error handling**: Catches `ElementNotInteractableException`, `TimeoutException`, and `WebDriverException`

### Batch Processing
- **Smaller batches**: Processes addresses in configurable batches (default: 50)
- **Batch delays**: 30-second delays between batches to avoid overwhelming servers
- **Progress tracking**: Shows batch progress and completion status

### Failed Address Tracking
- **Failed address file**: Saves failed addresses to `failed_addresses.json`
- **Retry capability**: Can retry only failed addresses in subsequent runs
- **Persistent tracking**: Failed addresses persist between runs

## How it works

1. **Address Discovery**: Uses OpenStreetMap data to find addresses in Melbourne CBD (defined by `CBD_BBOX` in `config.py`)

2. **Duplicate Prevention**: Loads existing results from `results.csv` and skips addresses that have already been checked

3. **Failed Address Loading**: Loads previously failed addresses from `failed_addresses.json` for retry

4. **Batch Processing**: Processes addresses in small batches with delays between batches

5. **Retry Logic**: Each address gets up to 3 attempts with exponential backoff

6. **Concurrent Processing**: Uses multiple threads within each batch for faster processing

7. **Error Recovery**: Continues processing even if individual addresses fail to check

8. **Immediate Saving**: Saves each result immediately to avoid data loss

## Output

- **results.csv**: Updated with new 5G availability data
- **bulk_checker.log**: Detailed logs of the checking process
- **failed_addresses.json**: List of addresses that failed and need retry
- **Console output**: Real-time progress and summary

## Example Output

```
2025-08-13 15:32:57,771 - INFO - Found 50 addresses in Melbourne CBD
2025-08-13 15:32:57,771 - INFO - Loaded 5 failed addresses for retry
2025-08-13 15:32:57,771 - INFO - Checking 55 addresses (including 5 retries)
2025-08-13 15:32:57,771 - INFO - Processing batch 1/2 (30 addresses)
2025-08-13 15:33:37,002 - INFO - + 2 Lygon Street VIC 3053: Not available (39.229s)
2025-08-13 15:33:49,452 - INFO - + 8 Whiteman Street Southbank VIC 3006: Available (12.448s)
2025-08-13 15:33:50,123 - WARNING - Loading error on attempt 1/3 for 123 Main St: ElementNotInteractableException
2025-08-13 15:33:52,234 - INFO - Retry 2/3 for 123 Main St after 2s delay
...
2025-08-13 15:40:13,796 - INFO - Batch 1 completed: 28 successful, 2 failed
2025-08-13 15:40:13,796 - INFO - Waiting 30 seconds before next batch...
2025-08-13 15:40:43,796 - INFO - Processing batch 2/2 (25 addresses)
...
2025-08-13 15:45:13,796 - INFO - Bulk check completed: 50 successful, 5 failed
2025-08-13 15:45:13,796 - INFO - Saved 5 failed addresses to failed_addresses.json for retry
```

## Performance Tips

- **Workers**: 2-3 workers is optimal for error handling. More workers = faster but may cause more loading errors
- **Batch size**: 30-50 addresses per batch is recommended to avoid overwhelming Telstra's servers
- **Limit**: Start with 200-500 addresses per run to test
- **Timing**: Each address takes 10-40 seconds to check, depending on availability and retries

## Integration with Web App

After running the bulk checker:

1. Your `results.csv` will be updated with new addresses
2. The web app will automatically load the new data
3. Users can click "Check from Database" to see results for nearby addresses
4. The map will show more 5G-available locations

## Troubleshooting

### Common Issues

1. **"No addresses found"**: Check your internet connection and OpenStreetMap availability
2. **"All addresses already checked"**: Increase the `--limit` to find more addresses
3. **Chrome driver issues**: The script automatically downloads the correct Chrome driver
4. **Slow performance**: Reduce the number of workers or check fewer addresses
5. **Many failed addresses**: Use `--retry-failed` to retry them, or reduce batch size

### Retry Strategy

If you have many failed addresses:

1. **First**: Run `./run_bulk_checker.sh --retry-failed` to retry failed addresses
2. **If still failing**: Reduce workers and batch size: `python bulk_checker.py --workers 1 --batch-size 10`
3. **Check logs**: Look at `bulk_checker.log` for specific error patterns
4. **Network issues**: Wait and try again later when network is more stable

### Logs

Check `bulk_checker.log` for detailed error messages and debugging information.

## Configuration

You can modify settings in `config.py`:
- `CBD_BBOX`: Melbourne CBD bounding box coordinates
- `TELSTRA_WAIT_SECONDS`: How long to wait for Telstra website responses
- `HEADLESS`: Whether to run Chrome in headless mode

## Safety Features

- **Rate limiting**: Built-in delays to be respectful to Telstra's servers
- **Error recovery**: Continues processing even if individual checks fail
- **Duplicate prevention**: Never checks the same address twice
- **Graceful interruption**: Can be safely interrupted with Ctrl+C
- **Batch processing**: Prevents overwhelming the system
- **Retry mechanism**: Handles temporary network issues and loading errors
- **Failed address tracking**: Persistent tracking of failed addresses for retry 