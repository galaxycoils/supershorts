import numpy as np
import threading
import time
from src.utils.captions import add_subtitle_overlay
from moviepy.editor import ColorClip

def test_concurrent_make_frame():
    # Create a dummy base clip
    duration = 10.0
    base_clip = ColorClip(size=(1920, 1080), color=(255, 0, 0), duration=duration)
    
    script = "This is a test script with multiple words to ensure we have several subtitle chunks for testing race conditions in the generator."
    
    # Add subtitle overlay
    video_with_subs = add_subtitle_overlay(base_clip, script, 'long')
    
    # The subtitle clip is the second one in CompositeVideoClip
    sub_clip = video_with_subs.clips[1]
    
    def worker(thread_id):
        for _ in range(100):
            t = np.random.uniform(0, duration)
            try:
                frame = sub_clip.make_frame(t)
                assert frame is not None
                assert isinstance(frame, np.ndarray)
            except Exception as e:
                print(f"Thread {thread_id} error at t={t}: {e}")

    threads = []
    for i in range(10):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()

    print("Concurrent make_frame test completed.")

if __name__ == "__main__":
    test_concurrent_make_frame()
