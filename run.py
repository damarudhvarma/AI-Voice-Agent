#!/usr/bin/env python3
"""
Universal entry point for AI Voice Agent
Works from any directory and handles path resolution automatically
"""

import os
import sys

def find_server_directory():
    """Find the server directory from various possible locations"""
    current_dir = os.path.abspath(os.getcwd())
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Possible server directory locations
    possible_paths = [
        os.path.join(current_dir, 'server'),  # ./server
        os.path.join(script_dir, 'server'),   # script_dir/server
        current_dir if os.path.basename(current_dir) == 'server' else None,  # already in server
        script_dir if os.path.basename(script_dir) == 'server' else None,    # script in server
    ]
    
    for path in possible_paths:
        if path and os.path.exists(path) and os.path.isfile(os.path.join(path, 'app_refactored.py')):
            return path
    
    return None

def setup_python_path(server_dir):
    """Setup Python path for imports"""
    if server_dir not in sys.path:
        sys.path.insert(0, server_dir)
    
    # Also add parent for absolute imports
    parent_dir = os.path.dirname(server_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

def main():
    """Main entry point"""
    print("🚀 AI Voice Agent Universal Launcher")
    
    # Find server directory
    server_dir = find_server_directory()
    if not server_dir:
        print("❌ Could not find server directory with app_refactored.py")
        print(f"📍 Current directory: {os.getcwd()}")
        print(f"📍 Script directory: {os.path.dirname(os.path.abspath(__file__))}")
        sys.exit(1)
    
    print(f"✅ Found server directory: {server_dir}")
    
    # Change to server directory
    os.chdir(server_dir)
    print(f"✅ Changed working directory to: {server_dir}")
    
    # Setup Python path
    setup_python_path(server_dir)
    print(f"✅ Setup Python path: {sys.path[0]}")
    
    # Set environment variables
    os.environ['PYTHONPATH'] = server_dir
    port = int(os.environ.get('PORT', 5000))
    
    print(f"🌐 Starting on port: {port}")
    print(f"📁 Files in server dir: {[f for f in os.listdir('.') if f.endswith('.py')]}")
    
    try:
        # Import and run the Flask app
        from app_refactored import app
        print("✅ Successfully imported Flask app")
        
        # Start the application
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print(f"📁 Directory contents: {os.listdir('.')}")
        print(f"🔍 Python path: {sys.path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Startup error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
