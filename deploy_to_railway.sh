#!/bin/bash

# Railway Deployment Script
# This script helps prepare and deploy the 5G Availability Checker to Railway

set -e

echo "=== Railway Deployment Script ==="
echo

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "Railway CLI not found. Installing..."
    npm install -g @railway/cli
else
    echo "Railway CLI found: $(railway --version)"
fi

echo

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "ERROR: Not in a git repository. Please initialize git and commit your changes:"
    echo "  git init"
    echo "  git add ."
    echo "  git commit -m 'Initial commit for Railway deployment'"
    echo "  git remote add origin <your-github-repo-url>"
    echo "  git push -u origin main"
    exit 1
fi

echo "Git repository found: $(git remote get-url origin 2>/dev/null || echo 'No remote set')"
echo

# Check required files
echo "Checking required files for Railway deployment..."

required_files=("app.py" "requirements.txt" "Procfile" "runtime.txt" "railway.json")
missing_files=()

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  + $file"
    else
        echo "  - $file (missing)"
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -ne 0 ]; then
    echo
    echo "ERROR: Missing required files for Railway deployment:"
    printf '  %s\n' "${missing_files[@]}"
    exit 1
fi

echo
echo "All required files present!"
echo

# Check if user is logged into Railway
if ! railway whoami &> /dev/null; then
    echo "Not logged into Railway. Please login:"
    echo "  railway login"
    echo
    echo "After logging in, run this script again."
    exit 1
fi

echo "Logged into Railway as: $(railway whoami)"
echo

# Check if project is initialized
if [ ! -f ".railway" ]; then
    echo "Railway project not initialized. Initializing..."
    railway init
    echo
fi

echo "Railway project initialized."
echo

# Show deployment options
echo "=== Deployment Options ==="
echo "1. Deploy to Railway (railway up)"
echo "2. Open Railway dashboard"
echo "3. View Railway logs"
echo "4. Exit"
echo

read -p "Choose an option (1-4): " choice

case $choice in
    1)
        echo
        echo "Deploying to Railway..."
        echo "This may take a few minutes..."
        railway up
        echo
        echo "Deployment completed!"
        echo "Your app should be available at the URL shown above."
        ;;
    2)
        echo
        echo "Opening Railway dashboard..."
        railway open
        ;;
    3)
        echo
        echo "Showing Railway logs..."
        railway logs
        ;;
    4)
        echo
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo
        echo "Invalid option. Exiting..."
        exit 1
        ;;
esac

echo
echo "=== Deployment Complete ==="
echo
echo "Next steps:"
echo "1. Visit your Railway URL to test the app"
echo "2. Check the Railway dashboard for logs and metrics"
echo "3. Set up environment variables if needed"
echo "4. Consider upgrading to Pro plan for better performance"
echo
echo "For more help, see RAILWAY_DEPLOYMENT.md" 