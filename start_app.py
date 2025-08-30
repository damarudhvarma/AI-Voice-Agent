#!/usr/bin/env python3
"""
Startup script for AI Voice Agent on Render
This script ensures correct working directory and Python path setup
"""

import os
import sys

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Change to server directory
server_dir = os.path.join(script_dir, 'server')
if os.path.exists(server_dir):
    os.chdir(server_dir)
    print(f"✅ Changed working directory to: {server_dir}")
else:
    # If we're already in server directory
    if os.path.basename(script_dir) == 'server':
        server_dir = script_dir
        print(f"✅ Already in server directory: {server_dir}")
    else:
        print(f"❌ Server directory not found. Current dir: {script_dir}")
        sys.exit(1)

# Add server directory to Python path
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)
    print(f"✅ Added to Python path: {server_dir}")

# Set environment variables
os.environ['PYTHONPATH'] = server_dir
os.environ['FLASK_ENV'] = os.environ.get('FLASK_ENV', 'production')

print(f"🔧 Working directory: {os.getcwd()}")
print(f"🔧 Python path: {sys.path[0]}")
print(f"🔧 Environment: {os.environ.get('FLASK_ENV')}")

# Import and run the Flask app
try:
    from app_refactored import app
    print("✅ Successfully imported Flask app")
    
    # Get port from environment
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Starting server on port: {port}")
    
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=False)
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"📁 Available files: {os.listdir('.')}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Startup error: {e}")
    sys.exit(1)
