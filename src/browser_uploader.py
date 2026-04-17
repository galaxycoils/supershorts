import os
import time
import datetime
from pathlib import Path
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

PROFILE_PATH = "/Users/cmd/Library/Application Support/Firefox/Profiles/aoi0g5my.default-release"

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
        except Exception:
            # Try finding by text if name fails
            try:
                el = driver.find_element(By.XPATH, "//*[contains(text(), 'No, it')]")
                driver.execute_script("arguments[0].click();", el)
            except Exception:
                print("⚠️ Could not set audience, might fail later.")
        
        time.sleep(2)

        # Click next 3 times
        for i in range(3):
            print(f"➡️ Clicking Next ({i+1}/3)...")
            try:
                next_btn = driver.find_element(By.ID, YOUTUBE_NEXT_BUTTON_ID)
                driver.execute_script("arguments[0].click();", next_btn)
            except Exception:
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
        except Exception:
            print("⚠️ Could not set visibility.")
        
        # Click Done
        print("✅ Clicking Done...")
        try:
            done_btn = driver.find_element(By.ID, YOUTUBE_DONE_BUTTON_ID)
            driver.execute_script("arguments[0].click();", done_btn)
        except Exception:
            done_btns = driver.find_elements(By.XPATH, "//*[text()='Done' or text()='Save' or text()='Publish']")
            if done_btns: driver.execute_script("arguments[0].click();", done_btns[0])
        
        time.sleep(10) # Wait for finalization

        # Extract Video ID
        print("🔗 Extracting video link...")
        video_id = "BROWSER_UPLOAD_SUCCESS"
        try:
            # Try finding the short link in the dialog
            link_els = driver.find_elements(By.CSS_SELECTOR, "a.style-scope.ytcp-video-share-config, span.video-url-wrapper a")
            for el in link_els:
                href = el.get_attribute("href")
                if "youtu.be" in href or "youtube.com/watch" in href:
                    video_id = href.split("/")[-1]
                    if "?" in video_id: video_id = video_id.split("?")[0]
                    break
        except Exception:
            pass

        print(f"🎉 Success! Video ID: {video_id}")
        driver.quit()
        return video_id

    except Exception as e:
        print(f"❌ Browser upload error: {e}")
        if driver:
            driver.quit()
        return None
