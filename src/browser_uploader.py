import json
import os
import time
import datetime
from pathlib import Path
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.firefox import GeckoDriverManager

# Selectors from old project
YOUTUBE_TEXTBOX_ID = "textbox"
YOUTUBE_MADE_FOR_KIDS_NAME = "VIDEO_MADE_FOR_KIDS_MFK"
YOUTUBE_NOT_MADE_FOR_KIDS_NAME = "VIDEO_MADE_FOR_KIDS_NOT_MFK"
YOUTUBE_NEXT_BUTTON_ID = "next-button"
YOUTUBE_RADIO_BUTTON_XPATH = "//*[@id=\"radioLabel\"]"
YOUTUBE_DONE_BUTTON_ID = "done-button"

PROFILE_PATH = os.environ.get(
    "YT_FIREFOX_PROFILE",
    "/Users/cmd/Library/Application Support/Firefox/Profiles/aoi0g5my.default-release",
)


def _yt_api_key() -> str | None:
    """Prefer env var, fall back to config.json populated by idea generator."""
    key = os.environ.get("YOUTUBE_API_KEY")
    if key:
        return key.strip()
    try:
        cfg = json.loads(Path("config.json").read_text())
        return (cfg.get("youtube_api_key") or "").strip() or None
    except Exception:
        return None


def wait_for_youtube_processing(video_id: str, timeout_s: int) -> bool:
    """Poll YouTube Data API v3 until upload is finished processing.

    Returns True when status.uploadStatus == 'processed' (or at least
    'uploaded' with processingDetails.processingStatus == 'succeeded').
    Returns False on timeout or when no API key is configured — caller
    falls back to a DOM/size-based wait.
    """
    api_key = _yt_api_key()
    if not api_key or not video_id or video_id == "BROWSER_UPLOAD_SUCCESS":
        return False

    url = (
        "https://www.googleapis.com/youtube/v3/videos"
        f"?part=status,processingDetails&id={video_id}&key={api_key}"
    )
    deadline = time.time() + timeout_s
    interval = 10
    started = time.time()
    print(f"⏳ Waiting on YouTube processing for {video_id} (≤{timeout_s}s)...")
    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=15)
            data = resp.json()
            items = data.get("items") or []
            if items:
                status = items[0].get("status", {})
                pdet = items[0].get("processingDetails", {})
                upload_status = status.get("uploadStatus", "")
                processing = pdet.get("processingStatus", "")
                if upload_status == "processed":
                    print(f"✅ YouTube finished processing {video_id}")
                    return True
                if upload_status == "uploaded" and processing == "succeeded":
                    print(f"✅ YouTube accepted upload {video_id}")
                    return True
                if upload_status == "failed" or processing == "failed":
                    print(f"⚠️ YouTube reported upload failure for {video_id}")
                    return False
            elif data.get("error"):
                print(f"⚠️ YouTube API error: {data['error'].get('message','?')}")
                return False
        except Exception as e:
            print(f"⚠️ YouTube API poll error: {e}")
        # Back off to 30s after the first 2 minutes so we don't spam the API
        if time.time() - started > 120:
            interval = 30
        time.sleep(interval)
    print(f"⏰ Timed out waiting for YouTube to finish processing {video_id}")
    return False


def _wait_for_share_link(driver, max_wait: int = 120) -> str | None:
    """Poll the Studio upload dialog until a share link is available.

    A populated share link is the first reliable signal from the UI that
    the upload has finished — Studio keeps writing bytes after "Done" is
    clicked, so the old 10-second sleep frequently killed the browser
    mid-upload on longer videos.
    """
    selectors = "a.style-scope.ytcp-video-share-config, span.video-url-wrapper a"
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            link_els = driver.find_elements(By.CSS_SELECTOR, selectors)
            for el in link_els:
                href = el.get_attribute("href") or ""
                if "youtu.be" in href or "youtube.com/watch" in href:
                    vid = href.split("/")[-1]
                    if "?" in vid:
                        vid = vid.split("?")[0]
                    if vid:
                        return vid
        except Exception:
            pass
        time.sleep(2)
    return None

def get_browser():
    options = Options()
    options.add_argument("-headless") 
    options.set_preference("profile", PROFILE_PATH)
    options.add_argument("-profile")
    options.add_argument(PROFILE_PATH)
    
    # Check if Firefox exists in common locations
    firefox_bin = "/Applications/Firefox.app/Contents/MacOS/firefox"
    if os.path.exists(firefox_bin):
        options.binary_location = firefox_bin

    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=options)
    return driver

def upload_to_youtube_browser(video_path, title, description, tags, thumbnail_path=None):
    print(f"🌐 Uploading '{video_path}' using browser profile...")
    driver = None
    try:
        driver = get_browser()
        driver.get("https://www.youtube.com/upload")
        time.sleep(5)

        # Check if login is required
        if "login" in driver.current_url.lower() or "signin" in driver.current_url.lower():
            print("❌ Browser profile is NOT logged in. Please log in manually in Firefox first.")
            driver.quit()
            return None

        # Set video file
        print("📤 Selecting video file...")
        file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
        file_input.send_keys(str(Path(video_path).resolve()))
        time.sleep(10) # Wait for initial upload/processing

        # Set title
        print("📝 Setting title and description...")
        textboxes = driver.find_elements(By.ID, YOUTUBE_TEXTBOX_ID)
        if len(textboxes) >= 2:
            title_el = textboxes[0]
            description_el = textboxes[1]
            
            # Use JS to click or clear if normal click is blocked
            driver.execute_script("arguments[0].scrollIntoView(true);", title_el)
            time.sleep(1)
            title_el.click()
            time.sleep(1)
            title_el.send_keys(Keys.COMMAND + "a")
            title_el.send_keys(Keys.BACKSPACE)
            title_el.send_keys(title)
            title_el.send_keys(Keys.ESCAPE) # Clear suggestions
            
            time.sleep(2)
            driver.execute_script("arguments[0].scrollIntoView(true);", description_el)
            description_el.click()
            time.sleep(1)
            description_el.send_keys(Keys.COMMAND + "a")
            description_el.send_keys(Keys.BACKSPACE)
            description_el.send_keys(f"{description}\n\nTags: {tags}")
            description_el.send_keys(Keys.ESCAPE) # Clear suggestions
        
        # Set `not made for kids`
        print("👶 Setting audience...")
        try:
            not_for_kids = driver.find_element(By.NAME, YOUTUBE_NOT_MADE_FOR_KIDS_NAME)
            driver.execute_script("arguments[0].click();", not_for_kids)
        except:
            # Try finding by text if name fails
            try:
                el = driver.find_element(By.XPATH, "//*[contains(text(), 'No, it')]")
                driver.execute_script("arguments[0].click();", el)
            except:
                print("⚠️ Could not set audience, might fail later.")
        
        time.sleep(2)

        # Click next 3 times
        for i in range(3):
            print(f"➡️ Clicking Next ({i+1}/3)...")
            try:
                next_btn = driver.find_element(By.ID, YOUTUBE_NEXT_BUTTON_ID)
                driver.execute_script("arguments[0].click();", next_btn)
            except:
                print(f"⚠️ Could not click Next ({i+1}), trying generic Next...")
                btns = driver.find_elements(By.XPATH, "//*[text()='Next']")
                if btns: driver.execute_script("arguments[0].click();", btns[0])
            time.sleep(3)

        # Set visibility to Unlisted
        print("👁️ Setting visibility to Unlisted...")
        try:
            radios = driver.find_elements(By.XPATH, YOUTUBE_RADIO_BUTTON_XPATH)
            if len(radios) >= 3:
                driver.execute_script("arguments[0].click();", radios[1]) # Usually Unlisted
        except:
            print("⚠️ Could not set visibility.")
        
        # Click Done
        print("✅ Clicking Done...")
        try:
            done_btn = driver.find_element(By.ID, YOUTUBE_DONE_BUTTON_ID)
            driver.execute_script("arguments[0].click();", done_btn)
        except:
            done_btns = driver.find_elements(By.XPATH, "//*[text()='Done' or text()='Save' or text()='Publish']")
            if done_btns: driver.execute_script("arguments[0].click();", done_btns[0])

        # Size-scaled DOM wait so large uploads don't get cut off.
        try:
            size_mb = Path(video_path).stat().st_size / (1024 * 1024)
        except Exception:
            size_mb = 0
        dom_timeout = max(120, int(size_mb * 3))    # ~3s per MB, floor 2min
        print(f"🔗 Waiting for share link (≤{dom_timeout}s, file ~{size_mb:.0f} MB)...")
        video_id = _wait_for_share_link(driver, max_wait=dom_timeout)
        if not video_id:
            print("⚠️ Share link never appeared — treating as failure.")
            driver.quit()
            return None

        print(f"🎉 Share link found — video ID: {video_id}")
        driver.quit()

        # Server-side processing wait via YouTube Data API v3.
        api_timeout = min(1800, max(180, int(size_mb * 4)))
        processed = wait_for_youtube_processing(video_id, api_timeout)
        if not processed:
            # No API key (or timed out) — sleep scaled to size so we never
            # return while bytes might still be uploading.
            fallback = min(900, max(30, int(size_mb * 2)))
            print(f"⏳ No API confirmation; sleeping {fallback}s as a safety net.")
            time.sleep(fallback)
        return video_id

    except Exception as e:
        print(f"❌ Browser upload error: {e}")
        if driver:
            driver.quit()
        return None
