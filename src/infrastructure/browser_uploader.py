import os
import sys
import glob
import time
import datetime
import re
import concurrent.futures
from typing import Optional, Union, Any, List
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
from src.core.interfaces import IVideoUploader
from src.infrastructure.adapters.browser_adapter import BrowserAdapter

# Selectors from old project
YOUTUBE_TEXTBOX_ID = "textbox"
YOUTUBE_MADE_FOR_KIDS_NAME = "VIDEO_MADE_FOR_KIDS_MFK"
YOUTUBE_NOT_MADE_FOR_KIDS_NAME = "VIDEO_MADE_FOR_KIDS_NOT_MFK"
YOUTUBE_NEXT_BUTTON_ID = "next-button"
YOUTUBE_DONE_BUTTON_ID = "done-button"
YOUTUBE_FINISH_BUTTON_ID = "finish-button"
YOUTUBE_RADIO_BUTTON_XPATH = "//*[@id=\"radioLabel\"]"
VISIBILITY_INDEX = int(os.environ.get("YT_VISIBILITY", "1"))
VIDEO_URL_PATTERNS = (
    "youtu.be/",
    "youtube.com/watch?v=",
    "/watch?v=",
)
STUDIO_VIDEO_PATTERN = re.compile(r"/video/([A-Za-z0-9_-]{11})/")

PROFILE_PATH = str(Path.home() / "Library/Application Support/Firefox/Profiles/youtube_uploader")
FIREFOX_PROFILES_DIR = Path.home() / "Library/Application Support/Firefox/Profiles"


def _find_firefox_profile() -> str:
    env_path = os.environ.get("FIREFOX_PROFILE_PATH")
    if env_path and os.path.isdir(env_path):
        return env_path
    if os.path.isdir(PROFILE_PATH):
        return PROFILE_PATH

    if FIREFOX_PROFILES_DIR.is_dir():
        preferred = sorted(FIREFOX_PROFILES_DIR.glob("*.default-release"))
        if preferred:
            return str(preferred[0])

        fallback = sorted(FIREFOX_PROFILES_DIR.glob("*.default"))
        if fallback:
            return str(fallback[0])

        any_profiles = sorted(p for p in FIREFOX_PROFILES_DIR.iterdir() if p.is_dir())
        if any_profiles:
            return str(any_profiles[0])

    return PROFILE_PATH


def _build_firefox_service():
    from selenium.webdriver.firefox.service import Service
    port = int(os.environ.get("GECKODRIVER_PORT", "4444"))
    return Service(GeckoDriverManager().install(), port=port)


def _parse_video_id_from_text(text: str) -> Optional[str]:
    if not text:
        return None

    for pattern in VIDEO_URL_PATTERNS:
        if pattern in text:
            candidate = text.split(pattern)[-1].split("&")[0].split("?")[0].split('"')[0].strip()
            if len(candidate) == 11:
                return candidate

    match = re.search(r"(?:v=|be/)([A-Za-z0-9_-]{11})", text)
    if match:
        return match.group(1)
    match = STUDIO_VIDEO_PATTERN.search(text)
    if match:
        return match.group(1)
    return None


def _extract_video_id(driver) -> Optional[str]:
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            video_id = _parse_video_id_from_text(driver.current_url)
            if video_id:
                return video_id

            link_els = driver.find_elements(
                By.CSS_SELECTOR,
                "a.style-scope.ytcp-video-share-config, span.video-url-wrapper a, a[href*='youtu.be'], a[href*='youtube.com/watch'], input[value*='youtu.be'], input[value*='youtube.com/watch']"
            )
            for el in link_els:
                for attr in ("href", "value", "textContent", "innerText", "aria-label"):
                    video_id = _parse_video_id_from_text(el.get_attribute(attr) or "")
                    if video_id:
                        return video_id

            video_id = _parse_video_id_from_text(driver.page_source)
            if video_id:
                return video_id
        except Exception:
            pass
        time.sleep(2)
    return None


def _set_visibility(driver) -> None:
    print("👁️ Setting visibility...")
    radios = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.XPATH, YOUTUBE_RADIO_BUTTON_XPATH))
    )
    if len(radios) > VISIBILITY_INDEX:
        driver.execute_script("arguments[0].click();", radios[VISIBILITY_INDEX])


def _click_finalize_button(driver) -> None:
    for button_id in (YOUTUBE_DONE_BUTTON_ID, YOUTUBE_FINISH_BUTTON_ID):
        try:
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, button_id))
            )
            driver.execute_script("arguments[0].click();", button)
            return
        except Exception:
            continue
    raise TimeoutError("Could not click YouTube Studio finalize button")


def _find_video_id_on_studio_page(driver, title: str) -> Optional[str]:
    title_probe = title.strip().lower()[:80]
    anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='/video/']")
    for anchor in anchors:
        text = " ".join(
            filter(
                None,
                [
                    (anchor.text or "").strip(),
                    anchor.get_attribute("aria-label") or "",
                    anchor.get_attribute("title") or "",
                ],
            )
        ).lower()
        href = anchor.get_attribute("href") or ""
        if title_probe and title_probe in text:
            return _parse_video_id_from_text(href)
    return None


def _wait_for_uploaded_video_id(driver, title: str) -> Optional[str]:
    deadline = time.time() + 120
    while time.time() < deadline:
        video_id = _extract_video_id(driver)
        if video_id:
            return video_id
        try:
            video_id = _find_video_id_on_studio_page(driver, title)
            if video_id:
                return video_id
        except Exception:
            pass
        time.sleep(5)
        try:
            driver.refresh()
        except Exception:
            pass
    return None


def get_browser() -> webdriver.Firefox:
    profile_path = _find_firefox_profile()
    options = Options()
    # Force headless mode as requested by user
    options.add_argument("--headless")
    options.add_argument("-profile")
    options.add_argument(profile_path)

    if sys.platform == "darwin":
        firefox_bin = "/Applications/Firefox.app/Contents/MacOS/firefox"
        if os.path.exists(firefox_bin):
            options.binary_location = firefox_bin

    service = _build_firefox_service()
    driver = webdriver.Firefox(service=service, options=options)
    return driver


class YouTubeBrowserUploader(IVideoUploader):
    def __init__(self, browser_adapter: BrowserAdapter = None):
        self.browser = browser_adapter or BrowserAdapter()

    def upload(self, video_path: Path, title: str, description: str, tags: List[str], thumbnail_path: Optional[Path] = None) -> Optional[str]:
        """Uploads a video using the browser's background task queue."""
        future = concurrent.futures.Future()

        def task_fn():
            try:
                # We normalize tags here as the standalone function does it too, 
                # but we'll pass the list/string as-is and let it handle it.
                result = upload_to_youtube_browser(
                    video_path=video_path,
                    title=title,
                    description=description,
                    tags=tags,
                    thumbnail_path=thumbnail_path
                )
                future.set_result(result)
            except Exception as e:
                print(f"❌ Task execution failed in browser worker: {e}")
                future.set_result(None)

        print(f"🕒 Queuing upload task for '{title}'...")
        self.browser.push_task(task_fn)
        
        # Wait for the background worker to finish the task
        return future.result()


def upload_to_youtube_browser(video_path: Union[str, Path], title: str, description: str,
                               tags: Union[str, List[str]],
                               thumbnail_path: Optional[Union[str, Path]] = None) -> Optional[str]:
    if isinstance(tags, list):
        tags_str = ", ".join(tags)
    else:
        tags_str = ", ".join(t.strip() for t in str(tags).split(',') if t.strip())
    print(f"🌐 Uploading '{video_path}' using browser profile...")
    driver = None
    try:
        driver = get_browser()
        driver.get("https://www.youtube.com/upload")
        time.sleep(5)

        if "login" in driver.current_url.lower() or "signin" in driver.current_url.lower():
            print("❌ Browser profile is NOT logged in.")
            return None

        print("📤 Selecting video file...")
        file_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )
        file_input.send_keys(str(Path(video_path).resolve()))

        print("📝 Setting title and description...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.ID, YOUTUBE_TEXTBOX_ID))
        )
        textboxes = driver.find_elements(By.ID, YOUTUBE_TEXTBOX_ID)

        if len(textboxes) >= 2:
            title_el, description_el = textboxes[0], textboxes[1]
            select_all = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL

            driver.execute_script("arguments[0].scrollIntoView(true);", title_el)
            time.sleep(1)
            title_el.click()
            time.sleep(1)
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
            description_el.send_keys(f"{description}\n\nTags: {tags_str}")
            description_el.send_keys(Keys.ESCAPE)

        print("👶 Setting audience...")
        try:
            not_for_kids = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.NAME, YOUTUBE_NOT_MADE_FOR_KIDS_NAME))
            )
            driver.execute_script("arguments[0].click();", not_for_kids)
        except Exception as e:
            print(f"⚠️ Could not set audience: {e}")

        for i in range(3):
            print(f"➡️ Clicking Next ({i+1}/3)...")
            try:
                next_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, YOUTUBE_NEXT_BUTTON_ID))
                )
                driver.execute_script("arguments[0].click();", next_btn)
            except Exception:
                time.sleep(2)
                next_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, YOUTUBE_NEXT_BUTTON_ID))
                )
                driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(2)

        try:
            _set_visibility(driver)
        except Exception as e:
            print(f"⚠️ Could not set visibility: {e}")

        print("🏁 Clicking Done/Finish...")
        try:
            _click_finalize_button(driver)
        except Exception as e:
            print(f"⚠️ Could not click Done: {e}")

        time.sleep(5)
        video_id = _wait_for_uploaded_video_id(driver, title)
        if video_id:
            print(f"✅ Upload successful! Video ID: {video_id}")
        else:
            print(f"⚠️ Could not extract video ID. Final URL: {driver.current_url}")
        return video_id

    except Exception as e:
        print(f"❌ Browser upload failed: {e}")
        return None
    finally:
        if driver:
            driver.quit()
