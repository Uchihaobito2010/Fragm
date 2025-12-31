"""
Local Development Server
"""
import uvicorn

if __name__ == "__main__":
    print("Starting Fragment Username Checker API...")
    print("Local URL: http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    print("\nTest endpoints:")
    print("  GET  /username?username=test")
    print("  POST /username")
    print("  GET  /health")
    
    uvicorn.run(
        "api.index:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
