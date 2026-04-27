import os
import sys
import time
from typing import Optional, List, Union
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
from src.core.interfaces import IVideoUploader
from src.infrastructure.browser_uploader import _find_firefox_profile, _build_firefox_service, _get_firefox_profiles_dir

# TikTok Selectors (Subject to change, should be configurable)
TIKTOK_UPLOAD_URL = "https://www.tiktok.com/upload"
TIKTOK_FILE_INPUT_CSS = "input[type='file']"
TIKTOK_CAPTION_SELECTOR = ".public-DraftEditor-content"
TIKTOK_POST_BUTTON_XPATH = "//button[contains(., 'Post')]"

class TikTokUploader(IVideoUploader):
    """TikTok uploader using Selenium and a Firefox profile."""
    
    def __init__(self, profile_name: str = "tiktok_uploader"):
        self.profile_name = profile_name

    def _find_tiktok_profile(self) -> str:
        """Finds a suitable Firefox profile for TikTok upload."""
        env_path = os.environ.get("TIKTOK_FIREFOX_PROFILE_PATH")
        if env_path and os.path.isdir(env_path):
            return env_path

        profiles_dir = _get_firefox_profiles_dir()
        tiktok_profile = profiles_dir / self.profile_name

        if tiktok_profile.is_dir():
            return str(tiktok_profile)

        # Fallback to the general profile finding logic if tiktok specific doesn't exist
        return _find_firefox_profile()

    def _get_browser(self) -> webdriver.Firefox:
        """Initializes and returns a Firefox browser instance."""
        profile_path = self._find_tiktok_profile()
        options = Options()
        # Force headless mode for automation
        options.add_argument("--headless")
        options.add_argument("-profile")
        options.add_argument(profile_path)

        # Allow override via environment variable
        env_bin = os.environ.get("FIREFOX_BINARY")
        if env_bin and os.path.exists(env_bin):
            options.binary_location = env_bin
        elif sys.platform == "darwin":
            firefox_bin = "/Applications/Firefox.app/Contents/MacOS/firefox"
            if os.path.exists(firefox_bin):
                options.binary_location = firefox_bin

        service = _build_firefox_service()
        driver = webdriver.Firefox(service=service, options=options)
        return driver

    def upload(self, video_path: Path, title: str, description: str, tags: List[str], thumbnail_path: Optional[Path] = None) -> Optional[str]:
        """Uploads a video to TikTok using Selenium."""
        print(f"🌐 Uploading '{video_path}' to TikTok...")
        driver = None
        try:
            driver = self._get_browser()
            driver.get(TIKTOK_UPLOAD_URL)
            time.sleep(5)

            # Check if logged in
            if "login" in driver.current_url.lower() or "signin" in driver.current_url.lower():
                print("❌ TikTok profile is NOT logged in.")
                return None

            print("📤 Selecting video file...")
            # TikTok sometimes uses an iframe for the upload component
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                )
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    driver.switch_to.frame(iframe)
                    if driver.find_elements(By.CSS_SELECTOR, TIKTOK_FILE_INPUT_CSS):
                        break
                    driver.switch_to.default_content()
            except Exception:
                print("ℹ️ No suitable iframe found, continuing with direct elements.")

            file_input = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, TIKTOK_FILE_INPUT_CSS))
            )
            file_input.send_keys(str(video_path.resolve()))

            print("📝 Setting caption...")
            # Wait for upload to progress enough for caption box to be interactable
            caption_el = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, TIKTOK_CAPTION_SELECTOR))
            )
            
            # Combine title, description and tags for TikTok caption
            # TikTok captions are limited, so we prioritize title and tags
            tag_str = " ".join([f"#{t.strip('#')}" for t in tags])
            full_caption = f"{title}\n{description}\n{tag_str}"
            
            caption_el.click()
            select_all = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL
            caption_el.send_keys(select_all + "a")
            caption_el.send_keys(Keys.BACKSPACE)
            caption_el.send_keys(full_caption)

            print("🏁 Clicking Post...")
            post_btn = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, TIKTOK_POST_BUTTON_XPATH))
            )
            driver.execute_script("arguments[0].click();", post_btn)

            # Wait for success indicator
            time.sleep(10)
            print(f"✅ TikTok upload initiated for '{title}'")
            
            # TikTok web doesn't easily return a video ID immediately
            return "tiktok_upload_success"

        except Exception as e:
            print(f"❌ TikTok upload failed: {e}")
            return None
        finally:
            if driver:
                driver.quit()
