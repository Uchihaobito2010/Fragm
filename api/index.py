import re
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from user_agent import generate_user_agent

app = FastAPI(title="Telegram Fragment Username API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OWNER = "Paras Chourasiya"
CONTACT = "t.me/Aotpy"

session = requests.Session()
session.headers.update({
    "User-Agent": generate_user_agent(),
    "Referer": "https://fragment.com/"
})

# ---------- Telegram page ----------
def telegram_exists(username: str) -> bool:
    try:
        r = session.get(f"https://t.me/{username}", timeout=8)
        return r.status_code == 200
    except:
        return False

# ---------- Fragment page ----------
def fragment_page_exists(username: str) -> bool:
    try:
        r = session.get(f"https://fragment.com/username/{username}", timeout=8)
        return r.status_code == 200
    except:
        return False

# ---------- Fragment SOLD ----------
def fragment_sold(username: str) -> bool:
    try:
        r = session.get(f"https://fragment.com/username/{username}", timeout=8)
        return "purchased on" in r.text.lower()
    except:
        return False

# ---------- Fragment API (ALL listings) ----------
def fragment_api_hit(username: str):
    try:
        r = session.get("https://fragment.com", timeout=8)
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
            "method": "search"   # IMPORTANT
        }

        data = session.post(api, data=payload, timeout=8).json()
        return data.get("html")

    except:
        return None

# ---------- Price ----------
def fragment_price(html: str):
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    values = soup.find_all("div", class_="tm-value")
    if len(values) >= 2:
        return values[1].get_text(strip=True)
    return None

# ---------- MAIN ----------
@app.get("/check")
def check(username: str = Query(...)):
    username = username.replace("@", "").lower().strip()
    if not username:
        raise HTTPException(status_code=400, detail="Invalid username")

    # 1️⃣ SOLD
    if fragment_sold(username):
        return {
            "username": f"@{username}",
            "status": "Sold",
            "on_fragment": True,
            "can_claim": False,
            "price_ton": "Unknown",
            "fragment_url": f"https://fragment.com/username/{username}",
            "api_owner": OWNER,
            "contact": CONTACT
        }

    # 2️⃣ AVAILABLE (Fragment API)
    frag_html = fragment_api_hit(username)
    if frag_html:
        return {
            "username": f"@{username}",
            "status": "Available",
            "on_fragment": True,
            "can_claim": False,
            "price_ton": fragment_price(frag_html) or "Unknown",
            "message": "Buy from Fragment",
            "fragment_url": f"https://fragment.com/username/{username}",
            "api_owner": OWNER,
            "contact": CONTACT
        }

    # 3️⃣ TAKEN (Fragment page OR Telegram page)
    if fragment_page_exists(username) or telegram_exists(username):
        return {
            "username": f"@{username}",
            "status": "Taken",
            "on_fragment": False,
            "can_claim": False,
            "price_ton": "Unknown",
            "api_owner": OWNER,
            "contact": CONTACT
        }

    # 4️⃣ FREE (VERY RARE)
    return {
        "username": f"@{username}",
        "status": "Free",
        "on_fragment": False,
        "can_claim": True,
        "price_ton": "Unknown",
        "message": "Can be claimed directly",
        "api_owner": OWNER,
        "contact": CONTACT
    }

app = app
