import re
import time
import requests
from bs4 import BeautifulSoup
from user_agent import generate_user_agent
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Fragment Username Checker API")

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

DEVELOPER = "Paras Chourasiya / @Aotpy"
CHANNEL = "t.me/obitostuffs"
PORTFOLIO = "https://aotpy.vercel.app/"

def frag_api():
    try:
        r = session.get("https://fragment.com")
        soup = BeautifulSoup(r.text, 'html.parser')
        for script in soup.find_all("script"):
            if script.string and "apiUrl" in script.string:
                match = re.search(r'hash=([a-fA-F0-9]+)', script.string)
                if match:
                    return f"https://fragment.com/api?hash={match.group(1)}"
        return None
    except Exception:
        return None

def check_fgusername(username: str, retries=3):
    api_url = frag_api()
    if not api_url:
        return {"error": f"Could not get API URL for @{username}"}

    data = {"type": "usernames", "query": username, "method": "searchAuctions"}
    try:
        response = session.post(api_url, data=data).json()
    except Exception:
        if retries > 0:
            time.sleep(2)
            return check_fgusername(username, retries - 1)
        return {"error": "API request failed"}

    html_data = response.get("html")
    if not html_data and retries > 0:
        time.sleep(2)
        return check_fgusername(username, retries - 1)
    elif not html_data:
        return {"error": "No HTML returned from Fragment API"}

    soup = BeautifulSoup(html_data, 'html.parser')
    elements = soup.find_all("div", class_="tm-value")
    if len(elements) < 3:
        return {"error": "Not enough info in response"}

    tag = elements[0].get_text(strip=True)
    price = elements[1].get_text(strip=True)
    status = elements[2].get_text(strip=True)

    available = status.lower() == "unavailable"
    
    # Determine status text
    status_text = "Available" if not available else "Not available"
    
    # Determine if on fragment
    on_fragment = "Yes" if not available else "No"
    
    # Can claim logic
    can_claim = "Yes" if available else "No"

    return {
        "developer": DEVELOPER,
        "username": tag,
        "status": status_text,
        "price": price,
        "on_fragment": on_fragment,
        "can_claim": can_claim
    }

@app.get("/")
async def root():
    return {
        "message": "Fragment Username Checker API",
        "developer": DEVELOPER,
        "channel": CHANNEL,
        "portfolio": PORTFOLIO,
        "endpoint": "GET /tobi?username=your_username",
        "example": "https://your-app.vercel.app/tobi?username=example"
    }

@app.get("/tobi")
async def check_username(username: str = Query(..., min_length=1)):
    username = username.strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="username is required")
    result = check_fgusername(username)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.exception_handler(404)
async def not_found(request: Request, exc: Exception):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found", "available_endpoints": ["/", "/tobi?username=xxx", "/api/health"]}
    )

# This is required for Vercel to run the app
app = app
