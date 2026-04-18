import sys
import os

try:
    from src.generator import (
        generate_curriculum,
        generate_lesson_content,
        text_to_speech,
        generate_visuals,
        compose_video,
        YOUR_NAME,
        start_viral_gameplay_mode,
        start_tutorial_generation,
        generate_youtube_content_package,
    )
    print("✓ src.generator imports successful")
except ImportError as e:
    print(f"✗ src.generator imports failed: {e}")

# Check other imports in main.py
modules_to_check = [
    'src.brainrot',
    'src.rotgen',
    'src.learning',
    'src.ideagenerator',
    'src.browser_uploader',
    'src.clipper_mode',
    'src.tcm_mode'
]

for mod in modules_to_check:
    try:
        __import__(mod)
        print(f"✓ {mod} import successful")
    except ImportError as e:
        print(f"✗ {mod} import failed: {e}")

