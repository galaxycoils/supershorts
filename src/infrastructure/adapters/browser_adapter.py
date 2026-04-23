import queue
import threading
from typing import Optional, Any, List, Callable
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

class BrowserAdapter:
    """Gateway adapter for browser automation (Selenium)."""
    
    def __init__(self, driver: Optional[webdriver.Firefox] = None):
        self._driver = driver
        self.queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def _worker(self):
        """Worker thread to process tasks sequentially."""
        while True:
            task_fn = self.queue.get()
            try:
                task_fn()
            except Exception as e:
                print(f"BrowserAdapter task error: {e}")
            finally:
                self.queue.task_done()

    def push_task(self, task_fn: Callable):
        """Push a callable task to the background queue."""
        self.queue.put(task_fn)

    @property
    def driver(self) -> webdriver.Firefox:
        if not self._driver:
            raise RuntimeError("Browser driver not initialized.")
        return self._driver

    def set_driver(self, driver: webdriver.Firefox):
        self._driver = driver

    def get(self, url: str):
        self.driver.get(url)

    def find_element(self, by: By, value: str):
        return self.driver.find_element(by, value)

    def find_elements(self, by: By, value: str):
        return self.driver.find_elements(by, value)

    def wait_for_element(self, by: By, value: str, timeout: int = 20):
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.presence_of_element_located((by, value)))

    def wait_for_all_elements(self, by: By, value: str, timeout: int = 20):
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.presence_of_all_elements_located((by, value)))

    def wait_for_clickable(self, by: By, value: str, timeout: int = 20):
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.element_to_be_clickable((by, value)))

    def execute_script(self, script: str, *args):
        return self.driver.execute_script(script, *args)

    def quit(self):
        if self._driver:
            self._driver.quit()
            self._driver = None
            
    def current_url(self) -> str:
        return self.driver.current_url
