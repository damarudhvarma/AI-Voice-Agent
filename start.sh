#!/bin/bash

# AI Voice Agent Production Start Script for Render

echo "🚀 Starting AI Voice Agent on Render..."

# Get port from environment (Render sets this automatically)
PORT=${PORT:-5000}
echo "📡 Using port: $PORT"

# Set production environment
export FLASK_ENV=production
export PYTHONUNBUFFERED=1

# Change to server directory
cd server

# Check if required API keys are set
echo "🔑 Checking API key configuration..."
if [ -z "$ASSEMBLYAI_API_KEY" ]; then
    echo "⚠️  Warning: ASSEMBLYAI_API_KEY not set"
fi
if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  Warning: GEMINI_API_KEY not set"
fi
if [ -z "$MURF_API_KEY" ]; then
    echo "⚠️  Warning: MURF_API_KEY not set"
fi

# Create uploads directory if it doesn't exist
mkdir -p uploads
echo "📁 Created uploads directory"

# Start the application
echo "🎤 Starting AI Voice Agent server..."
python app_refactored.py
