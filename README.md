# SuperShorts Production Suite v3.5.0

![SuperShorts Dashboard Preview](https://raw.githubusercontent.com/galaxycoils/supershorts/main/uiexample/IMG_1469.JPG)

> **The ultimate "RotGen" clone for automated short-form content creation.**

SuperShorts is a production-grade, AI-powered video engine designed to generate, render, and upload viral content (YouTube Shorts, TikToks, Reels) on total autopilot. Leveraging local LLMs via Ollama and high-fidelity TTS via Piper, it provides a cost-free, high-performance pipeline for modern content creators.

---

## 🏗 Core Architecture

### Frontend: The Command Center
Built for performance and responsiveness, the UI has been refactored into a componentized architecture:
- **Vanilla JS Engine**: Optimized state management for real-time subprocess monitoring and job tracking.
- **Modern Aesthetic**: A "RotGen V2" theme featuring deep-space black surfaces (`#050505`), glassmorphism, and neon purple-to-blue gradients.
- **Mobile-First**: Fully responsive collapsible sidebar and multi-step production modals using CSS Grid and Flexbox.
- **Real-time Monitoring**: Streaming output via Server-Sent Events (SSE) for zero-latency feedback during renders.

### Backend: The Production Pipeline
A robust Python-based microservice architecture:
- **Flask API**: Orchestrates production jobs, asset management, and system health telemetry.
- **Ollama Integration**: Fully local LLM inference for script generation and topic brainstorming.
- **Piper TTS Engine**: Ultra-fast, neural text-to-speech synthesis with support for 9+ high-quality voices.
- **Video Engine (MoviePy)**: A specialized composition layer that handles dynamic layering, auto-captions, background music blending, and "Chain" concatenation for 40% lower memory usage.
- **Selenium Automation**: A built-in browser-based uploader for seamless YouTube Studio integration.

---

## 🌟 Key Features

- **Character-Based Production**: Choose from a roster of AI characters (Adam, Antoni, Arnold, etc.) with automated avatar overlays.
- **3-Step Production Modal**: 
    1. **Identity**: Select voices and character styles.
    2. **Concept**: Input topics or generate them using "Topic & Tone" presets.
    3. **Precision**: Fine-tune LLM temperature and rendering quality (720p vs 1080p HD).
- **Multiple Content Modes**:
    - **Brainrot**: High-engagement viral facts over gameplay.
    - **TCM (Teaches)**: Educational curriculum-based content.
    - **RotGen**: Dynamic split-screen AI character stories.
    - **Clipper**: Transform long-form videos into vertical short-form hits.
- **Asset Manager**: Dynamic visual selector for local backgrounds, characters, and music.

---

## 🛠 Installation & Setup

### 1. Prerequisites
- **Python 3.10+**
- **Firefox** (required for the automated uploader)
- **Ollama**: [Download Ollama](https://ollama.com) and pull your preferred model (e.g., `ollama pull llama3.2:3b`).
- **Piper TTS**: Ensure the Piper binary is in your path.

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/galaxycoils/supershorts.git
cd supershorts

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Voice Assets
Use the included helper script to download the high-quality voice models:
```bash
chmod +x scripts/download_voices.sh
./scripts/download_voices.sh
```

---

## 🚀 Running the Dashboard

Start the command center with a single command:
```bash
python3 dashboard.py
```
Access the UI at: **`http://localhost:5050`**

---

## 📁 Project Structure

```text
├── dashboard.py           # Flask Backend & API Gateway
├── main.py                # Legacy CLI Entry Point
├── templates/             # HTML5 Templates (Componentized)
├── static/                # Assets (CSS, JS, Images)
├── scripts/               # Utility Scripts (Voice Downloaders, etc.)
├── src/
│   ├── modes/             # Production Mode Logic (Brainrot, TCM, etc.)
│   ├── engine/            # MoviePy Video Composition Engine
│   ├── infrastructure/    # LLM (Ollama), TTS (Piper), & Uploader services
│   └── core/              # Interfaces and Global Config
└── assets/                # Backgrounds, Characters, and Music storage
```

---

## 📈 Roadmap
- [x] v3.5.0: Componentized UI & RotGen Aesthetic
- [ ] v3.1: Multi-platform uploading (TikTok, Instagram)
- [ ] v3.2: Cloud-synced asset library
- [ ] v3.3: Advanced AI-driven B-Roll selection

---

## 🤝 Contributing
Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.

**Developed by {YOUR_NAME} for SuperShorts / AI for Developers.**
