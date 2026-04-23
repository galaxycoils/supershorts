# Money Printer V2 - SuperShorts Production Suite

![SuperShorts Dashboard](https://raw.githubusercontent.com/SuperShorts/money-printer-v2/main/uiexample/IMG_1469.JPG)

Money Printer V2 is an automated, AI-powered video production suite. It generates, renders, and uploads YouTube Shorts and TikToks on autopilot.

## Features
- **RotGen V2 Aesthetic:** Beautiful, dark-themed dashboard inspired by top-tier SaaS platforms.
- **Multiple Modes:** TCM (Traditional Chinese Medicine), Brainrot (Viral Facts), RotGen (Character-based AI), Tutorial, Clipper, and more.
- **Advanced Control:** Total control over LLMs, Piper voices, Backgrounds, and Characters directly from the UI.
- **Ollama Integration:** Fully local LLM inference for generating scripts and content.
- **Smart Pipeline:** MoviePy-based engine creates dynamic videos with auto-captions and background music.

## Installation

### Prerequisites
- Python 3.10+
- Firefox (for browser-based uploading)
- Ollama installed locally (`qwen2.5-coder:3b`, `llama3.2`, etc.)
- Piper TTS models downloaded into `~/.local/share/piper-tts/voices/`

### Setup
```bash
git clone https://github.com/YourUser/money-printer-v2.git
cd money-printer-v2
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running the Dashboard
```bash
python3 dashboard.py
```
Then visit `http://localhost:5050` in your browser.

## Directory Structure
- `assets/`: Place your backgrounds, characters, and music here.
- `src/modes/`: Different video generation modes.
- `src/engine/`: MoviePy video compilation engine.
- `dashboard.py`: The main Flask web server and UI.

## Adding Voices
The dashboard includes options for multiple voices (Adam, Antoni, Amy, Arnold, etc.). To use them, ensure the corresponding Piper ONNX files are placed in your Piper voices directory.

## Contributing
Pull requests are welcome. Make sure to run tests before submitting.
