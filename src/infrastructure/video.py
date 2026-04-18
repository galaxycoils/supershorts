import random
import requests
from pathlib import Path
from PIL import Image
from src.core.config import (
    BACKGROUNDS_PATH, GAMEPLAY_PATH, VIRAL_GAMEPLAY_PATH, 
    PEXELS_API_KEY, PEXELS_CACHE_DIR
)

def get_local_background(lesson_title: str, video_type: str) -> Image.Image:
    """Fixed for modern Pillow (no more ANTIALIAS error)."""
    if not BACKGROUNDS_PATH.exists() or len(list(BACKGROUNDS_PATH.glob("*.*"))) < 1:
        print("⚠️ Backgrounds folder is low/empty")
        w, h = (1920, 1080) if video_type == 'long' else (1080, 1920)
        return Image.new('RGBA', (w, h), color=(12, 17, 29))

    images = list(BACKGROUNDS_PATH.glob("*.jpg")) + list(BACKGROUNDS_PATH.glob("*.png")) + list(BACKGROUNDS_PATH.glob("*.jpeg"))
    if not images:
        w, h = (1920, 1080) if video_type == 'long' else (1080, 1920)
        return Image.new('RGBA', (w, h), color=(12, 17, 29))

    keywords = ["ai", "neural", "tech", "code", "abstract", "future", "data", "brain", "learning"]
    title_lower = lesson_title.lower()
    scored = [(sum(1 for kw in keywords if kw in title_lower or kw in img.name.lower()), img) for img in images]
    scored.sort(reverse=True, key=lambda x: x[0])
    chosen = scored[0][1] if scored[0][0] > 0 else random.choice(images)

    print(f"🎨 Using local background: {chosen.name}")
    img = Image.open(chosen).convert("RGBA")

    # Modern Pillow resizing (no ANTIALIAS)
    width, height = (1920, 1080) if video_type == 'long' else (1080, 1920)
    img = img.resize((width, height), Image.Resampling.LANCZOS)
    return img

def get_local_gameplay(video_type: str) -> str:
    clips = list(GAMEPLAY_PATH.glob("*.mp4"))
    if clips:
        return str(random.choice(clips))
    return None

def get_local_viral_gameplay() -> str | None:
    """NEW: Picks high-motion Subway Surfers / Minecraft style clips"""
    if not VIRAL_GAMEPLAY_PATH.exists():
        return None
    clips = list(VIRAL_GAMEPLAY_PATH.glob("*.mp4"))
    if not clips:
        return None
    chosen = random.choice(clips)
    print(f"🔥 Viral Gameplay background: {chosen.name}")
    return str(chosen)

def get_relevant_pexels_video(query: str, video_type: str) -> str:
    # clean query — guard empty string
    parts = query.split()
    if not parts:
        return None
    query = parts[0]
    headers = {"Authorization": PEXELS_API_KEY}
    orientation = "landscape" if video_type == 'long' else "portrait"
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=5&orientation={orientation}"
    try:
        res = requests.get(url, headers=headers, timeout=15)
        data = res.json()
        if data.get("videos"):
            video_url = None
            for v in data["videos"]:
                for f in v.get("video_files", []):
                    if f.get("quality") == "hd":
                        video_url = f["link"]
                        break
                if video_url:
                    video_id = v["id"]
                    break
            
            if not video_url:
                video_url = data["videos"][0]["video_files"][0]["link"]
                video_id = data["videos"][0]["id"]
            
            video_path = PEXELS_CACHE_DIR / f"{video_id}.mp4"
            if not video_path.exists():
                print(f"⬇️ Downloading Pexels video for '{query}'...")
                r = requests.get(video_url, stream=True, timeout=30)
                with open(video_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
            return str(video_path)
    except Exception as e:
        print(f"⚠️ Pexels error: {e}")
    return None
