import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Use venv python if present
_VENV_PY = PROJECT_ROOT / "venv" / "bin" / "python3"
PYTHON = str(_VENV_PY) if _VENV_PY.exists() else sys.executable

def run_dry_check(mode):
    env = os.environ.copy()
    env["OLLAMA_MODEL"] = "qwen2.5-coder:3b"
    env["YOUR_NAME"] = "Tester"
    env["CUSTOM_BG"] = "test_bg.mp4"
    env["CUSTOM_CHAR"] = "test_char.png"
    
    print(f"\n" + "="*50)
    print(f"🚀 Launching {mode} dry run...")
    print(f"   Env overrides: CUSTOM_BG={env.get('CUSTOM_BG')}, CUSTOM_CHAR={env.get('CUSTOM_CHAR')}")
    print("="*50)
    
    if mode == "tcm":
        code = "from src.modes.tcm_educational import run_tcm_mode; run_tcm_mode(dry_run=True)"
    elif mode == "brainrot":
        code = "from src.modes.brainrot import run_brainrot_pipeline; run_brainrot_pipeline(1, dry_run=True)"
    elif mode == "rotgen":
        code = "from src.modes.rotgen import run_rotgen_pipeline; run_rotgen_pipeline(1, dry_run=True)"
    else:
        return
        
    cmd = [PYTHON, "-c", f"import sys; sys.path.insert(0,'{PROJECT_ROOT}'); {code}"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, cwd=str(PROJECT_ROOT), env=env)
    
    # Feed stdin to handle prompts
    try:
        # For TCM: 
        # y (use existing plan) OR TCM Essentials (topic)
        # 1 (count)
        # For others, mostly just \n
        proc.stdin.write(b"y\n1\n\n\n\n\n") 
        proc.stdin.close()
    except OSError:
        pass
        
    for line in iter(proc.stdout.readline, b""):
        print(line.decode().rstrip())
    proc.wait()
    print(f"✅ {mode} finished with exit code {proc.returncode}")

if __name__ == '__main__':
    run_dry_check("brainrot")
    run_dry_check("rotgen")
    run_dry_check("tcm")
