import requests
import json
import time

BASE_URL = "http://localhost:5050"
MODES = ["educational", "brainrot", "rotgen", "tcm", "tutorial", "viral", "ideas", "learning", "package", "clipper"]

def test_mode(mode):
    print(f"Testing mode: {mode}")
    try:
        res = requests.post(f"{BASE_URL}/api/run/{mode}", json={
            "count": 1,
            "dry_run": "y",
            "voice": "en_US-ryan-high",
            "stdin_input": "Test Topic\nTest Extra\n1\n"
        })
        if res.status_code != 200:
            print(f"Error starting {mode}: {res.text}")
            return
        
        job_id = res.json().get("job_id")
        print(f"Job ID: {job_id}")
        
        # Stream output
        output = []
        with requests.get(f"{BASE_URL}/api/stream/{job_id}", stream=True) as r:
            for line in r.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith("data: "):
                        data = decoded[6:]
                        if data == "[DONE]":
                            break
                        output.append(data)
        
        full_output = "\n".join(output)
        if "Traceback" in full_output or "Error" in full_output.upper():
            print(f"Possible error in {mode}:")
            print(full_output)
        else:
            print(f"Mode {mode} finished successfully.")
            
    except Exception as e:
        print(f"Exception testing {mode}: {e}")

if __name__ == "__main__":
    for m in MODES:
        test_mode(m)
        time.sleep(2)
