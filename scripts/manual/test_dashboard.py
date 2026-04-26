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
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.get("http://localhost:5050")
    print(f"Page title: {driver.title}")
    
    # Wait for mode-grid
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.ID, "mode-grid")))
    
    modes = driver.find_elements(By.CLASS_NAME, "mode-card")
    print(f"Found {len(modes)} modes")
    
    results = []
    
    for i in range(len(modes)):
        # Re-find modes because of DOM refreshes
        modes = driver.find_elements(By.CLASS_NAME, "mode-card")
        mode = modes[i]
        mode_name = mode.find_element(By.CLASS_NAME, "mode-name").text
        print(f"Testing mode: {mode_name}")
        
        mode.click()
        time.sleep(1)
        
        # Check modal
        modal = driver.find_element(By.ID, "modal-overlay")
        if modal.is_displayed():
            print(f"Modal opened for {mode_name}")
            
            # Select first character if step 1
            step_indicator = driver.find_element(By.ID, "modal-steps-indicator").text
            if "STEP 1" in step_indicator:
                chars = driver.find_elements(By.CLASS_NAME, "char-card")
                if chars:
                    chars[0].click()
                    time.sleep(0.5)
            
            # Click CONTINUE
            next_btn = driver.find_element(By.ID, "btn-modal-next")
            next_btn.click()
            time.sleep(1)
            
            step_indicator = driver.find_element(By.ID, "modal-steps-indicator").text
            print(f"Moved to {step_indicator}")
            
            # Check for blank screen or obvious errors in modal body
            modal_body = driver.find_element(By.ID, "modal-body")
            if not modal_body.text.strip() and not modal_body.find_elements(By.TAG_NAME, "div"):
                results.append({"mode": mode_name, "error": "Blank screen in STEP 2"})
            
            # Check console logs
            logs = driver.get_log("browser")
            for log in logs:
                if log['level'] == 'SEVERE':
                    results.append({"mode": mode_name, "error": f"Console Error: {log['message']}"})
            
            # Special case for TCM: Trigger Dry Run
            if "tcm" in mode_name.lower():
                print("Triggering TCM Dry Run...")
                # TCM STEP 2 has some fields, click CONTINUE again to go to STEP 3
                next_btn = driver.find_element(By.ID, "btn-modal-next")
                next_btn.click()
                time.sleep(1)
                
                step_indicator = driver.find_element(By.ID, "modal-steps-indicator").text
                print(f"Moved to {step_indicator}")
                
                # In STEP 3, select Dry Run
                dry_btn = driver.find_element(By.ID, "btn-dry")
                dry_btn.click()
                time.sleep(0.5)
                
                # Launch
                next_btn = driver.find_element(By.ID, "btn-modal-next")
                next_btn.click()
                print("Launched TCM Dry Run")
                time.sleep(2)
                
                # Check terminal for ReferenceError or output
                terminal = driver.find_element(By.ID, "terminal")
                print(f"Terminal output: {terminal.text}")
                if "ReferenceError" in terminal.text:
                    results.append({"mode": mode_name, "error": f"Crash found: {terminal.text}"})

            # Close modal for next iteration
            close_btn = driver.find_element(By.CLASS_NAME, "modal-close-btn")
            close_btn.click()
            time.sleep(0.5)
        else:
            results.append({"mode": mode_name, "error": "Modal did not open"})
            
    driver.quit()
    
    with open("qa_results.json", "w") as f:
        json.dump(results, f)

if __name__ == "__main__":
    test()
