# Railway Deployment Guide

This guide will help you deploy your 5G Availability Checker on Railway.

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Account**: Your code should be in a GitHub repository
3. **Chrome/Chromium**: Railway will install this automatically

## Deployment Steps

### 1. Prepare Your Repository

Make sure your repository contains these files:
- `app.py` - Main FastAPI application
- `requirements.txt` - Python dependencies
- `Procfile` - Tells Railway how to run the app
- `runtime.txt` - Python version specification
- `railway.json` - Railway configuration
- All other project files (templates, static, etc.)

### 2. Deploy to Railway

#### Option A: Deploy from GitHub (Recommended)

1. **Connect GitHub**:
   - Go to [railway.app](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

2. **Configure Environment**:
   - Railway will automatically detect it's a Python project
   - The `Procfile` will tell Railway to run `uvicorn app:app --host 0.0.0.0 --port $PORT`

3. **Deploy**:
   - Railway will automatically build and deploy your app
   - You'll get a URL like `https://your-app-name.railway.app`

#### Option B: Deploy from CLI

1. **Install Railway CLI**:
   ```bash
   npm install -g @railway/cli
   ```

2. **Login and Deploy**:
   ```bash
   railway login
   railway init
   railway up
   ```

### 3. Environment Variables (Optional)

You can set these in Railway dashboard under "Variables":

- `RAILWAY_ENVIRONMENT=production` - Enables cloud optimizations
- `PORT=8000` - Port (Railway sets this automatically)

### 4. Verify Deployment

1. **Check Health**: Visit your Railway URL
2. **Test Features**: Try the main pages:
   - `/` - Main form
   - `/dashboard` - Dashboard
   - `/map` - Interactive map

## Important Notes

### Cloud Limitations

1. **Selenium in Cloud**: 
   - Chrome runs in headless mode
   - Some websites may block automated access
   - Telstra website may have additional protections

2. **Data Persistence**:
   - Railway provides ephemeral storage
   - Your `results.csv` will reset on each deployment
   - Consider using Railway's persistent storage or external database

3. **Resource Limits**:
   - Railway has memory and CPU limits
   - Bulk checking may be slower than local
   - Consider reducing concurrent workers

### Recommended Settings for Cloud

Update your `bulk_checker.py` settings for cloud deployment:

```python
# Conservative cloud settings
WORKERS = 1  # Reduce from 2-3 to 1
BATCH_SIZE = 20  # Reduce from 30-50 to 20
DELAY_BETWEEN_BATCHES = 60  # Increase from 30 to 60 seconds
```

### Troubleshooting

1. **Build Failures**:
   - Check `requirements.txt` has all dependencies
   - Ensure Python version in `runtime.txt` is supported
   - Check Railway logs for specific errors

2. **Runtime Errors**:
   - Chrome/Selenium issues: Check cloud Chrome options
   - Memory issues: Reduce concurrent workers
   - Timeout issues: Increase wait times

3. **Performance Issues**:
   - Reduce batch sizes
   - Increase delays between requests
   - Use fewer workers

## Monitoring

1. **Railway Dashboard**: Monitor logs, metrics, and deployments
2. **Application Logs**: Check for errors and performance issues
3. **Health Checks**: Railway will restart failed deployments

## Scaling

1. **Free Tier**: Limited resources, good for testing
2. **Pro Plan**: More resources, better for production
3. **Custom Domain**: Add your own domain name

## Security Considerations

1. **Environment Variables**: Store sensitive data in Railway variables
2. **Rate Limiting**: Be respectful of Telstra's servers
3. **User Input**: Validate all user inputs
4. **HTTPS**: Railway provides SSL certificates automatically

## Next Steps

1. **Database**: Consider using Railway's PostgreSQL or external database
2. **Caching**: Add Redis for better performance
3. **Monitoring**: Set up alerts for errors and performance
4. **Backup**: Implement data backup strategies

## Support

- **Railway Docs**: [docs.railway.app](https://docs.railway.app)
- **Railway Discord**: [discord.gg/railway](https://discord.gg/railway)
- **Project Issues**: Check your GitHub repository issues 