import os
import requests
from camoufox.sync_api import Camoufox

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
TARGET_URL = "https://kinepolis.be/fr/films/dune-part-three/HO00013472/"
TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"

def send_alert(message):
    if not DISCORD_WEBHOOK_URL:
        print("Error: DISCORD_WEBHOOK secret is missing!")
        return
    data = {"content": f"@everyone 🚨 **DUNE 3 CLOUD ALERT** 🚨\n{message}"}
    requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=10)

def run_check():
    print("1. Attempting direct connection with Camoufox anti-detect browser...")
    page_title = "Unknown"
    body_text = ""

    try:
        with Camoufox(headless=True, humanize=True) as browser:
            page = browser.new_page()
            page.goto(TARGET_URL, timeout=45000)
            page.wait_for_timeout(8000)
            page_title = page.title()
            body_text = page.inner_text("body")
            print(f"Camoufox Page Title: '{page_title}'")
    except Exception as e:
        print(f"Camoufox error: {e}")

    # If Kinepolis hard-blocks the entire GitHub Azure IP subnet (403), use Jina Reader fallback
    if "403" in page_title or "Blocked" in page_title or "Just a moment" in page_title or not body_text:
        print("2. Azure IP was 403 blocked. Trying Jina Reader proxy fallback...")
        try:
            r = requests.get(f"https://r.jina.ai/{TARGET_URL}", timeout=30)
            if r.status_code == 200 and "Dune" in r.text:
                page_title = "Loaded via Jina Proxy (Dune: Part Three)"
                body_text = r.text
                print("✅ Jina Proxy successfully loaded the page!")
            else:
                page_title = f"Proxy status {r.status_code}"
        except Exception as e:
            print(f"Proxy fallback failed: {e}")

    if TEST_MODE:
        snippet = body_text[:200].replace("\n", " ") if body_text else "No body text"
        send_alert(f"Cloud Bypass Test!\n**Result:** `{page_title}`\n**Preview:** `{snippet}...`")
        return

    if "Détails du film" in page_title or "Loaded via Jina Proxy" in page_title or "Dune: Part Three" in body_text:
        # Look for time slots appearing (e.g., 19:30, 20:00)
        has_showtimes = any(t in body_text for t in ["14:", "15:", "16:", "17:", "19:", "20:", "21:", "22:"])
        if has_showtimes:
            send_alert(f"Showtime slots detected on Kinepolis!\nGo buy NOW: {TARGET_URL}")
        else:
            print("✅ Checked cleanly. Still no showtimes.")
    else:
        print(f"⚠️ Could not bypass 403 on this run (Status: {page_title}).")

if __name__ == "__main__":
    run_check()
