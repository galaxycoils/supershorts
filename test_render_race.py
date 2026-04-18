import threading
from src.utils.captions import render_subtitle_frame

def worker(thread_id):
    for i in range(50):
        text = f"Thread {thread_id} frame {i} with some more text to trigger scaling and wrapping logic."
        frame = render_subtitle_frame(text, 1920)
        assert frame is not None

threads = []
for i in range(20):
    t = threading.Thread(target=worker, args=(i,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("Concurrent render_subtitle_frame test completed.")
