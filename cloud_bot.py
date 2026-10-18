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
        page.goto(TARGET_URL, timeout=45000)
        page.wait_for_timeout(6000)

        # 1. Accept cookies if banner is present
        try:
            cookie_btn = page.locator("#onetrust-accept-btn-handler")
            if cookie_btn.is_visible(timeout=3000):
                cookie_btn.click()
                page.wait_for_timeout(1500)
        except Exception:
            pass

        # 2. If 'Aucun cinéma sélectionné' is showing, automatically select Kinepolis Bruxelles!
        body_text = page.inner_text("body")
        if "Aucun cinéma sélectionné" in body_text or "Sélectionnez un ou plusieurs cinémas" in body_text:
            print("Selecting Kinepolis Bruxelles automatically...")
            try:
                # Click the blue 'Sélectionnez un ou plusieurs cinémas' button
                page.get_by_text("Sélectionnez un ou plusieurs cinémas").first.click(timeout=5000)
                page.wait_for_timeout(2000)
                # Click 'Bruxelles' in the cinema list
                page.get_by_text("Bruxelles", exact=False).first.click(timeout=5000)
                page.wait_for_timeout(1500)
                # Confirm selection if there is a confirm/save button in the modal
                for btn_text in ["Confirmer", "Enregistrer", "Appliquer", "Valider", "OK"]:
                    btn = page.get_by_role("button", name=btn_text)
                    if btn.is_visible():
                        btn.click()
                        break
                page.wait_for_timeout(4000)
            except Exception as e:
                print(f"Auto-select note: {e}")

        page_title = page.title()
        body_text = page.inner_text("body")

        # Extract the text right around the 'Showtimes' section so we can verify what it sees
        showtimes_Idx = body_text.find("Showtimes")
        if showtimes_Idx == -1:
            showtimes_Idx = body_text.find("Séances")
        showtimes_snippet = body_text[showtimes_Idx:showtimes_Idx+300].replace("\n", " ") if showtimes_Idx != -1 else body_text[-300:].replace("\n", " ")

        print(f"Showtimes section reads: {showtimes_snippet}")

        if TEST_MODE:
            send_alert(f"Cloud Showtimes Section Test!\n**Title:** `{page_title}`\n**Showtimes Box:** `{showtimes_snippet}`")
            return

        # 3. Check if showtimes have dropped!
        if "No showtimes available" in body_text or "Veuillez essayer une autre sélection" in body_text:
            print("✅ Verified: 'No showtimes available' is still present. No tickets yet.")
        elif "Aucun cinéma sélectionné" in body_text:
            # Even if cinema modal didn't close, check if any showtime hours or date tabs appeared on the page
            has_times = any(t in body_text for t in ["14:", "15:", "16:", "17:", "19:", "20:", "21:", "22:"])
            if has_times:
                send_alert(f"Showtimes detected on Kinepolis!\nGo buy NOW: {TARGET_URL}")
            else:
                print("⚠️ Cinema selector stayed on 'Aucun cinéma sélectionné', no showtime hours found.")
        else:
            if "Détails du film" in page_title and "Dune" in body_text:
                print("🚨 CHANGE DETECTED IN SHOWTIMES SECTION!")
                send_alert(f"The 'No showtimes available' message is GONE on Kinepolis!\n**Current text:** `{showtimes_snippet}`\nGo buy NOW: {TARGET_URL}")

if __name__ == "__main__":
    run_check()
