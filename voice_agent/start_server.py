#!/usr/bin/env python3
"""
Startup script for voice agent.
Handles proper path configuration and provides user-friendly error messages.
"""

import os
import sys

def setup_python_path():
    """Set up Python path for the project."""
    # Get the voice_agent directory
    voice_agent_dir = os.path.dirname(os.path.abspath(__file__))
    # Get the parent directory (project root) to allow imports like "voice_agent.core.router"
    project_root = os.path.dirname(voice_agent_dir)
    
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    print(f"✅ Project root added to Python path: {project_root}")
    return voice_agent_dir

def validate_environment():
    """Validate environment setup."""
    try:
        # Check if we can import the config module
        from voice_agent.config.environment import validate_environment as validate_env
        print("✅ Config module imported successfully")
        
        # Validate environment configuration
        if validate_env():
            print("✅ Environment configuration validated")
            return True
        else:
            print("⚠️ Environment validation failed, but continuing...")
            return True  # Allow startup for development
            
    except ImportError as e:
        print(f"❌ Failed to import config module: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Environment validation warning: {e}")
        return True  # Allow startup despite warnings

def main():
    """Main startup function."""
    print("🚀 Starting agent voice backend...")
    print("📋 Features: Restructured backend with /voice prefix endpoints")
    print("🔧 Compatible with existing frontend without changes")
    
    # Setup Python path
    voice_agent_dir = setup_python_path()
    
    # Validate environment
    if not validate_environment():
        print("❌ Failed to start server due to configuration issues")
        sys.exit(1)
    
    # Change to voice_agent directory
    os.chdir(voice_agent_dir)
    
    # Import and run the router
    try:
        print("📡 Starting voice agent router with /voice prefix endpoints...")
        print("🔗 Available endpoints:")
        print("   - https://localhost:8200/voice/health")
        print("   - https://localhost:8200/voice/connect")
        print("   - https://localhost:8200/voice/test-database-search")
        print("   - https://localhost:8200/voice/test-function-call")
        print("🔌 WebSocket endpoints:")
        print("   - wss://localhost:8200/voice/ws")
        print("   - wss://localhost:8200/voice/ws/tools")
        print("   - wss://localhost:8200/voice/ws/text-conversation")
        print("")
        
        # Import the router module and get the app
        from voice_agent.core.router import app
        import uvicorn
        
        # Run the FastAPI app
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8200,
            ssl_keyfile="./frontend/certificates/localhost-key.pem",
            ssl_certfile="./frontend/certificates/localhost.pem",
            log_level="info"
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()