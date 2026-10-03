import requests
import random
import string
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# ==================== CONFIG ====================
WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK_HERE" 

WORKERS = 8

BATCH_DELAY = 1.5

CHARS = string.ascii_lowercase + string.digits + "_"

# =================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

session = requests.Session()
session.headers.update(HEADERS)

found = set()
checked = 0

def generate_name() -> str:
    """Generate a random valid 4-character Minecraft username."""
    return "".join(random.choices(CHARS, k=4))

def is_available(name: str) -> bool:
    """
    Check if username is currently free.
    Mojang returns 200 + JSON if taken, 404/204 if no profile exists.
    """
    url = f"https://api.mojang.com/users/profiles/minecraft/{name}"
    try:
        r = session.get(url, timeout=8)
        if r.status_code == 200:
            return False  
        if r.status_code in (204, 404):
            return True
        if r.status_code == 429:
            print(f"[!] Rate limited on {name} — backing off")
            time.sleep(5)
            return False
        return False
    except Exception as e:
        print(f"[!] Request error on {name}: {e}")
        return False

def send_webhook(name: str):
    """Send clean embed to Discord when a name is found."""
    if not WEBHOOK_URL or "YOUR_DISCORD_WEBHOOK" in WEBHOOK_URL:
        print(f"[!] Webhook not set — found: {name}")
        return

    embed = {
        "title": "4-Char Name Available",
        "description": f"**`{name}`** is currently free",
        "color": 0x00FF00,
        "fields": [
            {"name": "Name", "value": f"`{name}`", "inline": True},
            {"name": "Length", "value": "4", "inline": True},
            {"name": "Time", "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), "inline": False},
        ],
        "footer": {"text": "Phantom Name Finder"},
    }

    payload = {"embeds": [embed]}
    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if r.status_code in (200, 204):
            print(f"[+] Webhook sent for {name}")
        else:
            print(f"[!] Webhook failed ({r.status_code}): {r.text[:120]}")
    except Exception as e:
        print(f"[!] Webhook error: {e}")

def check_one(name: str):
    global checked
    checked += 1
    if is_available(name):
        if name not in found:
            found.add(name)
            print(f"\n[HIT] {name} is AVAILABLE")
            send_webhook(name)
            with open("available_names.txt", "a") as f:
                f.write(f"{name}\n")
    if checked % 50 == 0:
        print(f"[*] Checked {checked} | Hits: {len(found)}")

def main():
    print("=" * 50)
    print("  Phantom 4-Char Minecraft Name Finder")
    print("=" * 50)
    print(f"Workers : {WORKERS}")
    print(f"Chars   : {CHARS}")
    print("Press Ctrl+C to stop\n")

    if "YOUR_DISCORD_WEBHOOK" in WEBHOOK_URL:
        print("[!] WARNING: Set your WEBHOOK_URL at the top of the file\n")

    try:
        while True:
            batch = set()
            while len(batch) < WORKERS * 4:
                batch.add(generate_name())

            with ThreadPoolExecutor(max_workers=WORKERS) as executor:
                futures = [executor.submit(check_one, name) for name in batch]
                for _ in as_completed(futures):
                    pass

            time.sleep(BATCH_DELAY)

    except KeyboardInterrupt:
        print(f"\n\nStopped. Checked: {checked} | Found: {len(found)}")
        if found:
            print("Hits:", ", ".join(sorted(found)))

if __name__ == "__main__":
    main()
