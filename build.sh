#!/bin/bash

# Build script for Netlify deployment
echo "Starting build process..."

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create a simple index.html for the root path
echo "Creating index.html..."
cat > index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>5G Availability Checker</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .api-info {
            background: #e8f4fd;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .endpoint {
            background: #f8f9fa;
            padding: 10px;
            margin: 10px 0;
            border-left: 4px solid #007bff;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>5G Availability Checker API</h1>
        <p>Welcome to the 5G Availability Checker API. This service helps you check 5G availability at specific addresses.</p>
        
        <div class="api-info">
            <h3>Available Endpoints:</h3>
            <div class="endpoint">GET /docs - API Documentation</div>
            <div class="endpoint">GET /health - Health Check</div>
            <div class="endpoint">POST /check-address - Check 5G availability for an address</div>
            <div class="endpoint">GET /map - Interactive map view</div>
        </div>
        
        <p>For detailed API documentation, visit <a href="/docs">/docs</a></p>
    </div>
</body>
</html>
EOF

echo "Build completed successfully!"
