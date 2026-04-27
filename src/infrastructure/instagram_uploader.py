import os
import sys
import time
import concurrent.futures
from pathlib import Path
from typing import List, Optional, Union
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.core.interfaces import IVideoUploader
from src.infrastructure.browser_uploader import get_browser
from src.infrastructure.adapters.browser_adapter import BrowserAdapter

class InstagramUploader(IVideoUploader):
    """Instagram uploader using Selenium."""
    
    def __init__(self, browser_adapter: BrowserAdapter = None):
        self.browser = browser_adapter or BrowserAdapter()

    def upload(self, video_path: Path, title: str, description: str, tags: List[str], thumbnail_path: Optional[Path] = None) -> Optional[str]:
        """Uploads a video to Instagram using the browser's background task queue."""
        future = concurrent.futures.Future()

        def task_fn():
            try:
                # Combine title, description and tags for Instagram caption
                caption = f"{title}\n\n{description}\n\n"
                caption += " ".join([f"#{tag.strip().replace(' ', '')}" for tag in tags])
                
                result = upload_to_instagram_browser(
                    video_path=video_path,
                    caption=caption
                )
                future.set_result(result)
            except Exception as e:
                print(f"❌ Instagram upload task failed: {e}")
                future.set_result(None)

        print(f"🕒 Queuing Instagram upload task for '{title}'...")
        self.browser.push_task(task_fn)
        return future.result()

def upload_to_instagram_browser(video_path: Union[str, Path], caption: str) -> Optional[str]:
    """Core logic for Instagram upload via Selenium."""
    driver = None
    try:
        driver = get_browser()
        print("🌐 Navigating to Instagram...")
        driver.get("https://www.instagram.com/")
        time.sleep(5)

        # Check if logged in
        if "login" in driver.current_url.lower():
            print("❌ Instagram: Not logged in. Please log in to your Firefox profile first.")
            return None

        print("📤 Starting upload process...")
        # 1. Click Create button
        # Instagram's "Create" button often has aria-label="New post" or "Create"
        create_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "svg[aria-label='New post'], svg[aria-label='Create']"))
        )
        # Click the parent button of the SVG
        driver.execute_script("arguments[0].closest('div[role=\"button\"]').click();", create_btn)
        time.sleep(2)

        # 2. Upload file
        file_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )
        file_input.send_keys(str(Path(video_path).resolve()))
        print(f"📁 Video file selected: {video_path}")
        time.sleep(5)

        # 3. Click Next (Crop screen)
        next_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//div[text()='Next']"))
        )
        next_btn.click()
        time.sleep(2)

        # 4. Click Next (Edit screen)
        next_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//div[text()='Next']"))
        )
        next_btn.click()
        time.sleep(2)

        # 5. Set Caption
        print("📝 Setting caption...")
        caption_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[aria-label='Write a caption...']"))
        )
        caption_input.click()
        caption_input.send_keys(caption)
        time.sleep(2)

        # 6. Click Share
        print("🏁 Clicking Share...")
        share_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//div[text()='Share']"))
        )
        share_btn.click()
        
        # Wait for completion (Instagram shows a "Your post has been shared" message)
        print("⏳ Waiting for upload to complete...")
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Your post has been shared')]"))
        )
        
        print("✅ Instagram upload successful!")
        return "instagram_success_" + str(int(time.time()))

    except Exception as e:
        print(f"❌ Instagram upload failed: {e}")
        # Take a screenshot for debugging if it fails
        try:
            if driver:
                driver.save_screenshot("instagram_upload_error.png")
                print("📸 Error screenshot saved to instagram_upload_error.png")
        except:
            pass
        return None
    finally:
        if driver:
            driver.quit()
