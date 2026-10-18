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
    print("Launching Camoufox stealth browser...")
    with Camoufox(headless=True, humanize=True) as browser:
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.goto(TARGET_URL, timeout=45000)
        page.wait_for_timeout(6000)

        # 1. Accept cookies if banner is present
        try:
            cookie_btn = page.locator("#onetrust-accept-btn-handler")
            if cookie_btn.is_visible(timeout=4000):
                cookie_btn.click()
                page.wait_for_timeout(2000)
        except Exception:
            pass

        # 2. Scroll down to Showtimes and open the cinema selector modal
        try:
            select_btn = page.locator("text=Sélectionnez un ou plusieurs cinémas").first
            if select_btn.is_visible(timeout=5000):
                select_btn.scroll_into_view_if_needed()
                select_btn.click()
                page.wait_for_timeout(3000)

                # Find all visible elements with 'Bruxelles' and click them
                bruxelles_items = page.locator("text=Bruxelles").all()
                print(f"Found {len(bruxelles_items)} elements matching 'Bruxelles'")
                for item in bruxelles_items:
                    if item.is_visible():
                        try:
                            item.click( timeout=2000)
                            print("Clicked visible 'Bruxelles' option!")
                            page.wait_for_timeout(1000)
                        except Exception:
                            pass

                # Look for any visible button in the modal to confirm/save
                buttons = page.locator("button").all()
                visible_btn_texts = []
                for b in buttons:
                    if b.is_visible():
                        txt = b.inner_text().strip()
                        if txt:
                            visible_btn_texts.append(txt)
                        if any(word in txt.lower() for word in ["confirm", "enregistr", "appliqu", "valid", "sauvegard", "choisir", "sélection", "voir"]):
                            try:
                                b.click(timeout=2000)
                                print(f"Clicked confirm button: {txt}")
                            except Exception:
                                pass
                print(f"Visible buttons on screen: {visible_btn_texts}")
                page.wait_for_timeout(5000)
        except Exception as e:
            print(f"Modal interaction error: {e}")

        page_title = page.title()
        body_text = page.inner_text("body")

        showtimes_Idx = body_text.find("Showtimes")
        if showtimes_Idx == -1:
            showtimes_Idx = body_text.find("Séances")
        showtimes_snippet = body_text[showtimes_Idx:showtimes_Idx+350].replace("\n", " ") if showtimes_Idx != -1 else body_text[-350:].replace("\n", " ")

        print(f"Showtimes section reads: {showtimes_snippet}")

        if TEST_MODE:
            send_alert(f"Cloud Modal Test!\n**Title:** `{page_title}`\n**Showtimes Box:** `{showtimes_snippet}`")
            return

        # 3. Check if showtimes have dropped
        if "No showtimes available" in body_text or "Veuillez essayer une autre sélection" in body_text:
            print("✅ Verified: 'No showtimes available' is present. No tickets yet.")
        elif "Aucun cinéma sélectionné" not in body_text and "Détails du film" in page_title:
            print("🚨 CHANGE DETECTED IN SHOWTIMES SECTION!")
            send_alert(f"The 'No showtimes available' message is GONE on Kinepolis!\n**Current text:** `{showtimes_snippet}`\nGo buy NOW: {TARGET_URL}")
        else:
            # Fallback: check if any time slots (HH:MM) appeared on the page
            has_times = any(t in body_text for t in ["14:", "15:", "16:", "17:", "19:", "20:", "21:", "22:"])
            if has_times:
                send_alert(f"Showtime hours detected on Kinepolis!\nGo buy NOW: {TARGET_URL}")
            else:
                print("⚠️ Still on 'Aucun cinéma sélectionné', check logs for button names.")

if __name__ == "__main__":
    run_check()
