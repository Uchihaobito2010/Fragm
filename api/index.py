import re
import time
import requests
from bs4 import BeautifulSoup
from user_agent import generate_user_agent
from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="Fragment Username Checker API")

session = requests.Session()
session.headers.update({"User-Agent": generate_user_agent()})

DEVELOPER = "ankucode"
CHANNEL = "trybyte || @AnkuCode"

# ================== FRAGMENT API URL ==================
def frag_api():
    try:
        r = session.get("https://fragment.com", timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for script in soup.find_all("script"):
            if script.string and "apiUrl" in script.string:
                match = re.search(r'hash=([a-fA-F0-9]+)', script.string)
                if match:
                    return f"https://fragment.com/api?hash={match.group(1)}"
    except:
        pass
    return None

# ================== FRAGMENT SOLD CHECK ==================
def fragment_sold(username: str) -> bool:
    try:
        r = session.get(f"https://fragment.com/username/{username}", timeout=10)
        return "purchased on" in r.text.lower()
    except:
        return False

# ================== FRAGMENT CHECK ==================
def check_fgusername(username: str, retries=2):
    api_url = frag_api()
    if not api_url:
        return {"error": "Fragment API not reachable"}

    payload = {
        "type": "usernames",
        "query": username,
        "method": "search"  # ✅ IMPORTANT FIX
    }

    try:
        response = session.post(api_url, data=payload, timeout=10).json()
    except:
        if retries > 0:
            time.sleep(1)
            return check_fgusername(username, retries - 1)
        return {"error": "Fragment API request failed"}

    html = response.get("html")
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    values = soup.find_all("div", class_="tm-value")

    if len(values) < 2:
        return None

    tag = values[0].get_text(strip=True)
    price = values[1].get_text(strip=True)

    return {
        "username": tag,
        "price": price
    }

# ================== TELEGRAM CHECK ==================
def telegram_taken(username: str) -> bool:
    try:
        r = session.get(f"https://t.me/{username}", timeout=8)
        return r.status_code == 200
    except:
        return False

# ================== ENDPOINT ==================
@app.get("/username")
async def check_username(username: str = Query(..., min_length=1)):
    username = username.strip().replace("@", "").lower()

    # 1️⃣ SOLD (Fragment ownership)
    if fragment_sold(username):
        return {
            "username": f"@{username}",
            "status": "Sold",
            "on_fragment": True,
            "price": "Unknown",
            "can_claim": False,
            "developer": DEVELOPER,
            "channel": CHANNEL
        }

    # 2️⃣ AVAILABLE (Fragment listing)
    frag_data = check_fgusername(username)
    if frag_data:
        return {
            "username": frag_data["username"],
            "status": "Available",
            "on_fragment": True,
            "price": frag_data["price"],
            "can_claim": False,
            "message": "Buy from Fragment",
            "developer": DEVELOPER,
            "channel": CHANNEL
        }

    # 3️⃣ TAKEN (Telegram, never fragment)
    if telegram_taken(username):
        return {
            "username": f"@{username}",
            "status": "Taken",
            "on_fragment": False,
            "price": "Unknown",
            "can_claim": False,
            "developer": DEVELOPER,
            "channel": CHANNEL
        }

    # 4️⃣ FREE
    return {
        "username": f"@{username}",
        "status": "Free",
        "on_fragment": False,
        "price": "Unknown",
        "can_claim": True,
        "message": "Can be claimed directly",
        "developer": DEVELOPER,
        "channel": CHANNEL
    }
