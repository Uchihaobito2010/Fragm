"""
Fragment Username Checker API
Check Telegram username availability on Fragment.com
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from user_agent import generate_user_agent
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional
import datetime

# Initialize FastAPI app
app = FastAPI(
    title="Fragment Username Checker API",
    description="API to check Telegram username availability on Fragment.com",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global constants
DEVELOPER = "@Aotpy"
CHANNEL = "@obitoapi / @obitostuffs"

# Create requests session
session = requests.Session()

def update_session_headers():
    """Update session headers with fresh user agent"""
    session.headers.update({
        "User-Agent": generate_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    })

# Initial header update
update_session_headers()

# Pydantic models
class UsernameRequest(BaseModel):
    username: str

class UsernameResponse(BaseModel):
    username: str
    price: Optional[str] = None
    status: str
    available: bool
    message: str
    developer: str = DEVELOPER
    channel: str = CHANNEL
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    message: str
    developer: str = DEVELOPER
    channel: str = CHANNEL
    timestamp: str
    version: str = "2.0.0"

class ErrorResponse(BaseModel):
    error: bool
    message: str
    developer: str = DEVELOPER
    channel: str = CHANNEL
    timestamp: str

def get_fragment_api_hash():
    """
    Extract the API hash from fragment.com
    Returns: API hash string or None if not found
    """
    try:
        update_session_headers()
        
        response = session.get(
            "https://fragment.com",
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }
        )
        response.raise_for_status()
        
        # Look for hash in the HTML
        html_content = response.text
        
        # Try different patterns to find the hash
        patterns = [
            r'hash=([a-fA-F0-9]{64})',
            r'"hash":"([a-fA-F0-9]{64})"',
            r'apiUrl.*hash=([a-fA-F0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content)
            if match:
                return match.group(1)
        
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"Error getting API hash: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error getting API hash: {str(e)}")
        return None

def check_username_fragment(username: str, retries: int = 2):
    """
    Check username availability on Fragment.com
    """
    api_hash = get_fragment_api_hash()
    
    if not api_hash:
        return {
            "error": True,
            "message": "Unable to connect to Fragment.com. Please try again later.",
            "username": f"@{username}",
            "available": None
        }
    
    api_url = f"https://fragment.com/api?hash={api_hash}"
    
    # Prepare request data
    data = {
        "type": "usernames",
        "query": username,
        "method": "searchAuctions"
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://fragment.com",
        "Referer": "https://fragment.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for attempt in range(retries + 1):
        try:
            response = session.post(
                api_url,
                data=data,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            
            json_data = response.json()
            
            if "html" not in json_data or not json_data["html"]:
                # Empty response usually means username is not listed
                return {
                    "error": False,
                    "username": f"@{username}",
                    "status": "Not Listed",
                    "available": True,
                    "price": "N/A",
                    "message": "✅ Username is not listed on Fragment (might be available)"
                }
            
            # Parse the HTML response
            soup = BeautifulSoup(json_data["html"], 'html.parser')
            
            # Find all tm-value divs
            tm_values = soup.find_all("div", class_="tm-value")
            
            if not tm_values or len(tm_values) < 3:
                # Not enough data, might be available
                return {
                    "error": False,
                    "username": f"@{username}",
                    "status": "Not Found",
                    "available": True,
                    "price": "N/A",
                    "message": "✅ Username not found on Fragment (likely available)"
                }
            
            # Extract information
            found_username = tm_values[0].get_text(strip=True) if len(tm_values) > 0 else f"@{username}"
            price = tm_values[1].get_text(strip=True) if len(tm_values) > 1 else "Unknown"
            status = tm_values[2].get_text(strip=True) if len(tm_values) > 2 else "Unknown"
            
            # Determine availability
            available = "unavailable" in status.lower()
            
            return {
                "error": False,
                "username": found_username,
                "price": price,
                "status": status,
                "available": available,
                "message": "✅ Available for purchase" if available else "❌ Not available on Fragment"
            }
            
        except requests.exceptions.Timeout:
            if attempt < retries:
                time.sleep(1)
                continue
            return {
                "error": True,
                "message": "Request timeout. Fragment.com is taking too long to respond.",
                "username": f"@{username}",
                "available": None
            }
        except requests.exceptions.RequestException as e:
            if attempt < retries:
                time.sleep(1)
                continue
            return {
                "error": True,
                "message": f"Network error: {str(e)}",
                "username": f"@{username}",
                "available": None
            }
        except Exception as e:
            return {
                "error": True,
                "message": f"Unexpected error: {str(e)}",
                "username": f"@{username}",
                "available": None
            }
    
    return {
        "error": True,
        "message": "Max retries exceeded",
        "username": f"@{username}",
        "available": None
    }

# ==================== API ENDPOINTS ====================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with HTML landing page"""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Fragment Username Checker API</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 20px;
                min-height: 100vh;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }}
            
            header {{
                text-align: center;
                margin-bottom: 40px;
                padding-bottom: 20px;
                border-bottom: 2px solid #f0f0f0;
            }}
            
            h1 {{
                color: #333;
                font-size: 2.5em;
                margin-bottom: 10px;
            }}
            
            .tagline {{
                color: #666;
                font-size: 1.2em;
                margin-bottom: 30px;
            }}
            
            .cards {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            
            .card {{
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                border: 1px solid #e0e0e0;
            }}
            
            .card h3 {{
                color: #667eea;
                margin-top: 0;
            }}
            
            .endpoint {{
                background: #e8f4ff;
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
                font-family: monospace;
                border-left: 3px solid #667eea;
            }}
            
            .btn {{
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 5px;
                margin: 5px;
                font-weight: bold;
            }}
            
            .btn:hover {{
                background: #5a6fd8;
            }}
            
            .response-example {{
                background: #2d2d2d;
                color: #f8f9fa;
                padding: 20px;
                border-radius: 5px;
                font-family: monospace;
                overflow-x: auto;
            }}
            
            footer {{
                text-align: center;
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #f0f0f0;
                color: #666;
            }}
            
            @media (max-width: 768px) {{
                .container {{
                    padding: 20px;
                }}
                
                h1 {{
                    font-size: 1.8em;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Fragment Username Checker API</h1>
                <p class="tagline">Check Telegram username availability on Fragment.com</p>
                <div>
                    <a href="/docs" class="btn">API Documentation</a>
                    <a href="/username?username=test" class="btn">Test API</a>
                    <a href="/health" class="btn">Health Check</a>
                </div>
            </header>
            
            <section>
                <h2>API Endpoints</h2>
                <div class="cards">
                    <div class="card">
                        <h3>Check Username</h3>
                        <div class="endpoint">GET /username?username=your_username</div>
                        <div class="endpoint">POST /username {{"username": "your_username"}}</div>
                    </div>
                    
                    <div class="card">
                        <h3>Health Check</h3>
                        <div class="endpoint">GET /health</div>
                    </div>
                    
                    <div class="card">
                        <h3>Documentation</h3>
                        <div class="endpoint">GET /docs (Swagger UI)</div>
                        <div class="endpoint">GET /redoc (ReDoc)</div>
                    </div>
                </div>
            </section>
            
            <section>
                <h2>Quick Examples</h2>
                <h3>Using curl:</h3>
                <div class="endpoint">curl "https://YOUR_APP.vercel.app/username?username=obito"</div>
                
                <h3>Using Python:</h3>
                <div class="response-example">
import requests<br>
response = requests.get(<br>
    "https://YOUR_APP.vercel.app/username",<br>
    params={{"username": "obito"}}<br>
)<br>
print(response.json())
                </div>
            </section>
            
            <section>
                <h2>Example Response</h2>
                <div class="response-example">
{{
  "username": "@obito",
  "price": "10,000 TON",
  "status": "Unavailable",
  "available": false,
  "message": "❌ Not available on Fragment",
  "developer": "@Aotpy",
  "channel": "@obitoapi / @obitostuffs",
  "timestamp": "2024-01-15T10:30:00.000Z"
}}
                </div>
            </section>
            
            <footer>
                <p><strong>Developer:</strong> {DEVELOPER}</p>
                <p><strong>Channel:</strong> {CHANNEL}</p>
                <p><strong>Version:</strong> 2.0.0</p>
            </footer>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        message="API is running normally",
        timestamp=datetime.datetime.now().isoformat()
    )

@app.get("/username", response_model=UsernameResponse)
async def check_username(
    username: str = Query(
        ...,
        min_length=1,
        max_length=32,
        description="Telegram username to check (without @ symbol)",
        example="obito"
    )
):
    """
    Check if a Telegram username is available on Fragment.com
    
    - **username**: The Telegram username to check (1-32 characters)
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
            detail="Invalid username format. Use only letters, numbers, and underscores (1-32 characters)."
        )
    
    # Check username on Fragment
    result = check_username_fragment(username)
    
    if result.get("error", False):
        raise HTTPException(
            status_code=500,
            detail=result.get("message", "Failed to check username")
        )
    
    # Add timestamp and developer info
    result["timestamp"] = datetime.datetime.now().isoformat()
    result["developer"] = DEVELOPER
    result["channel"] = CHANNEL
    
    return result

@app.post("/username", response_model=UsernameResponse)
async def check_username_post(request: UsernameRequest):
    """
    Check username availability using POST method
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
            detail="Invalid username format. Use only letters, numbers, and underscores (1-32 characters)."
        )
    
    # Check username on Fragment
    result = check_username_fragment(username)
    
    if result.get("error", False):
        raise HTTPException(
            status_code=500,
            detail=result.get("message", "Failed to check username")
        )
    
    # Add timestamp and developer info
    result["timestamp"] = datetime.datetime.now().isoformat()
    result["developer"] = DEVELOPER
    result["channel"] = CHANNEL
    
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
    """
    # Parse and clean usernames
    username_list = [u.strip().lower().replace('@', '') for u in usernames.split(',')]
    username_list = [u for u in username_list if u and re.match(r'^[a-zA-Z0-9_]{1,32}$', u)]
    
    if not username_list:
        raise HTTPException(
            status_code=400,
            detail="No valid usernames provided"
        )
    
    if len(username_list) > 5:
        raise HTTPException(
            status_code=400,
            detail="Maximum 5 usernames allowed per batch request"
        )
    
    # Check each username
    results = []
    for username in username_list:
        result = check_username_fragment(username)
        result["timestamp"] = datetime.datetime.now().isoformat()
        results.append(result)
    
    return {
        "count": len(results),
        "results": results,
        "developer": DEVELOPER,
        "channel": CHANNEL,
        "timestamp": datetime.datetime.now().isoformat()
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": True,
            "message": f"Endpoint {request.url.path} not found",
            "available_endpoints": ["/", "/docs", "/health", "/username", "/batch"],
            "developer": DEVELOPER,
            "channel": CHANNEL,
            "timestamp": datetime.datetime.now().isoformat()
        }
    )

@app.exception_handler(500)
async def server_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error occurred",
            "developer": DEVELOPER,
            "channel": CHANNEL,
            "timestamp": datetime.datetime.now().isoformat()
        }
    )

# Vercel handler
def handler(request, context):
    """Vercel serverless function handler"""
    from mangum import Mangum
    asgi_handler = Mangum(app)
    return asgi_handler(request, context)
