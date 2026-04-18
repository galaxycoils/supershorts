import os
import sys
import subprocess
from pathlib import Path
from src.core.config import FONT_FILE
from src.utils.text import strip_emojis, strip_markdown

_PIPER_VOICES_DIR = Path.home() / ".local/share/piper-tts/voices"
_PIPER_VOICE_NAMES = ("en_US-ryan-high", "en_US-lessac-high", "en-us-lessac-medium")

def text_to_speech(text: str, output_path: Path) -> Path:
    """
    Natural TTS — 3-tier fallback:
    1. Piper neural (Python API)
    2. macOS `say` with Alex voice
    3. pyttsx3 (last resort)
    """
    text = strip_markdown(strip_emojis(text))
    print(f"🗣️ TTS → {Path(output_path).stem} ({len(text)} chars)...")
    wav_path = output_path.with_suffix('.wav')

    # 1 — Piper Python API
    try:
        import wave
        from piper.voice import PiperVoice
        for model_name in _PIPER_VOICE_NAMES:
            model_path = _PIPER_VOICES_DIR / f"{model_name}.onnx"
            if model_path.exists():
                voice = PiperVoice.load(str(model_path))
                with wave.open(str(wav_path), 'wb') as wf:
                    voice.synthesize_wav(text, wf)
                print(f"✅ Piper ({model_name}) → {wav_path.name}")
                return wav_path
        raise FileNotFoundError(f"No Piper voice in {_PIPER_VOICES_DIR}")
    except Exception as e:
        print(f"⚠️ Piper Python API failed ({e}), trying macOS say...")

    # 2 — macOS `say` command
    try:
        aiff_path = output_path.with_suffix('.aiff')
        subprocess.run(
            ['say', '-v', 'Alex', '-r', '170', '-o', str(aiff_path), text],
            check=True, capture_output=True
        )
        subprocess.run(
            ['ffmpeg', '-y', '-loglevel', 'error',
             '-i', str(aiff_path), '-ar', '22050', '-ac', '1', str(wav_path)],
            check=True, capture_output=True
        )
        if aiff_path.exists():
            aiff_path.unlink()
        print(f"✅ macOS say (Alex) → {wav_path.name}")
        return wav_path
    except Exception as e:
        print(f"⚠️ macOS say failed ({e}), using pyttsx3...")

    # 3 — pyttsx3 last resort
    import pyttsx3
    mp3_path = output_path.with_suffix('.mp3')
    engine = pyttsx3.init()
    engine.save_to_file(text, str(mp3_path))
    engine.runAndWait()
    
    # convert mp3 to wav for consistency
    subprocess.run(
        ['ffmpeg', '-y', '-loglevel', 'error', '-i', str(mp3_path), str(wav_path)],
        check=True, capture_output=True
    )
    if mp3_path.exists():
        mp3_path.unlink()
    print(f"✅ pyttsx3 → {wav_path.name}")
    return wav_path
