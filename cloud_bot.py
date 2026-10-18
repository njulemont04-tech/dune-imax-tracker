import os
import sys
import requests
from playwright.sync_api import sync_playwright

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
TARGET_URL = "https://kinepolis.be/fr/films/dune-part-three/HO00013472/"
# Set TEST_ALERT via workflow input to test your phone connection from the cloud
TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"

def send_alert(message):
    if not DISCORD_WEBHOOK_URL:
        print("Error: DISCORD_WEBHOOK secret is missing!")
        return
    data = {"content": f"@everyone 🚨 **DUNE 3 CLOUD ALERT** 🚨\n{message}"}
    requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=10)

def run_check():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--window-size=1920,1080"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="fr-BE"
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print("Loading Kinepolis Dune: Part Three page from GitHub Cloud...")
        page.goto(TARGET_URL, timeout=45000)
        page.wait_for_timeout(8000)

        page_title = page.title()
        body_text = page.inner_text("body")
        html_content = page.content()

        print(f"Page Title loaded: '{page_title}'")

        if TEST_MODE:
            print("✅ Cloud Test Mode enabled! Sending test ping to Discord...")
            send_alert(f"GitHub Cloud Tracker is LIVE! Page title read as: `{page_title}`\n{TARGET_URL}")
            browser.close()
            return

        # Check if Cloudflare blocked the GitHub datacenter IP
        if "Just a moment" in page_title or "Attention Required" in page_title or "Cloudflare" in page_title:
            print("⚠️ Cloudflare challenged the GitHub IP on this run. Skipping gracefully.")
            browser.close()
            return

        # Confirm we are actually on the Kinepolis movie page
        if "Détails du film" not in page_title and "Dune" not in body_text:
            print(f"⚠️ Unexpected page state ('{page_title}'). Skipping.")
            browser.close()
            return

        # Accept cookies if banner appears
        try:
            cookie_btn = page.locator("#onetrust-accept-btn-handler")
            if cookie_btn.is_visible(timeout=2000):
                cookie_btn.click()
                page.wait_for_timeout(2000)
        except Exception:
            pass

        # If no cinema is selected on a fresh cloud session, check the underlying showtime/session data
        # On Kinepolis Belgium, when Zero showtimes exist nationwide for a film, no session times (HH:MM) or IMAX badges render in the showtime block
        body_text = page.inner_text("body")

        # Look for session time indicators or disappearance of empty states
        has_showtime_buttons = any(t in body_text for t in ["14:", "15:", "16:", "17:", "19:", "20:", "21:", "22:"])
        
        if has_showtime_buttons:
            print("🚨 SHOWTIMES DETECTED ON PAGE! Sending Discord alert!")
            send_alert(f"Showtime slots were just detected on the Kinepolis Dune: Part Three page!\nCheck immediately: {TARGET_URL}")
        else:
            print("✅ Page checked cleanly. No showtime slots posted yet.")

        browser.close()

if __name__ == "__main__":
    run_check()
