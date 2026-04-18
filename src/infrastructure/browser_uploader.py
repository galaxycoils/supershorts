import os
import sys
import glob
import time
import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager

# Selectors from old project
YOUTUBE_TEXTBOX_ID = "textbox"
YOUTUBE_MADE_FOR_KIDS_NAME = "VIDEO_MADE_FOR_KIDS_MFK"
YOUTUBE_NOT_MADE_FOR_KIDS_NAME = "VIDEO_MADE_FOR_KIDS_NOT_MFK"
YOUTUBE_NEXT_BUTTON_ID = "next-button"
YOUTUBE_RADIO_BUTTON_XPATH = "//*[@id=\"radioLabel\"]"
YOUTUBE_DONE_BUTTON_ID = "done-button"

# 0=Public, 1=Unlisted, 2=Private — override with YT_VISIBILITY env var
VISIBILITY_INDEX = int(os.environ.get("YT_VISIBILITY", "1"))


def _find_firefox_profile() -> str:
    """Auto-discover Firefox default-release profile across OS or use FIREFOX_PROFILE_PATH env var."""
    env = os.environ.get("FIREFOX_PROFILE_PATH", "").strip()
    if env and os.path.isdir(env):
        return env
    
    # OS-specific search paths
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support/Firefox/Profiles")
    elif sys.platform == "win32":
        base = os.path.expanduser("~/AppData/Roaming/Mozilla/Firefox/Profiles")
    else: # Linux
        # Try both standard and snap paths
        bases = [
            os.path.expanduser("~/.mozilla/firefox"),
            os.path.expanduser("~/snap/firefox/common/.mozilla/firefox")
        ]
        base = next((b for b in bases if os.path.isdir(b)), bases[0])

    if not os.path.isdir(base):
        raise RuntimeError(f"Firefox profile directory not found at {base}. Set FIREFOX_PROFILE_PATH.")

    # Prioritize default-release
    hits = glob.glob(f"{base}/*.default-release")
    if hits:
        return hits[0]
    
    # Fallback to any profile
    hits = glob.glob(f"{base}/*")
    for hit in hits:
        if os.path.isdir(hit) and ("default" in hit or "release" in hit):
            return hit
            
    if hits:
        return hits[0]

    raise RuntimeError(
        "No Firefox profile found. Set FIREFOX_PROFILE_PATH env var to your profile directory."
    )


PROFILE_PATH = _find_firefox_profile()


def get_browser():
    options = Options()
    options.add_argument("--headless")
    # Using profile with -profile arg is more reliable than set_preference("profile")
    options.add_argument("-profile")
    options.add_argument(PROFILE_PATH)

    # Check if Firefox exists in common locations
    if sys.platform == "darwin":
        firefox_bin = "/Applications/Firefox.app/Contents/MacOS/firefox"
        if os.path.exists(firefox_bin):
            options.binary_location = firefox_bin

    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=options)
    return driver


def _extract_video_id(driver) -> str | None:
    """Poll up to 30s for a real 11-char YouTube video ID after Done is clicked."""
    deadline = time.time() + 30
    while time.time() < deadline:
        # Check address bar redirect
        try:
            url = driver.current_url
            for pattern in ("youtu.be/", "youtube.com/watch?v="):
                if pattern in url:
                    vid = url.split(pattern)[-1].split("&")[0].split("?")[0]
                    if len(vid) == 11:
                        return vid

            # Check post-upload dialog link elements
            link_els = driver.find_elements(
                By.CSS_SELECTOR,
                "a.style-scope.ytcp-video-share-config, span.video-url-wrapper a, a[href*='youtu.be'], a[href*='youtube.com/watch']"
            )
            for el in link_els:
                href = el.get_attribute("href") or ""
                for pattern in ("youtu.be/", "youtube.com/watch?v="):
                    if pattern in href:
                        vid = href.split(pattern)[-1].split("&")[0].split("?")[0]
                        if len(vid) == 11:
                            return vid
        except Exception:
            pass

        time.sleep(2)
    return None


def upload_to_youtube_browser(video_path, title, description, tags, thumbnail_path=None):
    print(f"🌐 Uploading '{video_path}' using browser profile...")
    driver = None
    try:
        driver = get_browser()
        wait = WebDriverWait(driver, 20)
        driver.get("https://www.youtube.com/upload")
        
        # Wait for page to load or check for login
        time.sleep(5) 

        # Check if login is required
        if "login" in driver.current_url.lower() or "signin" in driver.current_url.lower():
            print("❌ Browser profile is NOT logged in. Please log in manually in Firefox first.")
            driver.quit()
            return None

        # Set video file
        print("📤 Selecting video file...")
        file_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']")))
        file_input.send_keys(str(Path(video_path).resolve()))
        
        # Wait for textboxes to appear (indicates file selection accepted)
        print("📝 Setting title and description...")
        wait.until(EC.presence_of_all_elements_located((By.ID, YOUTUBE_TEXTBOX_ID)))
        
        textboxes = driver.find_elements(By.ID, YOUTUBE_TEXTBOX_ID)
        if len(textboxes) >= 2:
            title_el = textboxes[0]
            description_el = textboxes[1]

            # OS-agnostic select-all key
            select_all = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL
            
            driver.execute_script("arguments[0].scrollIntoView(true);", title_el)
            time.sleep(1)
            title_el.click()
            time.sleep(1)
            # Use OS-agnostic key to clear and type
            title_el.send_keys(select_all + "a")
            title_el.send_keys(Keys.BACKSPACE)
            title_el.send_keys(title)
            title_el.send_keys(Keys.ESCAPE)

            time.sleep(2)
            driver.execute_script("arguments[0].scrollIntoView(true);", description_el)
            description_el.click()
            time.sleep(1)
            description_el.send_keys(select_all + "a")
            description_el.send_keys(Keys.BACKSPACE)
            description_el.send_keys(f"{description}\n\nTags: {tags}")
            description_el.send_keys(Keys.ESCAPE)

        # Set `not made for kids`
        print("👶 Setting audience...")
        try:
            not_for_kids = wait.until(EC.element_to_be_clickable((By.NAME, YOUTUBE_NOT_MADE_FOR_KIDS_NAME)))
            driver.execute_script("arguments[0].click();", not_for_kids)
        except Exception:
            try:
                el = driver.find_element(By.XPATH, "//*[contains(text(), 'No, it')]")
                driver.execute_script("arguments[0].click();", el)
            except Exception as e:
                print(f"⚠️ Could not set audience: {e}")

        # Click next 3 times
        for i in range(3):
            print(f"➡️ Clicking Next ({i+1}/3)...")
            try:
                next_btn = wait.until(EC.element_to_be_clickable((By.ID, YOUTUBE_NEXT_BUTTON_ID)))
                driver.execute_script("arguments[0].click();", next_btn)
            except Exception:
                print(f"⚠️ Could not click Next ({i+1}), trying generic Next...")
                btns = driver.find_elements(By.XPATH, "//*[text()='Next']")
                if btns:
                    driver.execute_script("arguments[0].click();", btns[0])
            time.sleep(2)

        # Set visibility
        vis_labels = {0: "Public", 1: "Unlisted", 2: "Private"}
        print(f"👁️ Setting visibility to {vis_labels.get(VISIBILITY_INDEX, 'Unlisted')}...")
        try:
            # Re-fetch radios because they might be stale after 'Next' clicks
            radios = wait.until(EC.presence_of_all_elements_located((By.XPATH, YOUTUBE_RADIO_BUTTON_XPATH)))
            if len(radios) > VISIBILITY_INDEX:
                driver.execute_script("arguments[0].click();", radios[VISIBILITY_INDEX])
        except Exception as e:
            print(f"⚠️ Could not set visibility: {e}")

        # Click Done
        print("✅ Clicking Done...")
        try:
            done_btn = wait.until(EC.element_to_be_clickable((By.ID, YOUTUBE_DONE_BUTTON_ID)))
            driver.execute_script("arguments[0].click();", done_btn)
        except Exception:
            done_btns = driver.find_elements(By.XPATH, "//*[text()='Done' or text()='Save' or text()='Publish']")
            if done_btns:
                driver.execute_script("arguments[0].click();", done_btns[0])

        # Extract real video ID (poll up to 30s)
        print("🔗 Waiting for video ID...")
        video_id = _extract_video_id(driver)

        if video_id:
            print(f"🎉 Uploaded! https://youtube.com/watch?v={video_id}")
        else:
            print("⚠️ Upload may have succeeded but video ID could not be extracted. Check YouTube Studio.")

        driver.quit()
        return video_id

    except Exception as e:
        print(f"❌ Browser upload error: {e}")
        if driver:
            driver.quit()
        return None
