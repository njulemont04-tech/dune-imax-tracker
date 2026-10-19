import os
import requests

# Automatically attach GITHUB_TOKEN to any background api.github.com requests made by Camoufox
_orig_get = requests.get
def _patched_get(url, *args, **kwargs):
    if "api.github.com" in str(url) and os.environ.get("GITHUB_TOKEN"):
        headers = dict(kwargs.get("headers") or {})
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
        kwargs["headers"] = headers
    return _orig_get(url, *args, **kwargs)
requests.get = _patched_get

from camoufox.sync_api import Camoufox

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
TARGET_URL = "https://www.kinepolis.be/fr/films/dune-part-three/HO00013472/"
TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"

def send_alert(message):
    if not DISCORD_WEBHOOK_URL:
        print("Error: DISCORD_WEBHOOK secret is missing!")
        return
    data = {"content": f"@everyone 🚨 **DUNE 3 CLOUD ALERT** 🚨\n{message}"}
    try:
        _orig_get  # keep reference clean
        requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=10)
    except Exception as e:
        print(f"Discord webhook error: {e}")

def run_check():
    print("Launching Camoufox stealth browser...")
    try:
        with Camoufox(headless=True, humanize=True) as browser:
            page = browser.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})

            # 1. Pre-inject Kinepolis Brussels (KBRU) into localStorage
            selected_sites_json = '[{"id":"KBRU","name":{"text":"Kinepolis Brussel","translations":[{"languageTag":"fr-BE","text":"Kinepolis Bruxelles"}]},"location":{"latitude":50.8950004577637,"longitude":4.34110021591186},"contactDetails":{"phoneNumbers":[],"email":"2003@kinepolis.com","address":{"line1":"Eeuwfeestlaan 20","line2":""}}}]'
            
            page.goto("https://www.kinepolis.be/fr/", timeout=45000)
            page.evaluate(f"localStorage.setItem('selectedSites', {repr(selected_sites_json)});")
            page.evaluate("localStorage.setItem('languageCode', 'fr-BE');")

            # 2. Navigate to the Dune: Part Three movie page
            print("Navigating to Dune 3 page with Brussels pre-loaded...")
            page.goto(TARGET_URL, timeout=45000)
            page.wait_for_timeout(6000)

            page_title = page.title()
            body_text = page.inner_text("body")

            showtimes_Idx = body_text.find("Showtimes")
            if showtimes_Idx == -1:
                showtimes_Idx = body_text.find("Séances")
            showtimes_snippet = body_text[showtimes_Idx:showtimes_Idx+300].replace("\n", " ") if showtimes_Idx != -1 else body_text[-300:].replace("\n", " ")

            print(f"Page Title: {page_title}")
            print(f"Showtimes Snippet: {showtimes_snippet}")

            if TEST_MODE:
                send_alert(f"Cloud Check Test!\n**Title:** `{page_title}`\n**Snippet:** `{showtimes_snippet}`")
                return

            # Guard against Cloudflare challenge or partial load
            if "Détails du film" not in page_title and "Dune" not in body_text:
                print(f"⚠️ Temporary Cloudflare challenge or slow load ('{page_title}'). Will retry on next cycle.")
                return

            # 3. Check if tickets have dropped
            if "No showtimes available" in body_text or "Veuillez essayer une autre sélection" in body_text:
                print("✅ Verified: 'No showtimes available' detected cleanly for Brussels!")
            elif "Aucun cinéma sélectionné" in body_text:
                print("⚠️ Cinema storage didn't take on this load, skipping.")
            else:
                has_times = any(t in body_text for t in ["14:", "15:", "16:", "17:", "19:", "20:", "21:", "22:"])
                if has_times:
                    send_alert(f"🚨 SHOWTIMES DETECTED ON KINEPOLIS BRUSSELS!\nGo buy tickets NOW: {TARGET_URL}")
                else:
                    print("🚨 Page changed! Sending alert...")
                    send_alert(f"Kinepolis page updated!\n**Snippet:** `{showtimes_snippet}`\nGo check: {TARGET_URL}")

    except Exception as e:
        print(f"⚠️ Handled transient error cleanly: {e}")

if __name__ == "__main__":
    run_check()
