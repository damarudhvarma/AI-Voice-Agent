@echo off
REM AI Voice Agent Production Start Script for Render (Windows)

echo 🚀 Starting AI Voice Agent on Render...

REM Get port from environment (Render sets this automatically)
if not defined PORT set PORT=5000
echo 📡 Using port: %PORT%

REM Set production environment
set FLASK_ENV=production
set PYTHONUNBUFFERED=1

REM Change to server directory
cd server

REM Check if required API keys are set
echo 🔑 Checking API key configuration...
if not defined ASSEMBLYAI_API_KEY echo ⚠️  Warning: ASSEMBLYAI_API_KEY not set
if not defined GEMINI_API_KEY echo ⚠️  Warning: GEMINI_API_KEY not set
if not defined MURF_API_KEY echo ⚠️  Warning: MURF_API_KEY not set

REM Create uploads directory if it doesn't exist
if not exist uploads mkdir uploads
echo 📁 Created uploads directory

REM Start the application
echo 🎤 Starting AI Voice Agent server...
python app_refactored.py
