import os
import requests
from camoufox.sync_api import Camoufox

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
TARGET_URL = "https://www.kinepolis.be/fr/films/dune-part-three/HO00013472/"
TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"

def send_alert(message):
    if not DISCORD_WEBHOOK_URL:
        print("Error: DISCORD_WEBHOOK secret is missing!")
        return
    data = {"content": f"@everyone 🚨 **DUNE 3 CLOUD ALERT** 🚨\n{message}"}
    requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=10)

def run_check():
    print("Launching Camoufox stealth browser...")
    with Camoufox(headless=True, humanize=True) as browser:
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})

        # 1. Pre-inject the exact Kinepolis Brussels selection into localStorage before loading the page!
        selected_sites_json = '[{"id":"KBRU","name":{"text":"Kinepolis Brussel","translations":[{"languageTag":"fr-BE","text":"Kinepolis Bruxelles"}]},"location":{"latitude":50.8950004577637,"longitude":4.34110021591186},"contactDetails":{"phoneNumbers":[],"email":"2003@kinepolis.com","address":{"line1":"Eeuwfeestlaan 20","line2":""}}}]'
        
        page.goto("https://www.kinepolis.be/fr/", timeout=45000)
        page.evaluate(f"localStorage.setItem('selectedSites', {repr(selected_sites_json)});")
        page.evaluate("localStorage.setItem('languageCode', 'fr-BE');")

        # 2. Now navigate directly to the Dune 3 page with Brussels already saved!
        print("Navigating to Dune 3 page with Brussels pre-loaded...")
        page.goto(TARGET_URL, timeout=45000)
        page.wait_for_timeout(6000)

        page_title = page.title()
        body_text = page.inner_text("body")

        # Find the showtimes section snippet
        showtimes_Idx = body_text.find("Showtimes")
        if showtimes_Idx == -1:
            showtimes_Idx = body_text.find("Séances")
        showtimes_snippet = body_text[showtimes_Idx:showtimes_Idx+300].replace("\n", " ") if showtimes_Idx != -1 else body_text[-300:].replace("\n", " ")

        print(f"Page Title: {page_title}")
        print(f"Showtimes Snippet: {showtimes_snippet}")

        if TEST_MODE:
            send_alert(f"Cloud Final Injection Test!\n**Title:** `{page_title}`\n**Snippet:** `{showtimes_snippet}`")
            return

        # 3. Check if tickets have dropped
        if "No showtimes available" in body_text or "Veuillez essayer une autre sélection" in body_text:
            print("✅ Verified: 'No showtimes available' detected cleanly for Brussels!")
        elif "Aucun cinéma sélectionné" in body_text:
            print("⚠️ Cinema storage didn't take, still showing no cinema selected.")
        else:
            # Check if actual time slots (HH:MM) have appeared
            has_times = any(t in body_text for t in ["14:", "15:", "16:", "17:", "19:", "20:", "21:", "22:"])
            if has_times:
                send_alert(f"🚨 SHOWTIMES DETECTED ON KINEPOLIS BRUSSELS!\nGo buy tickets NOW: {TARGET_URL}")
            else:
                print("🚨 Page changed! Checking text...")
                send_alert(f"Kinepolis page updated!\n**Snippet:** `{showtimes_snippet}`\nGo check: {TARGET_URL}")

if __name__ == "__main__":
    run_check()
