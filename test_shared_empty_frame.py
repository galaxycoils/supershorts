import numpy as np
import threading
import time

def test_shared_state():
    empty_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    
    def make_frame(t):
        return empty_frame

    def thread_1():
        frame = make_frame(0)
        time.sleep(0.1)
        # Simulate MoviePy or some effect modifying the frame in-place
        frame[0, 0] = [255, 255, 255]
        
    def thread_2():
        frame = make_frame(0)
        # If thread_1 modified it, this will be [255, 255, 255]
        if frame[0, 0, 0] == 255:
            print("Race condition detected: Shared empty_frame was modified by another thread!")
        else:
            print("No race condition detected in this iteration.")

    t1 = threading.Thread(target=thread_1)
    t2 = threading.Thread(target=thread_2)
    
    t1.start()
    time.sleep(0.15) # Wait for t1 to modify
    t2.start()
    
    t1.join()
    t2.join()

if __name__ == "__main__":
    test_shared_state()
