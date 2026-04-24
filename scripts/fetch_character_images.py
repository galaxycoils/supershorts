#!/usr/bin/env python3
"""Fetch character images from Pexels Photo API. Falls back to PIL-generated avatars."""
import os
import sys
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).parent.parent
STATIC_IMG = PROJECT_ROOT / "static" / "img"

CHARACTERS = [
    {"filename": "peter.png",         "query": "professional architect male portrait",      "initial": "A", "color": (79, 70, 229),   "name": "Adam"},
    {"filename": "peter_finance.png", "query": "analyst finance professional portrait",     "initial": "N", "color": (8, 145, 178),   "name": "Antoni"},
    {"filename": "stewie.png",        "query": "athletic runner sport portrait",            "initial": "A", "color": (217, 119, 6),   "name": "Amy"},
    {"filename": "spongebob.png",     "query": "security professional confident portrait",  "initial": "A", "color": (5, 150, 105),   "name": "Arnold"},
    {"filename": "squidward.png",     "query": "creative designer woman professional",      "initial": "R", "color": (219, 39, 119),  "name": "Rachel"},
    {"filename": "patrick.png",       "query": "software engineer developer portrait",      "initial": "J", "color": (234, 88, 12),   "name": "Joe"},
    {"filename": "trump.png",         "query": "visionary entrepreneur woman leader",       "initial": "K", "color": (124, 58, 237),  "name": "Kristin"},
]

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")


def fetch_pexels_photo(query: str, out_path: Path) -> bool:
    if not PEXELS_API_KEY:
        return False
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": 1, "orientation": "square"},
            timeout=10,
        )
        if r.status_code != 200:
            print(f"  Pexels {r.status_code} for '{query}'")
            return False
        photos = r.json().get("photos", [])
        if not photos:
            return False
        url = photos[0]["src"]["medium"]
        img_data = requests.get(url, timeout=15).content
        out_path.write_bytes(img_data)
        print(f"  Downloaded: {out_path.name}")
        return True
    except Exception as e:
        print(f"  Pexels error: {e}")
        return False


def generate_avatar(char: dict, out_path: Path):
    size = 200
    img = Image.new("RGB", (size, size), color=char["color"])
    draw = ImageDraw.Draw(img)

    # Dark circle background
    margin = 10
    draw.ellipse([margin, margin, size - margin, size - margin], fill=char["color"])

    # Initial letter
    try:
        font = ImageFont.truetype(str(PROJECT_ROOT / "assets" / "fonts" / "arial.ttf"), 80)
    except Exception:
        font = ImageFont.load_default()

    text = char["initial"]
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) // 2, (size - th) // 2 - 10), text, fill="white", font=font)

    # Name label at bottom
    try:
        small_font = ImageFont.truetype(str(PROJECT_ROOT / "assets" / "fonts" / "arial.ttf"), 18)
    except Exception:
        small_font = ImageFont.load_default()

    name = char["name"]
    nbbox = draw.textbbox((0, 0), name, font=small_font)
    nw = nbbox[2] - nbbox[0]
    draw.text(((size - nw) // 2, size - 35), name, fill="white", font=small_font)

    img.save(out_path, "PNG")
    print(f"  Generated avatar: {out_path.name}")


def main():
    STATIC_IMG.mkdir(parents=True, exist_ok=True)

    if not PEXELS_API_KEY:
        print("PEXELS_API_KEY not set — using PIL avatars")

    for char in CHARACTERS:
        out = STATIC_IMG / char["filename"]
        print(f"Processing {char['name']}...")
        if not fetch_pexels_photo(char["query"], out):
            generate_avatar(char, out)

    print("\nDone. Sizes:")
    for char in CHARACTERS:
        p = STATIC_IMG / char["filename"]
        print(f"  {p.name}: {p.stat().st_size} bytes")


if __name__ == "__main__":
    main()
