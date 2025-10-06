# Vercel Deployment Guide

## Overview

This application has been modified to support Vercel deployment by removing Selenium dependencies and adding fallback logic for serverless environments.

## Changes Made

### 1. Python Version
- Updated `runtime.txt` to use Python 3.12 (required by Vercel)

### 2. Dependencies
- Removed `selenium==4.15.2` and `webdriver-manager==4.0.1` from `requirements.txt`
- These packages cannot run in Vercel's serverless environment

### 3. Code Modifications
- Added graceful import handling for Selenium in `app.py` and `telstra5g.py`
- Added fallback methods that return mock data when Selenium is not available
- Updated cloud environment detection to include Vercel

### 4. Configuration
- Created `vercel.json` for proper Vercel deployment configuration
- Updated `config.py` to detect Vercel environment

## Limitations

**Important**: The 5G availability checking functionality will not work in Vercel because:
- Selenium requires a full browser environment
- Vercel's serverless functions cannot run browser automation
- The app will return "serverless_mode" status for all address checks

## Alternative Deployment Options

For full functionality, consider deploying to:
1. **Railway** (already configured) - Supports Docker containers with browsers
2. **Google Cloud Run** - Can run containers with Selenium
3. **AWS ECS/Fargate** - Container-based deployment
4. **DigitalOcean App Platform** - Supports Docker containers

## Vercel Deployment

To deploy to Vercel:

1. Install Vercel CLI: `npm i -g vercel`
2. Run: `vercel`
3. Follow the prompts to configure your project

The app will deploy successfully but with limited functionality (no actual 5G checking).
