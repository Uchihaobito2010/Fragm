import re
import time
import requests
from bs4 import BeautifulSoup
from user_agent import generate_user_agent
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Fragment Username Checker API",
    description="Check Telegram username availability on Fragment.com",
    version="1.0.0",
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

session = requests.Session()
session.headers.update({"User-Agent": generate_user_agent()})

DEVELOPER = "@Aotpy"
CHANNEL = "@obitoapi / @obitostuffs"

# Pydantic model for input validation
class UsernameRequest(BaseModel):
    username: str

class HealthResponse(BaseModel):
    status: str
    developer: str
    channel: str
    timestamp: str

def frag_api():
    """
    Get the dynamic API URL from Fragment.com
    """
    try:
        r = session.get("https://fragment.com", timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        for script in soup.find_all("script"):
            if script.string and "apiUrl" in script.string:
                match = re.search(r'hash=([a-fA-F0-9]+)', script.string)
                if match:
                    return f"https://fragment.com/api?hash={match.group(1)}"
        return None
    except Exception as e:
        print(f"Error getting fragment API: {e}")
        return None

def check_fgusername(username: str, retries=3):
    """
    Check username availability on Fragment.com
    """
    api_url = frag_api()
    if not api_url:
        return {"error": f"Could not get API URL for @{username}"}

    data = {"type": "usernames", "query": username, "method": "searchAuctions"}
    
    try:
        response = session.post(api_url, data=data, timeout=10)
        response.raise_for_status()
        json_data = response.json()
    except Exception as e:
        print(f"API request error: {e}")
        if retries > 0:
            time.sleep(2)
            return check_fgusername(username, retries - 1)
        return {"error": "API request failed"}

    html_data = json_data.get("html")
    if not html_data:
        if retries > 0:
            time.sleep(2)
            return check_fgusername(username, retries - 1)
        return {"error": "No HTML returned from Fragment API"}

    soup = BeautifulSoup(html_data, 'html.parser')
    elements = soup.find_all("div", class_="tm-value")
    
    if len(elements) < 3:
        return {
            "username": username,
            "status": "Not Found",
            "available": True,
            "message": "✅ This username might be free or not listed on Fragment",
            "developer": DEVELOPER,
            "channel": CHANNEL
        }

    tag = elements[0].get_text(strip=True)
    price = elements[1].get_text(strip=True)
    status = elements[2].get_text(strip=True)

    available = status.lower() == "unavailable"
    message = "✅ This username might be free or not listed on Fragment" if available else ""

    return {
        "username": tag,
        "price": price,
        "status": status,
        "available": available,
        "message": message,
        "developer": DEVELOPER,
        "channel": CHANNEL
    }

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Fragment Username Checker API",
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
    return HealthResponse(
        status="healthy",
        developer=DEVELOPER,
        channel=CHANNEL,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    )

@app.get("/username")
async def check_username(username: str = Query(..., min_length=1, description="Telegram username to check")):
    """
    Check if a Telegram username is available on Fragment.com
    
    - **username**: The Telegram username (without @)
    """
    username = username.strip().lower().replace('@', '')
    
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    
    if len(username) > 32:
        raise HTTPException(status_code=400, detail="Username too long (max 32 characters)")
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        raise HTTPException(status_code=400, detail="Invalid username format (only letters, numbers, and underscore)")
    
    result = check_fgusername(username)
    
    if "error" in result:
        raise HTTPException(
            status_code=500,
            detail=result["error"]
        )
    
    return result

@app.post("/username")
async def check_username_post(request: UsernameRequest):
    """
    Check username availability (POST method)
    """
    username = request.username.strip().lower().replace('@', '')
    
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    
    result = check_fgusername(username)
    
    if "error" in result:
        raise HTTPException(
            status_code=500,
            detail=result["error"]
        )
    
    return result

# Handler for Vercel (needs to be at module level)
handler = app
