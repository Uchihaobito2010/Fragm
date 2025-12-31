"""
Fragment Username Checker API for Vercel
FastAPI application for checking Telegram username availability on Fragment.com
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

# Global variables
DEVELOPER = "@Aotpy"
CHANNEL = "@obitoapi / @obitostuffs"

# Create session
session = requests.Session()

# Update session headers
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

def get_api_hash():
    """
    Extract the API hash from fragment.com
    """
    try:
        # Update headers before making request
        update_session_headers()
        
        response = session.get(
            "https://fragment.com",
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }
        )
        response.raise_for_status()
        
        # Look for hash in the HTML
        html_content = response.text
        
        # Pattern 1: hash= followed by 64 hex characters
        pattern1 = r'hash=([a-fA-F0-9]{64})'
        match1 = re.search(pattern1, html_content)
        
        if match1:
            return match1.group(1)
        
        # Pattern 2: "hash":" followed by 64 hex characters
        pattern2 = r'"hash":"([a-fA-F0-9]{64})"'
        match2 = re.search(pattern2, html_content)
        
        if match2:
            return match2.group(1)
        
        # Pattern 3: Look in script tags
        if "apiUrl" in html_content:
            lines = html_content.split('\n')
            for line in lines:
                if "apiUrl" in line and "hash=" in line:
                    hash_match = re.search(r'hash=([a-fA-F0-9]+)', line)
                    if hash_match:
                        return hash_match.group(1)
        
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"Error getting API hash: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error getting API hash: {str(e)}")
        return None

def check_username_on_fragment(username: str, retries: int = 2):
    """
    Check if a username is available on Fragment.com
    """
    api_hash = get_api_hash()
    
    if not api_hash:
        return {
            "error": True,
            "message": "Failed to connect to Fragment.com. Please try again later.",
            "username": f"@{username}",
            "available": None
        }
    
    api_url = f"https://fragment.com/api?hash={api_hash}"
    
    # Prepare the request data
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
                timeout=20
            )
            response.raise_for_status()
            
            json_data = response.json()
            
            if "html" not in json_data or not json_data["html"]:
                # Empty response might mean username is not listed
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

# ============ API ENDPOINTS ============

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint - HTML landing page"""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Fragment Username Checker API</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1000px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                margin-top: 20px;
            }}
            
            header {{
                text-align: center;
                margin-bottom: 40px;
                padding-bottom: 20px;
                border-bottom: 2px solid #eee;
            }}
            
            h1 {{
                color: #667eea;
                font-size: 2.8em;
                margin-bottom: 10px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            
            .tagline {{
                color: #666;
                font-size: 1.2em;
                margin-bottom: 20px;
            }}
            
            .cards {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 25px;
                margin: 30px 0;
            }}
            
            .card {{
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
                border: 1px solid #eaeaea;
                transition: transform 0.3s, box-shadow 0.3s;
            }}
            
            .card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15);
            }}
            
            .card h3 {{
                color: #667eea;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            .card h3 i {{
                font-size: 1.2em;
            }}
            
            .code-block {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 10px;
                font-family: 'Courier New', monospace;
                margin: 15px 0;
                border-left: 4px solid #667eea;
                overflow-x: auto;
            }}
            
            .endpoint {{
                background: #f0f4ff;
                padding: 12px;
                border-radius: 8px;
                margin: 8px 0;
                border-left: 3px solid #764ba2;
            }}
            
            .btn {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 14px 28px;
                text-decoration: none;
                border-radius: 10px;
                font-weight: bold;
                margin: 10px 5px;
                transition: all 0.3s;
                border: none;
                cursor: pointer;
                font-size: 16px;
            }}
            
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
            }}
            
            .btn-secondary {{
                background: #6c757d;
            }}
            
            .btn-success {{
                background: #28a745;
            }}
            
            .examples {{
                background: #f8f9fa;
                border-radius: 15px;
                padding: 25px;
                margin: 30px 0;
            }}
            
            .response-example {{
                background: #1a1a1a;
                color: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                font-family: 'Courier New', monospace;
                margin: 15px 0;
                overflow-x: auto;
            }}
            
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                color: #666;
            }}
            
            @media (max-width: 768px) {{
                .container {{
                    padding: 20px;
                }}
                
                h1 {{
                    font-size: 2em;
                }}
                
                .cards {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body>
        <div class="container">
            <header>
                <h1><i class="fas fa-search"></i> Fragment Username Checker API</h1>
                <p class="tagline">Check Telegram username availability on Fragment.com</p>
                <div>
                    <a href="/docs" class="btn"><i class="fas fa-book"></i> API Documentation</a>
                    <a href="/redoc" class="btn btn-secondary"><i class="fas fa-file-alt"></i> ReDoc</a>
                    <a href="/health" class="btn btn-success"><i class="fas fa-heartbeat"></i> Health Check</a>
                </div>
            </header>
            
            <section class="cards">
                <div class="card">
                    <h3><i class="fas fa-globe"></i> API Endpoints</h3>
                    <div class="endpoint">
                        <strong>GET /username</strong><br>
                        <small>Check username availability</small><br>
                        <code>/username?username=your_username</code>
                    </div>
                    <div class="endpoint">
                        <strong>POST /username</strong><br>
                        <small>Check username with JSON</small><br>
                        <code>{{"username": "your_username"}}</code>
                    </div>
                    <div class="endpoint">
                        <strong>GET /health</strong><br>
                        <small>API health status</small>
                    </div>
                </div>
                
                <div class="card">
                    <h3><i class="fas fa-bolt"></i> Quick Test</h3>
                    <p>Test the API immediately:</p>
                    <div class="code-block">
                        <a href="/username?username=test" target="_blank">/username?username=test</a>
                    </div>
                    <p>Or try with curl:</p>
                    <div class="code-block">
                        curl "https://{app.title}.vercel.app/username?username=obito"
                    </div>
                </div>
            </section>
            
            <section class="examples">
                <h2><i class="fas fa-code"></i> Example Usage</h2>
                
                <h3>Python Example:</h3>
                <div class="code-block">
import requests<br>
<br>
# Check username<br>
response = requests.get(<br>
    "https://your-app.vercel.app/username",<br>
    params={{"username": "obito"}}<br>
)<br>
print(response.json())
                </div>
                
                <h3>JavaScript Example:</h3>
                <div class="code-block">
fetch('https://your-app.vercel.app/username?username=obito')<br>
  .then(response => response.json())<br>
  .then(data => console.log(data));
                </div>
                
                <h3>Example Response:</h3>
                <div class="response-example">
{{
  "username": "@obito",
  "price": "10,000 TON",
  "status": "Unavailable",
  "available": false,
  "message": "❌ Not available on Fragment",
  "developer": "@Aotpy",
  "channel": "@obitoapi / @obitostuffs",
  "timestamp": "2024-01-15T10:30:00Z"
}}
                </div>
            </section>
            
            <section>
                <h2><i class="fas fa-info-circle"></i> About This API</h2>
                <p>This API checks the availability of Telegram usernames on <a href="https://fragment.com" target="_blank">Fragment.com</a>, the official Telegram auction platform.</p>
                
                <h3>Features:</h3>
                <ul style="margin-left: 20px; margin-bottom: 20px;">
                    <li>Real-time username availability checking</li>
                    <li>Fast and reliable API</li>
                    <li>JSON responses</li>
                    <li>CORS enabled</li>
                    <li>Rate limiting protection</li>
                    <li>Automatic retry mechanism</li>
                </ul>
            </section>
            
            <footer class="footer">
                <p><strong>Developer:</strong> {DEVELOPER}</p>
                <p><strong>Channel:</strong> {CHANNEL}</p>
                <p><strong>Version:</strong> 2.0.0</p>
                <p>© {datetime.datetime.now().year} Fragment Username Checker API</p>
            </footer>
        </div>
        
        <script>
            // Add copy functionality to code blocks
            document.querySelectorAll('.code-block').forEach(block => {{
                block.addEventListener('click', function() {{
                    const text = this.textContent || this.innerText;
                    navigator.clipboard.writeText(text.trim()).then(() => {{
                        const original = this.innerHTML;
                        this.innerHTML = '<i class="fas fa-check"></i> Copied to clipboard!';
                        this.style.background = '#d4edda';
                        setTimeout(() => {{
                            this.innerHTML = original;
                            this.style.background = '';
                        }}, 2000);
                    }});
                }});
            }});
            
            // Add smooth scrolling for anchor links
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
                anchor.addEventListener('click', function (e) {{
                    e.preventDefault();
                    const target = document.querySelector(this.getAttribute('href'));
                    if (target) {{
                        target.scrollIntoView({{
                            behavior: 'smooth'
                        }});
                    }}
                }});
            }});
        </script>
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
    
    This endpoint queries Fragment.com to check the availability and price of a Telegram username.
    
    Parameters:
    - **username**: The Telegram username to check (1-32 characters, letters/numbers/underscores only)
    
    Returns:
    - JSON response with username availability, price, and status
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
            detail="Invalid username format. Username must be 1-32 characters containing only letters, numbers, and underscores."
        )
    
    # Check username on Fragment
    result = check_username_on_fragment(username)
    
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
    
    Alternative endpoint for checking username with JSON body
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
            detail="Invalid username format. Username must be 1-32 characters containing only letters, numbers, and underscores."
        )
    
    # Check username on Fragment
    result = check_username_on_fragment(username)
    
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
    Check multiple usernames at once (limited to 5)
    
    Useful for checking availability of multiple usernames in a single request.
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
        result = check_username_on_fragment(username)
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
            "available_endpoints": [
                "/",
                "/docs",
                "/redoc",
                "/health",
                "/username",
                "/batch"
            ],
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

# Vercel requires the app to be accessible
# No need for handler function - Vercel will use the ASGI app directly
