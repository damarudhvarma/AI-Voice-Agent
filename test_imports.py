#!/usr/bin/env python3
"""
Test script to verify all imports work correctly
"""

import os
import sys

def setup_paths():
    """Setup Python paths for testing"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # If we're in the root, add server to path
    server_dir = os.path.join(current_dir, 'server')
    if os.path.exists(server_dir):
        os.chdir(server_dir)
        sys.path.insert(0, server_dir)
        print(f"✅ Using server directory: {server_dir}")
    elif os.path.basename(current_dir) == 'server':
        # Already in server directory
        sys.path.insert(0, current_dir)
        print(f"✅ Already in server directory: {current_dir}")
    else:
        print(f"❌ Cannot find server directory from: {current_dir}")
        return False
    
    return True

def test_imports():
    """Test all critical imports"""
    tests = []
    
    # Test basic modules
    try:
        from utils.config import Config
        tests.append(("✅", "utils.config"))
    except ImportError as e:
        tests.append(("❌", f"utils.config - {e}"))
    
    try:
        from utils.logger import get_logger, setup_logger
        tests.append(("✅", "utils.logger"))
    except ImportError as e:
        tests.append(("❌", f"utils.logger - {e}"))
    
    try:
        from models.schemas import TTSRequest, ErrorType, MessageRole
        tests.append(("✅", "models.schemas"))
    except ImportError as e:
        tests.append(("❌", f"models.schemas - {e}"))
    
    # Test service imports
    services = ['stt_service', 'tts_service', 'llm_service', 'chat_manager', 'file_service', 'voice_commands_service']
    
    for service in services:
        try:
            module = __import__(f'services.{service}', fromlist=[service])
            tests.append(("✅", f"services.{service}"))
        except ImportError as e:
            tests.append(("❌", f"services.{service} - {e}"))
    
    # Print results
    print("\n📋 Import Test Results:")
    print("=" * 50)
    for status, module in tests:
        print(f"{status} {module}")
    
    failed = [t for t in tests if t[0] == "❌"]
    if failed:
        print(f"\n❌ {len(failed)} imports failed out of {len(tests)}")
        return False
    else:
        print(f"\n✅ All {len(tests)} imports successful!")
        return True

def main():
    """Main test function"""
    print("🧪 Testing AI Voice Agent imports...")
    
    if not setup_paths():
        sys.exit(1)
    
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🐍 Python path: {sys.path[0]}")
    print(f"📄 Files: {[f for f in os.listdir('.') if f.endswith('.py')]}")
    
    if test_imports():
        print("\n🎉 All imports working correctly!")
        
        # Try to import the main app
        try:
            from app_refactored import app
            print("✅ Main Flask app imports successfully!")
            print("🚀 Ready for deployment!")
        except ImportError as e:
            print(f"❌ Main app import failed: {e}")
            sys.exit(1)
    else:
        print("\n💥 Some imports failed - check the errors above")
        sys.exit(1)

if __name__ == '__main__':
    main()
