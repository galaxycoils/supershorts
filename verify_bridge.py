import sys
import os

print("--- SuperShorts Architecture Bridge Verification ---")

try:
    from src import generator
    print("✓ src.generator package import successful")
    
    # Check key orchestration re-exports
    entry_points = [
        'run_tcm_mode',
        'run_brainrot_pipeline',
        'run_rotgen_pipeline',
        'start_tutorial_generation',
        'run_video_clipper'
    ]
    for ep in entry_points:
        if hasattr(generator, ep):
            print(f"  ✓ {ep} re-exported")
        else:
            print(f"  ✗ {ep} MISSING from generator")
            
except ImportError as e:
    print(f"✗ src.generator import failed: {e}")

# Check internal modular structure
modules_to_check = [
    'src.core.base_mode',
    'src.infrastructure.llm',
    'src.infrastructure.tts',
    'src.infrastructure.browser_uploader',
    'src.engine.video_engine',
    'src.modes.tcm_educational',
    'src.modes.brainrot',
    'src.modes.tutorial'
]

print("\n--- Modular Structure Check ---")
for mod in modules_to_check:
    try:
        __import__(mod)
        print(f"✓ {mod} import successful")
    except ImportError as e:
        print(f"✗ {mod} import failed: {e}")

print("\nVerification Complete.")
