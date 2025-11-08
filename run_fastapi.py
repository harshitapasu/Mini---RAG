#!/usr/bin/env python3
"""
Mini-RAG Assistant FastAPI Startup Script
"""

import os
import sys
import subprocess
import uvicorn
from pathlib import Path

def check_requirements():
    """Check if required packages are installed."""
    required_packages = [
        'fastapi',
        'uvicorn',
        'python-multipart',
        'google-generativeai',
        'chromadb',
        'langchain',
        'pdfplumber'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            if package == 'google-generativeai':
                import google.generativeai
            elif package == 'python-multipart':
                import multipart
            else:
                __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Please install requirements with:")
        print("   pip install -r requirements.txt")
        return False
    
    print("✅ All required packages are installed!")
    return True

def create_directories():
    """Create necessary directories."""
    directories = ['chroma_db', 'static', 'knowledge_base']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"📁 Directory '{directory}' ready")

def main():
    """Main startup function."""
    print("🤖 Mini-RAG Assistant FastAPI Startup")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists('fastapi_app_clean.py'):
        print("❌ Error: fastapi_app_clean.py not found!")
        print("   Please run this script from the Mini-RAG directory")
        sys.exit(1)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    print("\n🚀 Starting FastAPI server...")
    print("📋 Available endpoints:")
    print("   - Web Interface: http://localhost:8000")
    print("   - API Documentation: http://localhost:8000/docs")
    print("   - System Status: http://localhost:8000/status")
    print("   - Health Check: http://localhost:8000/health")
    
    print("\n⚠️  Important:")
    print("   1. Make sure you have a Google AI API key")
    print("   2. Configure the API key in the web interface")
    print("   3. Upload documents before asking questions")
    
    print("\n🔧 Configuration:")
    print("   - Host: 0.0.0.0 (accessible from other devices)")
    print("   - Port: 8000")
    print("   - Reload: Enabled (for development)")
    
    print("\n" + "=" * 40)
    print("Press Ctrl+C to stop the server")
    print("=" * 40 + "\n")
    
    try:
        # Start the FastAPI server
        uvicorn.run(
            "fastapi_app_clean:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()