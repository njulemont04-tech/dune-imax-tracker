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
TARGET_URLS = [
    ("Main Movie Page", "https://www.kinepolis.be/fr/films/dune-part-three/HO00013472/"),
    ("IMAX 70mm Page", "https://www.kinepolis.be/fr/genres/dune-troisieme-partie/70mm-movies/")
]
TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"

def send_alert(message):
    if not DISCORD_WEBHOOK_URL:
        print("Error: DISCORD_WEBHOOK secret is missing!")
        return
    data = {"content": f"@everyone 🚨 **DUNE 3 IMAX 70MM ALERT** 🚨\n{message}"}
    try:
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

            test_reports = []

            # 2. Check BOTH the Main Page and the IMAX 70mm Page
            for label, url in TARGET_URLS:
                print(f"Checking {label}: {url}")
                page.goto(url, timeout=45000)
                page.wait_for_timeout(6000)

                page_title = page.title()
                body_text = page.inner_text("body")

                # Grab the relevant section of text
                idx = body_text.find("No showtimes available")
                if idx == -1:
                    idx = body_text.find("Showtimes")
                if idx == -1:
                    idx = body_text.find("Sorry, there are no films")
                snippet = body_text[idx:idx+250].replace("\n", " ") if idx != -1 else body_text[:250].replace("\n", " ")

                print(f"[{label}] Title: {page_title}")
                print(f"[{label}] Snippet: {snippet}")

                if TEST_MODE:
                    test_reports.append(f"**{label}:** `{snippet[:160]}`")
                    continue

                # Skip if Cloudflare challenge or error page
                if "Just a moment" in page_title or "Attention Required" in page_title or "Kinepolis" not in page_title:
                    print(f"⚠️ Cloudflare challenge or slow load on {label}, skipping.")
                    continue

                if label == "Main Movie Page":
                    if "No showtimes available" in body_text or "Veuillez essayer une autre sélection" in body_text:
                        print(f"✅ [{label}] Verified: Still 'No showtimes available'.")
                    elif "Aucun cinéma sélectionné" in body_text:
                        print(f"⚠️ [{label}] Cinema storage didn't take on this load.")
                    else:
                        send_alert(f"🚨 **SHOWTIMES DETECTED ON {label.upper()}!**\n👉 **70mm Link:** {TARGET_URLS[1][1]}\n👉 **Main Link:** {url}\nSnippet: `{snippet[:150]}`")
                
                elif label == "IMAX 70mm Page":
                    if "Sorry, there are no films" in body_text or "Il n’y a pas de séances" in body_text or "Il n'y a pas de séances" in body_text:
                        print(f"✅ [{label}] Verified: Still 'Sorry, there are no films!'.")
                    elif "Aucun cinéma sélectionné" in body_text:
                        print(f"⚠️ [{label}] Cinema storage didn't take on this load.")
                    else:
                        send_alert(f"🚨 **IMAX 70MM PAGE JUST WENT LIVE!**\n👉 **BOOK 70MM NOW:** {url}\n👉 **Main Link:** {TARGET_URLS[0][1]}\nSnippet: `{snippet[:150]}`")

            if TEST_MODE and test_reports:
                send_alert("Dual-URL Cloud Test!\n" + "\n".join(test_reports))

    except Exception as e:
        print(f"⚠️ Handled transient error cleanly: {e}")

if __name__ == "__main__":
    run_check()
