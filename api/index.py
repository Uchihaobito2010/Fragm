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

# ================== FRAGMENT HASH API ==================
def get_fragment_api():
    try:
        r = session.get("https://fragment.com", timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for script in soup.find_all("script"):
            if script.string and "apiUrl" in script.string:
                m = re.search(r"hash=([a-fA-F0-9]+)", script.string)
                if m:
                    return f"https://fragment.com/api?hash={m.group(1)}"
    except:
        pass
    return None

def fragment_price(username: str):
    api = get_fragment_api()
    if not api:
        return None

    payload = {
        "type": "usernames",
        "query": username,
        "method": "searchAuctions"
    }

    try:
        r = session.post(api, data=payload, timeout=10).json()
        html = r.get("html")
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        values = soup.find_all("div", class_="tm-value")
        if len(values) < 2:
            return None

        return values[1].get_text(strip=True)
    except:
        return None

# ================== FRAGMENT PAGE CHECK (UPGRADED) ==================

def fragment_page(username: str):
    url = f"https://fragment.com/username/{username}"
    try:
        r = session.get(url, timeout=15)
        if r.status_code != 200:
            return False, None

        html = r.text.lower()

        # 🔴 DEFINITE SOLD (ONLY THIS)
        if "purchased on" in html:
            return True, "Sold"

        # 🟢 BUYABLE / AUCTION
        if "buy username" in html or "place a bid" in html:
            return True, "Available"

    except:
        pass

    return False, None

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

    # 1️⃣ Fragment page (SOURCE OF TRUTH)
    on_fragment, frag_status = fragment_page(username)
    if on_fragment:
        price = fragment_price(username)
        return {
            "username": f"@{username}",
            "status": frag_status,          # Sold / Available
            "on_fragment": True,
            "price_ton": price or "Unknown",
            "can_claim": False,
            "message": (
                "Buy from Fragment"
                if frag_status == "Available"
                else "Already sold on Fragment"
            ),
            "fragment_url": f"https://fragment.com/username/{username}",
            "api_owner": OWNER,
            "contact": CONTACT,
        }

    # 2️⃣ Telegram check (fallback)
    if is_telegram_taken(username):
        return {
            "username": f"@{username}",
            "status": "Sold",
            "on_fragment": False,
            "price_ton": "Unknown",
            "can_claim": False,
            "message": "Username already owned",
            "api_owner": OWNER,
            "contact": CONTACT,
        }

    # 3️⃣ Claimable
    return {
        "username": f"@{username}",
        "status": "Available",
        "on_fragment": False,
        "price_ton": "Unknown",
        "can_claim": True,
        "message": "Can be claimed directly",
        "api_owner": OWNER,
        "contact": CONTACT,
    }

# ================== REQUIRED FOR VERCEL ==================
app = app
