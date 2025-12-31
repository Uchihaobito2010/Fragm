"""
Local Development Server
Run: python main.py
Access: http://localhost:8000
"""

import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("Fragment Username Checker API - Local Development")
    print("=" * 60)
    print("\n🌐 Starting server...")
    print("\n📋 Available endpoints:")
    print("   • http://localhost:8000/          - Landing page")
    print("   • http://localhost:8000/docs      - API documentation")
    print("   • http://localhost:8000/health    - Health check")
    print("   • http://localhost:8000/username  - Check username")
    print("\n🔧 Testing:")
    print("   Try: http://localhost:8000/username?username=test")
    print("\n" + "=" * 60)
    
    uvicorn.run(
        "api.index:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
  )
