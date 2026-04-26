import wave
import os
from pathlib import Path
from piper.voice import PiperVoice

VOICES_DIR = Path.home() / ".local/share/piper-tts/voices"
TEST_TEXT = "Viral AI voice system check. Local and neural. Let's go viral."

VOICES = [
    "en_US-ryan-high",
    "en_US-lessac-high",
    "en_US-amy-medium",
    "en_GB-alan-medium",
    "en_US-hfc_female-medium",
    "en_US-joe-medium",
    "en_US-kristin-medium"
]

def test_voice(name):
    model_path = VOICES_DIR / f"{name}.onnx"
    output_path = Path(f"test_voice_{name}.wav")
    
    if not model_path.exists():
        print(f"➖ Voice {name} not downloaded, skipping.")
        return False
        
    try:
        voice = PiperVoice.load(str(model_path))
        with wave.open(str(output_path), 'wb') as wf:
            voice.synthesize_wav(TEST_TEXT, wf)
        print(f"✅ Voice {name} synthesized to {output_path}")
        return True
    except Exception as e:
        print(f"❌ Voice {name} failed: {e}")
        return False

if __name__ == "__main__":
    print(f"Testing {len(VOICES)} viral voices...")
    for v in VOICES:
        test_voice(v)
