import os
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.get("http://localhost:5050")
    print(f"Page title: {driver.title}")
    
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.ID, "mode-grid")))
    
    modes = driver.find_elements(By.CLASS_NAME, "mode-card")
    mode_ids = [m.get_attribute("onclick").split("'")[1] for m in modes]
    print(f"Found {len(mode_ids)} mode IDs: {mode_ids}")
    
    all_results = []
    
    for mode_id in mode_ids:
        print(f"\n--- Testing mode: {mode_id} ---")
        try:
            # Navigate back to main productions if needed
            nav_productions = driver.find_element(By.XPATH, "//button[contains(., 'Productions')]")
            driver.execute_script("arguments[0].click();", nav_productions)
            time.sleep(0.5)
            
            # Find the card again
            card = driver.find_element(By.XPATH, f"//div[@onclick=\"openModal('{mode_id}')\"]")
            driver.execute_script("arguments[0].click();", card)
            time.sleep(1)
            
            # Modal Step 1
            print("Step 1 check...")
            wait.until(EC.visibility_of_element_located((By.ID, "modal-overlay")))
            
            chars = driver.find_elements(By.CLASS_NAME, "char-card")
            if chars:
                driver.execute_script("arguments[0].click();", chars[0])
                time.sleep(0.5)
            
            next_btn = driver.find_element(By.ID, "btn-modal-next")
            driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(1)
            
            # Modal Step 2
            print("Step 2 check...")
            indicator = driver.find_element(By.ID, "modal-steps-indicator").text
            if "STEP 2" not in indicator:
                all_results.append({"mode": mode_id, "error": f"Failed to reach STEP 2. Currently at {indicator}"})
            
            modal_body = driver.find_element(By.ID, "modal-body")
            if not modal_body.text.strip() and not modal_body.find_elements(By.TAG_NAME, "div"):
                all_results.append({"mode": mode_id, "error": "Blank screen in STEP 2"})
            
            # Check console
            for entry in driver.get_log('browser'):
                if entry['level'] == 'SEVERE':
                    print(f"CONSOLE ERROR ({mode_id}): {entry['message']}")
                    all_results.append({"mode": mode_id, "error": f"Console SEVERE: {entry['message']}"})
            
            # For TCM, proceed to launch dry run
            if mode_id == 'tcm':
                print("Proceeding to TCM Dry Run Step 3...")
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(1)
                
                print("Step 3 check...")
                dry_btn = driver.find_element(By.ID, "btn-dry")
                driver.execute_script("arguments[0].click();", dry_btn)
                time.sleep(0.5)
                
                print("Launching...")
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(2)
                
                # Check for crash in console OR terminal
                terminal = driver.find_element(By.ID, "terminal")
                term_text = terminal.text
                print(f"Terminal Output Snippet: {term_text[-200:]}")
                
                for entry in driver.get_log('browser'):
                    if entry['level'] == 'SEVERE':
                        print(f"CONSOLE ERROR (TCM Launch): {entry['message']}")
                        all_results.append({"mode": mode_id, "error": f"Crash found: {entry['message']}"})
                
                if "ReferenceError" in term_text:
                    all_results.append({"mode": mode_id, "error": f"Terminal ReferenceError: {term_text}"})

            # Close modal
            close_btn = driver.find_element(By.CLASS_NAME, "modal-close-btn")
            driver.execute_script("arguments[0].click();", close_btn)
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Exception testing {mode_id}: {str(e)}")
            all_results.append({"mode": mode_id, "error": f"Exception: {str(e)}"})

    driver.quit()
    
    with open("qa_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

if __name__ == "__main__":
    test()
