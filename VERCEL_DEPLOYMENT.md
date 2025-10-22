# Vercel Deployment Guide

## Issues Fixed

### 1. **WebSocket Support**
- **Problem**: Vercel doesn't support WebSocket connections in serverless functions
- **Solution**: Updated frontend to use REST API endpoints instead of WebSockets
  - `/api/check-live` - For live checking (returns mock data in serverless)
  - `/api/check-from-database` - For database checking

### 2. **Missing Dependencies**
- **Problem**: `overpy` package was missing from `requirements-vercel.txt`
- **Solution**: Added `overpy==0.7` to requirements

### 3. **CSV File Deployment**
- **Problem**: CSV files weren't being included in the Vercel deployment
- **Solution**: 
  - Updated `vercel.json` to include CSV files using `includeFiles`
  - Created `.vercelignore` to ensure CSV files are not ignored
  - Enhanced file loading logic to check multiple paths (Vercel uses `/var/task/`)

## Deployment Steps

### 1. Deploy to Vercel

```bash
# Install Vercel CLI if you haven't
npm i -g vercel

# Login to Vercel
vercel login

# Deploy
vercel --prod
```

### 2. Verify Deployment

After deployment, check these endpoints:

1. **Health Check**: `https://your-app.vercel.app/health`
   - Should show `status: "healthy"`
   - Should show `files_available` with CSV files listed
   - Should show `database_status.results_ready: true`

2. **Debug Info**: `https://your-app.vercel.app/debug`
   - Should show CSV files in `csv_files` array
   - Should show `app_state.results_count > 0`

3. **Database Status**: `https://your-app.vercel.app/api/database-status`
   - Should show `database_ready: true`
   - Should show `address_count > 0`

### 3. Test the Application

1. Visit `https://your-app.vercel.app/`
2. Enter an address (e.g., "340 Lygon Street Carlton VIC")
3. Click "Check from Database"
4. You should see results from the CSV file

## Features in Vercel Deployment

### ✅ Available Features
- Web interface
- Database checking (from `results.csv`)
- Map visualization (from cached data)
- Dashboard

### ❌ Disabled Features
- Real-time checking (requires Selenium, not available in serverless)
- Bulk checking (requires long-running processes)

## Troubleshooting

### No Results Showing

1. **Check if CSV is loaded**:
   ```bash
   curl https://your-app.vercel.app/health
   ```
   Look for `database_status.results_count > 0`

2. **Check file availability**:
   ```bash
   curl https://your-app.vercel.app/debug
   ```
   Look for `csv_files` array - should include `results.csv`

3. **Test API directly**:
   ```bash
   curl "https://your-app.vercel.app/api/check-from-database?n=5"
   ```
   Should return sample addresses

### Logs

View logs in Vercel Dashboard:
1. Go to your project in Vercel
2. Click on "Deployments"
3. Click on the latest deployment
4. View "Functions" tab to see logs

The app includes extensive logging:
- File loading status
- Database initialization
- API request handling
- Error details with stack traces

## Configuration

### Environment Variables (Optional)

You can set these in Vercel Dashboard under Project Settings > Environment Variables:

- `VERCEL=1` (automatically set by Vercel)
- `PYTHON_VERSION=3.11` (already in vercel.json)

### File Size Limits

Vercel has a 50MB limit for serverless functions. The current configuration:
- `maxLambdaSize: "50mb"`
- If your CSV files are very large, you might need to:
  1. Split them into smaller files
  2. Use Vercel Blob storage
  3. Use an external database

## Alternative: Deploy to Railway

If you need real-time checking with Selenium, consider deploying to Railway instead:

1. Railway supports long-running processes
2. Can run Chrome/Selenium
3. Better for CPU-intensive tasks

See `README.md` for Railway deployment instructions.

## Files Modified

1. `requirements-vercel.txt` - Added `overpy` dependency
2. `vercel.json` - Updated to include CSV files
3. `.vercelignore` - Created to ensure CSV files are deployed
4. `templates/form.html` - Updated to use REST APIs instead of WebSockets
5. `app.py` - Enhanced error handling and logging, improved file path resolution

