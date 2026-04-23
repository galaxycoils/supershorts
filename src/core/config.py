import os
import platform
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
ASSETS_PATH = PROJECT_ROOT / "assets"
OUTPUT_DIR = PROJECT_ROOT / "output"
BACKGROUNDS_PATH = ASSETS_PATH / "backgrounds"
GAMEPLAY_PATH = ASSETS_PATH / "gameplay"
VIRAL_GAMEPLAY_PATH = ASSETS_PATH / "viral_gameplay"
FONT_FILE = ASSETS_PATH / "fonts" / "arial.ttf"
BACKGROUND_MUSIC_PATH = ASSETS_PATH / "music" / "background.mp3"
PEXELS_CACHE_DIR = PROJECT_ROOT / "assets" / "pexels"

# API Keys
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

# LLM Config
OLLAMA_MODEL = "qwen2.5-coder:3b"
OLLAMA_TIMEOUT = 120

# User Info
YOUR_NAME = os.environ.get("YOUR_NAME", "SuperShorts")

# Video render tuning
_default_low_memory = platform.system() == "Darwin" and platform.machine() == "arm64"
LOW_MEMORY_MODE = os.environ.get("LOW_MEMORY_MODE", str(_default_low_memory)).lower() in {"1", "true", "yes", "on"}
VIDEO_THREADS = max(1, int(os.environ.get("VIDEO_THREADS", "2")))
VIDEO_FPS = max(12, int(os.environ.get("VIDEO_FPS", "24")))
LONG_VIDEO_SIZE = (
    1280 if LOW_MEMORY_MODE else 1920,
    720 if LOW_MEMORY_MODE else 1080,
)
SHORT_VIDEO_SIZE = (
    720 if LOW_MEMORY_MODE else 1080,
    1280 if LOW_MEMORY_MODE else 1920,
)

# Topics
TUTORIAL_TOPICS = [
    "Build Your First AI Agent with Python",
    "Local LLMs with Ollama – Complete Beginner Guide",
    "Vector Databases Explained Simply for Developers",
    "LangChain vs LangGraph – Which One Should You Use",
    "Prompt Engineering Masterclass – From Beginner to Pro",
    "Fine-Tuning LLMs on Your Own Data – Step by Step",
    "RAG (Retrieval-Augmented Generation) Explained and Built",
    "How to Run DeepSeek Locally on Any Machine",
    "Building Multi-Agent AI Systems from Scratch",
    "Function Calling and Tool Use in Modern LLMs",
    "Embeddings and Semantic Search – How They Really Work",
    "Build a Fully Local AI Coding Assistant",
    "AI Safety and Alignment – What Every Developer Must Know",
    "Transformer Architecture Explained Without the Math",
    "The Complete Guide to Open-Source AI Models in 2026",
]

CONTENT_PACKAGE_TOPICS = [
    "The Science of Habit Formation",
    "Why Sleep Deprivation Destroys Productivity",
    "How Top Performers Structure Their Day",
    "The Hidden Psychology of Motivation",
    "Why Most People Never Reach Their Goals",
    "The Neuroscience of Deep Work",
    "How to Learn Anything 10x Faster",
    "The Truth About Multitasking",
    "Why Your Environment Controls Your Behaviour",
    "The Simple System That Beats Every To-Do App",
    "What High Achievers Do in the First Hour of Their Day",
    "The Real Reason You Procrastinate (And How to Stop)",
]

# Ensure critical dirs exist
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
PEXELS_CACHE_DIR.mkdir(exist_ok=True, parents=True)

@dataclass
class VideoOptions:
    video_type: str  # 'long' or 'short'
    lesson_title: str
    is_tutorial: bool = False
    force_viral_bg: bool = False
    script: Optional[str] = None
    bg_query: Optional[str] = None
    threads: int = VIDEO_THREADS
    fps: int = VIDEO_FPS
