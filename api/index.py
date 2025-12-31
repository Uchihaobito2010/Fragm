import re
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from user_agent import generate_user_agent

# ================== APP ==================
app = FastAPI(title="Telegram Fragment Username API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================== META ==================
OWNER = "Paras Chourasiya"
CONTACT = "t.me/Aotpy"
PORTFOLIO = "https://aotpy.vercel.app"
CHANNEL = "@obitoapi / @obitostuffs"

# ================== SESSION ==================
session = requests.Session()
session.headers.update({
    "User-Agent": generate_user_agent(),
    "Referer": "https://fragment.com/"
})

# ================== TELEGRAM CHECK ==================
def is_telegram_taken(username: str) -> bool:
    try:
        r = session.get(f"https://t.me/{username}", timeout=10)
        return r.status_code == 200 and "tgme_page_title" in r.text
    except:
        return False

# ================== FRAGMENT STATUS ==================
def fragment_status(username: str):
    url = f"https://fragment.com/username/{username}"
    try:
        r = session.get(url, timeout=15)
        if r.status_code != 200:
            return None  # never fragment

        soup = BeautifulSoup(r.text, "html.parser")
        text = r.text.lower()

        # 🔴 SOLD (real sale happened)
        if "purchased on" in text:
            return "Sold"

        # 🟢 AVAILABLE ONLY IF REAL ACTION BUTTON EXISTS
        buy_btn = soup.find("button", string=lambda x: x and "buy username" in x.lower())
        bid_btn = soup.find("button", string=lambda x: x and "place a bid" in x.lower())

        if buy_btn or bid_btn:
            return "Available"

        # ❌ Page exists but NEVER listed / already owned
        return None

    except:
        return None

# ================== FRAGMENT PRICE ==================
def fragment_price(username: str):
    try:
        r = session.get("https://fragment.com", timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        api = None
        for s in soup.find_all("script"):
            if s.string and "apiUrl" in s.string:
                m = re.search(r"hash=([a-fA-F0-9]+)", s.string)
                if m:
                    api = f"https://fragment.com/api?hash={m.group(1)}"
                    break

        if not api:
            return None

        payload = {
            "type": "usernames",
            "query": username,
            "method": "searchAuctions"
        }

        r = session.post(api, data=payload, timeout=10).json()
        html = r.get("html")
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        values = soup.find_all("div", class_="tm-value")
        if len(values) >= 2:
            return values[1].get_text(strip=True)

    except:
        pass

    return None

# ================== ROOT ==================
@app.get("/")
def home():
    return {
        "api": "Telegram Fragment Username Check API",
        "usage": "/check?username=tobi",
        "status": "online",
        "owner": OWNER,
        "contact": CONTACT,
        "portfolio": PORTFOLIO,
        "channel": CHANNEL
    }

# ================== MAIN ENDPOINT ==================
@app.get("/check")
def check_username(username: str = Query(..., min_length=1)):
    username = username.replace("@", "").lower().strip()
    if not username:
        raise HTTPException(status_code=400, detail="username required")

    frag_state = fragment_status(username)

    # 1️⃣ Fragment SOLD
    if frag_state == "Sold":
        return {
            "username": f"@{username}",
            "status": "Sold",
            "on_fragment": True,
            "price_ton": fragment_price(username) or "Unknown",
            "can_claim": False,
            "fragment_url": f"https://fragment.com/username/{username}",
            "api_owner": OWNER,
            "contact": CONTACT
        }

    # 2️⃣ Fragment AVAILABLE
    if frag_state == "Available":
        return {
            "username": f"@{username}",
            "status": "Available",
            "on_fragment": True,
            "price_ton": fragment_price(username) or "Unknown",
            "can_claim": False,
            "message": "Buy from Fragment",
            "fragment_url": f"https://fragment.com/username/{username}",
            "api_owner": OWNER,
            "contact": CONTACT
        }

    # 3️⃣ Telegram TAKEN (never fragment)
    if is_telegram_taken(username):
        return {
            "username": f"@{username}",
            "status": "Taken",
            "on_fragment": False,
            "price_ton": "Unknown",
            "can_claim": False,
            "api_owner": OWNER,
            "contact": CONTACT
        }

    # 4️⃣ FREE
    return {
        "username": f"@{username}",
        "status": "Free",
        "on_fragment": False,
        "price_ton": "Unknown",
        "can_claim": True,
        "message": "Can be claimed directly",
        "api_owner": OWNER,
        "contact": CONTACT
    }

# ================== VERCEL ==================
app = app
