"""
Fragment Username Checker API for Vercel
Main handler file
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from user_agent import generate_user_agent
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
import json

# Create FastAPI app
app = FastAPI(
    title="Fragment Username Checker API",
    description="Check Telegram username availability on Fragment.com",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create session with user agent
session = requests.Session()
session.headers.update({
    "User-Agent": generate_user_agent(),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
})

DEVELOPER = "@Aotpy"
CHANNEL = "@obitoapi / @obitostuffs"

# Pydantic models
class UsernameRequest(BaseModel):
    username: str

class HealthResponse(BaseModel):
    status: str
    developer: str
    channel: str
    timestamp: str
    version: str

def get_fragment_api_hash():
    """Get the dynamic API hash from Fragment.com"""
    try:
        response = session.get(
            "https://fragment.com",
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        response.raise_for_status()
        
        # Look for API hash in script tags
        html_content = response.text
        hash_pattern = r'hash=([a-fA-F0-9]{64})'
        match = re.search(hash_pattern, html_content)
        
        if match:
            return match.group(1)
        
        # Alternative pattern
        alt_pattern = r'"hash":"([a-fA-F0-9]{64})"'
        alt_match = re.search(alt_pattern, html_content)
        if alt_match:
            return alt_match.group(1)
            
        return None
    except Exception as e:
        print(f"Error getting fragment hash: {str(e)}")
        return None

def check_fragment_username(username: str, max_retries: int = 3):
    """Check username availability on Fragment.com"""
    api_hash = get_fragment_api_hash()
    
    if not api_hash:
        return {
            "error": True,
            "message": "Failed to get Fragment API hash",
            "username": username,
            "available": None,
            "developer": DEVELOPER,
            "channel": CHANNEL
        }
    
    api_url = f"https://fragment.com/api?hash={api_hash}"
    
    payload = {
        "type": "usernames",
        "query": username,
        "method": "searchAuctions"
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Origin": "https://fragment.com",
        "Referer": "https://fragment.com/",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    for attempt in range(max_retries):
        try:
            response = session.post(
                api_url,
                data=payload,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            
            if "html" not in data or not data["html"]:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return {
                    "error": True,
                    "message": "No data returned from Fragment",
                    "username": username,
                    "available": None,
                    "developer": DEVELOPER,
                    "channel": CHANNEL
                }
            
            # Parse the HTML response
            soup = BeautifulSoup(data["html"], 'html.parser')
            
            # Look for username elements
            username_elem = soup.find("div", class_="tm-value")
            if not username_elem:
                # Username might not exist or be available
                return {
                    "error": False,
                    "username": f"@{username}",
                    "available": True,
                    "status": "Available",
                    "price": "Not listed",
                    "message": "✅ This username might be available",
                    "developer": DEVELOPER,
                    "channel": CHANNEL
                }
            
            # Extract data
            found_username = username_elem.get_text(strip=True)
            price_elem = username_elem.find_next("div", class_="tm-value")
            status_elem = price_elem.find_next("div", class_="tm-value") if price_elem else None
            
            price = price_elem.get_text(strip=True) if price_elem else "Unknown"
            status = status_elem.get_text(strip=True) if status_elem else "Unknown"
            
            available = "unavailable" in status.lower()
            
            return {
                "error": False,
                "username": found_username,
                "price": price,
                "status": status,
                "available": available,
                "message": "✅ Available for purchase" if available else "❌ Not available",
                "developer": DEVELOPER,
                "channel": CHANNEL,
                "source": "fragment.com"
            }
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return {
                "error": True,
                "message": f"Network error: {str(e)}",
                "username": username,
                "available": None,
                "developer": DEVELOPER,
                "channel": CHANNEL
            }
        except Exception as e:
            return {
                "error": True,
                "message": f"Unexpected error: {str(e)}",
                "username": username,
                "available": None,
                "developer": DEVELOPER,
                "channel": CHANNEL
            }
    
    return {
        "error": True,
        "message": "Max retries exceeded",
        "username": username,
        "available": None,
        "developer": DEVELOPER,
        "channel": CHANNEL
    }

# ============ API ENDPOINTS ============

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with HTML welcome page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Fragment Username Checker API</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: white;
            }
            .container {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 40px;
                margin-top: 20px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
            h1 {
                margin-top: 0;
                font-size: 2.5em;
                background: linear-gradient(45deg, #fff, #f0f0f0);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .endpoint {
                background: rgba(255, 255, 255, 0.15);
                padding: 15px;
                border-radius: 10px;
                margin: 15px 0;
                border-left: 4px solid #00d4aa;
            }
            code {
                background: rgba(0, 0, 0, 0.3);
                padding: 2px 8px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
            }
            .btn {
                display: inline-block;
                background: #00d4aa;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 8px;
                font-weight: bold;
                margin: 10px 5px;
                transition: transform 0.2s;
            }
            .btn:hover {
                transform: translateY(-2px);
                background: #00c49a;
            }
            .btn-docs {
                background: #667eea;
            }
            .btn-docs:hover {
                background: #5a6fd8;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Fragment Username Checker API</h1>
            <p>Check Telegram username availability on Fragment.com</p>
            
            <h2>📚 API Endpoints</h2>
            
            <div class="endpoint">
                <strong>GET /username</strong><br>
                Check username availability<br>
                <code>/username?username=your_username</code>
            </div>
            
            <div class="endpoint">
                <strong>POST /username</strong><br>
                Check username (with JSON body)<br>
                <code>{ "username": "your_username" }</code>
            </div>
            
            <div class="endpoint">
                <strong>GET /health</strong><br>
                Health check endpoint
            </div>
            
            <h2>🔗 Quick Links</h2>
            <a href="/docs" class="btn btn-docs">Open API Documentation</a>
            <a href="/redoc" class="btn btn-docs">Open ReDoc</a>
            
            <h2>🚀 Try It Now</h2>
            <p>Check if a username is available:</p>
            <div class="endpoint">
                <code><a href="/username?username=test" style="color: #00d4aa;">/username?username=test</a></code>
            </div>
            
            <h2>👨‍💻 Developer</h2>
            <p><strong>Developer:</strong> @Aotpy</p>
            <p><strong>Channel:</strong> @obitoapi / @obitostuffs</p>
            <p><strong>Version:</strong> 2.0.0</p>
        </div>
        
        <script>
            // Add click animation to buttons
            document.querySelectorAll('.btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    this.style.transform = 'scale(0.95)';
                    setTimeout(() => {
                        this.style.transform = '';
                    }, 150);
                });
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        developer=DEVELOPER,
        channel=CHANNEL,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        version="2.0.0"
    )

@app.get("/username")
async def check_username_get(
    username: str = Query(
        ...,
        min_length=1,
        max_length=32,
        description="Telegram username to check (without @)",
        example="obito"
    )
):
    """
    Check if a Telegram username is available on Fragment.com
    
    - **username**: The Telegram username (without @ symbol)
    """
    # Clean and validate username
    username = username.strip().lower().replace('@', '')
    
    if not username:
        raise HTTPException(
            status_code=400,
            detail="Username is required"
        )
    
    # Validate username format
    if not re.match(r'^[a-zA-Z0-9_]{1,32}$', username):
        raise HTTPException(
            status_code=400,
            detail="Invalid username format. Only letters, numbers, and underscores allowed (1-32 characters)."
        )
    
    # Check username
    result = check_fragment_username(username)
    
    if result.get("error"):
        raise HTTPException(
            status_code=500,
            detail=result.get("message", "Unknown error occurred")
        )
    
    return result

@app.post("/username")
async def check_username_post(request: UsernameRequest):
    """
    Check username availability using POST method
    
    - **request**: JSON object with username field
    """
    username = request.username.strip().lower().replace('@', '')
    
    if not username:
        raise HTTPException(
            status_code=400,
            detail="Username is required in request body"
        )
    
    # Validate username format
    if not re.match(r'^[a-zA-Z0-9_]{1,32}$', username):
        raise HTTPException(
            status_code=400,
            detail="Invalid username format. Only letters, numbers, and underscores allowed (1-32 characters)."
        )
    
    # Check username
    result = check_fragment_username(username)
    
    if result.get("error"):
        raise HTTPException(
            status_code=500,
            detail=result.get("message", "Unknown error occurred")
        )
    
    return result

@app.get("/batch")
async def check_batch_usernames(
    usernames: str = Query(
        ...,
        description="Comma-separated list of usernames (max 5)",
        example="obito,naruto,sasuke"
    )
):
    """
    Check multiple usernames at once
    
    - **usernames**: Comma-separated list of usernames
    """
    username_list = [u.strip().lower().replace('@', '') for u in usernames.split(',')]
    username_list = [u for u in username_list if u]
    
    if not username_list:
        raise HTTPException(
            status_code=400,
            detail="No valid usernames provided"
        )
    
    if len(username_list) > 5:
        raise HTTPException(
            status_code=400,
            detail="Maximum 5 usernames allowed per batch"
        )
    
    results = []
    for username in username_list:
        if re.match(r'^[a-zA-Z0-9_]{1,32}$', username):
            result = check_fragment_username(username)
            results.append(result)
        else:
            results.append({
                "error": True,
                "message": "Invalid username format",
                "username": username,
                "available": None
            })
    
    return {
        "count": len(results),
        "results": results,
        "developer": DEVELOPER,
        "channel": CHANNEL
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": True,
            "message": f"Endpoint {request.url.path} not found",
            "available_endpoints": [
                "/",
                "/docs",
                "/redoc",
                "/health",
                "/username",
                "/batch"
            ],
            "developer": DEVELOPER,
            "channel": CHANNEL
        }
    )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error",
            "developer": DEVELOPER,
            "channel": CHANNEL
        }
    )

# Vercel serverless function handler
def handler(request, response):
    """Vercel serverless function handler"""
    from mangum import Mangum
    mangum_handler = Mangum(app)
    return mangum_handler(request, response)
