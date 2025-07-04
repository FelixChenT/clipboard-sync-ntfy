#!/bin/bash

# Clipboard Sync GUI Startup Script
# This script helps you start the GUI application

set -e

echo "🚀 Starting Clipboard Sync GUI..."

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Please run this script from the gui directory"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is not installed. Please install Node.js 16 or later."
    exit 1
fi

# Check if dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install --no-audit
fi

# Check if React app dependencies are installed
if [ ! -d "src/renderer/node_modules" ]; then
    echo "📦 Installing React app dependencies..."
    cd src/renderer && npm install --no-audit && cd ../..
fi

# Build React app if build directory doesn't exist
if [ ! -d "src/renderer/build" ]; then
    echo "🔨 Building React application..."
    npm run build:react
fi

# Start the application
echo "✅ Starting Clipboard Sync GUI..."
npm start
