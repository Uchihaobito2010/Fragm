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

def get_fragment_api_hash():
    """
    Extract the API hash from fragment.com
    """
    try:
        update_session_headers()
        
        response = session.get(
            "https://fragment.com",
            timeout=10
        )
        response.raise_for_status()
        
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
        
    except Exception as e:
        print(f"Error getting API hash: {str(e)}")
        return None

def check_username_fragment(username: str, retries: int = 2):
    """
    Check username availability on Fragment.com
    """
    api_hash = get_fragment_api_hash()
    
    if not api_hash:
        return {
            "error": True,
            "message": "Unable to connect to Fragment.com",
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
        "Referer": "https://fragment.com/"
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
                return {
                    "error": False,
                    "username": f"@{username}",
                    "status": "Not Listed",
                    "available": True,
                    "price": "N/A",
                    "message": "✅ Username is not listed on Fragment"
                }
            
            # Parse the HTML response
            soup = BeautifulSoup(json_data["html"], 'html.parser')
            
            # Find all tm-value divs
            tm_values = soup.find_all("div", class_="tm-value")
            
            if not tm_values or len(tm_values) < 3:
                return {
                    "error": False,
                    "username": f"@{username}",
                    "status": "Not Found",
                    "available": True,
                    "price": "N/A",
                    "message": "✅ Username not found on Fragment"
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
                "message": "✅ Available" if available else "❌ Not available"
            }
            
        except requests.exceptions.Timeout:
            if attempt < retries:
                time.sleep(1)
                continue
            return {
                "error": True,
                "message": "Request timeout",
                "username": f"@{username}",
                "available": None
            }
        except Exception as e:
            if attempt < retries:
                time.sleep(1)
                continue
            return {
                "error": True,
                "message": f"Error: {str(e)}",
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

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Fragment Username Checker API",
        "version": "2.0.0",
        "endpoints": {
            "check_username": "/username?username=YOUR_USERNAME",
            "health": "/health",
            "docs": "/docs"
        },
        "developer": DEVELOPER,
        "channel": CHANNEL
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "API is running",
        "developer": DEVELOPER,
        "channel": CHANNEL,
        "timestamp": datetime.datetime.now().isoformat(),
        "version": "2.0.0"
    }

@app.get("/username")
async def check_username(
    username: str = Query(..., min_length=1, max_length=32)
):
    """
    Check if a Telegram username is available on Fragment.com
    """
    username = username.strip().lower().replace('@', '')
    
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    
    if not re.match(r'^[a-zA-Z0-9_]{1,32}$', username):
        raise HTTPException(
            status_code=400,
            detail="Invalid username format. Use only letters, numbers, and underscores."
        )
    
    result = check_username_fragment(username)
    
    if result.get("error", False):
        raise HTTPException(
            status_code=500,
            detail=result.get("message", "Failed to check username")
        )
    
    result["timestamp"] = datetime.datetime.now().isoformat()
    result["developer"] = DEVELOPER
    result["channel"] = CHANNEL
    
    return result

@app.post("/username")
async def check_username_post(request: UsernameRequest):
    """
    Check username availability using POST method
    """
    username = request.username.strip().lower().replace('@', '')
    
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    
    if not re.match(r'^[a-zA-Z0-9_]{1,32}$', username):
        raise HTTPException(
            status_code=400,
            detail="Invalid username format. Use only letters, numbers, and underscores."
        )
    
    result = check_username_fragment(username)
    
    if result.get("error", False):
        raise HTTPException(
            status_code=500,
            detail=result.get("message", "Failed to check username")
        )
    
    result["timestamp"] = datetime.datetime.now().isoformat()
    result["developer"] = DEVELOPER
    result["channel"] = CHANNEL
    
    return result

@app.get("/batch")
async def check_batch_usernames(
    usernames: str = Query(..., description="Comma-separated list of usernames")
):
    """
    Check multiple usernames at once
    """
    username_list = [u.strip().lower().replace('@', '') for u in usernames.split(',')]
    username_list = [u for u in username_list if u and re.match(r'^[a-zA-Z0-9_]{1,32}$', u)]
    
    if not username_list:
        raise HTTPException(status_code=400, detail="No valid usernames provided")
    
    if len(username_list) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 usernames allowed")
    
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

# Vercel requires this handler
async def handler(request, response):
    """Vercel serverless function handler"""
    return app
