<div align="center">

# 🌙 SuperShorts

### *AI-powered short-form video engine — generate, render, and upload on autopilot.*

[![CI Pipeline](https://github.com/galaxycoils/supershorts/actions/workflows/ci.yml/badge.svg)](https://github.com/galaxycoils/supershorts/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-8B5CF6.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-4C7DFF.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-1E1E2E.svg)](https://github.com/astral-sh/ruff)
[![Last commit](https://img.shields.io/github/last-commit/galaxycoils/supershorts?color=8B5CF6)](https://github.com/galaxycoils/supershorts/commits/main)

<img src="https://raw.githubusercontent.com/galaxycoils/supershorts/main/uiexample/IMG_1469.JPG" alt="SuperShorts dashboard" width="820" />

</div>

---

## 📚 Table of Contents

- [Why SuperShorts](#-why-supershorts)
- [Core Architecture](#-core-architecture)
- [Key Features](#-key-features)
- [Screenshots](#-screenshots)
- [Installation & Setup](#-installation--setup)
- [Running the Dashboard](#-running-the-dashboard)
- [Project Structure](#-project-structure)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Why SuperShorts

SuperShorts is a production-grade, AI-powered video engine designed to generate, render, and upload viral content (YouTube Shorts, TikToks, Reels) on total autopilot. Leveraging local LLMs via Ollama and high-fidelity TTS via Piper, it provides a cost-free, high-performance pipeline for modern content creators.

> **The ultimate "RotGen" clone for automated short-form content creation.**

---

## 🏗 Core Architecture

### Frontend: The Command Center
Built for performance and responsiveness, the UI has been refactored into a componentized architecture:
- **Vanilla JS Engine**: Optimized state management for real-time subprocess monitoring and job tracking.
- **Tranquil Eclipse Aesthetic**: Deep-indigo surfaces, soft lunar glow, and a refined purple-to-blue gradient — calmer than neon, sharper than flat.
- **Mobile-First**: Fully responsive collapsible sidebar and multi-step production modals using CSS Grid and Flexbox.
- **Real-time Monitoring**: Streaming output via Server-Sent Events (SSE) for zero-latency feedback during renders.

### Backend: The Production Pipeline
A robust Python-based microservice architecture:
- **Flask API**: Orchestrates production jobs, asset management, and system health telemetry.
- **Multi-LLM Integration**: Fully local LLM inference via **Ollama** or **LM Studio** (OpenAI-compatible) for script generation and topic brainstorming.
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

## 📸 Screenshots

<table>
  <tr>
    <td align="center" width="33%">
      <img src="https://raw.githubusercontent.com/galaxycoils/supershorts/main/uiexample/IMG_1469.JPG" alt="Command Center" /><br/>
      <sub><b>Command Center</b><br/>KPIs &amp; live job telemetry</sub>
    </td>
    <td align="center" width="33%">
      <img src="https://raw.githubusercontent.com/galaxycoils/supershorts/main/uiexample/IMG_1471.JPG" alt="Production Modal" /><br/>
      <sub><b>Production Modal</b><br/>3-step identity → concept → precision</sub>
    </td>
    <td align="center" width="33%">
      <img src="https://raw.githubusercontent.com/galaxycoils/supershorts/main/uiexample/IMG_1473.JPG" alt="Gallery" /><br/>
      <sub><b>Gallery</b><br/>Browse rendered shorts</sub>
    </td>
  </tr>
</table>

---

## 🛠 Installation & Setup

### 1. Prerequisites
- **Python 3.10+**
- **Firefox** (required for the automated uploader)
- **Local LLM**: [Ollama](https://ollama.com) or [LM Studio](https://lmstudio.ai).
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

| Version | Milestone                                  | Status |
|--------:|--------------------------------------------|:------:|
| v3.5.0  | Componentized UI & RotGen Aesthetic        | ✅ |
| v3.6.0  | Multi-LLM Provider Support (LM Studio)     | ✅ |
| v3.7.0  | Multi-platform uploading (TikTok, Instagram) | 🚧 |
| v3.8.0  | Cloud-synced asset library                 | 🔭 |
| v3.9.0  | Advanced AI-driven B-Roll selection        | 🔭 |

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
Distributed under the MIT License. See [`LICENSE`](LICENSE) for more information.

<div align="center">
<sub>Built with ☕ by the SuperShorts team — <i>AI for Developers</i>.</sub>
</div>
