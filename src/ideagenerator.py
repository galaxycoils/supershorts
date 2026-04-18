# src/ideagenerator.py
# YouTube Studio Idea Generator — real YT suggestions + thumbnails + Ollama dialogue
# Auto-produces short-form video + uploads for every idea found. Zero interactive prompts
# after the first-time API key setup.

import json
import re
import time
import datetime
import concurrent.futures
import requests
import ollama
from pathlib import Path
from tqdm import tqdm

from src.generator import (
    generate_visuals,
    text_to_speech,
    compose_video,
    strip_emojis,
    _clamp_words,
    OUTPUT_DIR,
    PROJECT_ROOT,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    safe_json_parse,
)

LOG_FILE    = PROJECT_ROOT / "performance_log.json"
IDEAS_FILE  = PROJECT_ROOT / "youtube_studio_ideas.json"
CONFIG_FILE = PROJECT_ROOT / "config.json"


# ─────────────────────────── helpers ────────────────────────────

def load_performance_data():
    try:
        return json.loads(LOG_FILE.read_text()) if LOG_FILE.exists() else []
    except Exception:
        return []


def get_trending_context():
    return (
        "Trending: DeepSeek-V3, Qwen-2.5-Max, Agentic Workflows, "
        "local RAG, AI video generation, coding agents, GPT-5 rumours, "
        "open-source LLMs, Claude 3.5, Gemini Ultra, AI coding tools."
    )


def get_yt_api_key() -> str | None:
    """Read YouTube Data API key from config.json; prompt + save if missing."""
    try:
        cfg = json.loads(CONFIG_FILE.read_text()) if CONFIG_FILE.exists() else {}
        if cfg.get("youtube_api_key"):
            return cfg["youtube_api_key"]
    except Exception:
        cfg = {}

    print("\n  YouTube Data API key needed for real Studio suggestions.")
    print("  Get free key: https://console.cloud.google.com/apis/library/youtube.googleapis.com")
    key = input("  Paste API key (Enter to skip → Ollama-only mode): ").strip()
    if key:
        cfg["youtube_api_key"] = key
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
        print("  Key saved to config.json")
    return key or None


# ─────────────────── YouTube Data API v3 ────────────────────────

def fetch_yt_suggestions(query: str = "AI tutorial 2025",
                          max_results: int = 5,
                          api_key: str = None) -> list:
    if not api_key:
        return []
    url = (
        "https://www.googleapis.com/youtube/v3/search"
        f"?part=snippet&q={requests.utils.quote(query)}"
        f"&type=video&order=viewCount&maxResults={max_results}&key={api_key}"
    )
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if "error" in data:
            print(f"  YT API error: {data['error'].get('message','unknown')}")
            return []
        results = []
        for item in data.get("items", []):
            snippet  = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId", "")
            thumbs   = snippet.get("thumbnails", {})
            thumb_url = (
                thumbs.get("maxres", thumbs.get("high", thumbs.get("medium", {}))).get("url", "")
            )
            results.append({
                "video_id":      video_id,
                "title":         snippet.get("title", ""),
                "description":   snippet.get("description", ""),
                "channel":       snippet.get("channelTitle", ""),
                "thumbnail_url": thumb_url,
                "yt_link":       f"https://youtube.com/watch?v={video_id}",
            })
        return results
    except Exception as e:
        print(f"  YT fetch failed: {e}")
        return []


def download_yt_thumbnail(video_data: dict) -> str | None:
    url      = video_data.get("thumbnail_url", "")
    video_id = video_data.get("video_id", "unknown")
    if not url:
        return None
    out_dir = PROJECT_ROOT / "output" / "thumbnails"
    out_dir.mkdir(exist_ok=True, parents=True)
    dest = out_dir / f"yt_{video_id}.jpg"
    if dest.exists():
        return str(dest)
    try:
        r = requests.get(url, timeout=10)
        dest.write_bytes(r.content)
        print(f"  Thumbnail: {dest.name}")
        return str(dest)
    except Exception as e:
        print(f"  Thumbnail download failed: {e}")
        return None


def generate_dialogue_from_yt(video_data: dict) -> dict:
    """Ollama generates a 60-90 second Short script from a real YT video."""
    title = video_data.get("title", "")
    desc  = video_data.get("description", "")[:600]
    prompt = f"""You are a YouTube Shorts scriptwriter for the SuperShorts channel.
A trending video exists:
TITLE: {title}
DESCRIPTION: {desc}

Write a punchy 35-45 second Short script on the same topic — punchier and more hooky.
Rules: hook first 2 seconds, plain spoken language, address viewer as "you", end with CTA.
IMPORTANT: dialogue MUST be exactly 99-127 words (35-45 seconds at 170 wpm). NO more, NO less.
Return ONLY JSON:
{{
  "title": "clickbait title",
  "hook": "first 2-second hook sentence",
  "dialogue": "99-127 word spoken script here",
  "thumbnail_prompt": "visual description for thumbnail"
}}"""
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(
                lambda: ollama.chat(
                    model=OLLAMA_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    options={"temperature": 0.75, "num_ctx": 2048},
                )
            )
            resp = future.result(timeout=OLLAMA_TIMEOUT)
        text = resp["message"]["content"]
        if "```json" in text: text = text.split("```json")[1].split("```")[0]
        elif "```" in text:   text = text.split("```")[1]
        result = safe_json_parse(text)
    except Exception as e:
        print(f"  Dialogue gen failed ({e}), using fallback.")
        result = {
            "title":            title,
            "hook":             "Nobody is talking about this AI secret...",
            "dialogue":         desc or "This AI technology is changing everything. Here is what you need to know.",
            "thumbnail_prompt": "cinematic neon AI background",
        }
    # Enforce 35-45s duration (99-127 words)
    if result.get("dialogue"):
        result["dialogue"] = _clamp_words(result["dialogue"], min_w=99, max_w=127)
    result["yt_thumbnail_url"] = video_data.get("thumbnail_url", "")
    result["yt_video_id"]      = video_data.get("video_id", "")
    result["yt_link"]          = video_data.get("yt_link", "")
    result["source_title"]     = title
    return result


def generate_ideas(num_ideas: int = 5) -> list:
    """Pure Ollama idea generation (no YouTube API needed)."""
    data     = load_performance_data()
    trending = get_trending_context()
    past_data = (
        "\n".join(f"- {e.get('title','Untitled')} ({e.get('mode','?')})" for e in data[-10:])
        if data else "No past data. Generate fresh ideas."
    )
    prompt = f"""You are YouTube Studio's AI Idea Generator.
TRENDING: {trending}
PAST PERFORMANCE: {past_data}

Generate {num_ideas} YouTube Short ideas. Each object must have:
- title (clickbait + searchable, include emoji)
- hook (first 2-second sentence)
- dialogue (35-45 second spoken script — exactly 99-127 words, NO more, NO less)
- thumbnail_prompt (visual description)

Return ONLY a valid JSON array of {num_ideas} objects."""

    print("  Asking Ollama for ideas...")
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(
                lambda: ollama.chat(
                    model=OLLAMA_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    options={"temperature": 0.8, "num_ctx": 4096},
                )
            )
            resp = future.result(timeout=OLLAMA_TIMEOUT)
        text  = resp["message"]["content"]
        if "```json" in text: text = text.split("```json")[1].split("```")[0]
        elif "```" in text:   text = text.split("```")[1]
        try:
            ideas = safe_json_parse(text)
        except Exception:
            match = re.search(r'\[.*\]', text, re.DOTALL)
            ideas = json.loads(match.group(0)) if match else []
        if not isinstance(ideas, list):
            ideas = ideas.get("ideas", [ideas]) if isinstance(ideas, dict) else []
        # Enforce 35-45s duration on every idea
        for idea in ideas:
            if isinstance(idea, dict) and idea.get("dialogue"):
                idea["dialogue"] = _clamp_words(idea["dialogue"], min_w=99, max_w=127)
    except Exception as e:
        print(f"  Ollama failed ({e}), using fallback ideas.")
        ideas = [
            {
                "title":            f"🤖 AI Secret #{i+1} Nobody Talks About",
                "hook":             "Nobody is talking about this...",
                "dialogue":         (
                    "Here is an AI trick that will change how you work forever. "
                    "Most developers spend hours on tasks that AI can handle in seconds. "
                    "The key is knowing which tool to use and how to prompt it correctly. "
                    "This single technique has saved professionals countless hours every week. "
                    "Start using this today and you will never go back to the old way. "
                    "Subscribe for more AI productivity tips."
                ),
                "thumbnail_prompt": "neon circuits dark background",
            }
            for i in range(num_ideas)
        ]
    IDEAS_FILE.write_text(json.dumps(ideas, indent=2))
    return ideas


def create_thumbnail_from_idea(idea: dict) -> str:
    """Generate thumbnail PNG for an idea using existing slide renderer."""
    title      = idea.get("title", "New Idea")
    output_dir = PROJECT_ROOT / "output" / "thumbnails"
    output_dir.mkdir(exist_ok=True, parents=True)
    return generate_visuals(output_dir=output_dir, video_type='short', thumbnail_title=title)


# ──────────────── video production per idea ──────────────────────

def _produce_and_upload_idea(idea: dict, index: int, total: int) -> dict:
    """
    Full pipeline for one idea:
      dialogue → TTS → thumbnail → compose Short → upload
    Returns result dict with status.
    """
    from src.browser_uploader import upload_to_youtube_browser
    from src.learning import log_upload

    title    = strip_emojis(idea.get("title", f"Idea {index+1}"))[:100]
    dialogue = strip_emojis(idea.get("dialogue", idea.get("script", "")))
    if not dialogue.strip():
        print(f"  [{index+1}/{total}] No dialogue — skipping.")
        return {"status": "skipped", "title": title}

    # Enforce 35-45s duration before TTS
    dialogue = _clamp_words(dialogue, min_w=99, max_w=127)

    print(f"\n  ── Idea {index+1}/{total}: {title[:60]} ──")

    uid = f"idea_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{index}"

    # TTS
    audio_path = text_to_speech(dialogue, OUTPUT_DIR / f"{uid}_audio.mp3")

    # Thumbnail — prefer downloaded YT thumb, else generate one
    local_thumb = idea.get("local_thumbnail_path")
    if not local_thumb or not Path(str(local_thumb)).exists():
        local_thumb = create_thumbnail_from_idea(idea)

    # Slide visual (dark card with title + hook)
    slide_content = {
        "title":   title,
        "content": idea.get("hook", dialogue[:200]),
    }
    slide_dir  = OUTPUT_DIR / f"{uid}_slides"
    slide_path = generate_visuals(slide_dir, "short", slide_content,
                                  slide_number=1, total_slides=1)

    # Compose Short with subtitle overlay
    video_path = OUTPUT_DIR / f"{uid}.mp4"
    print(f"  Composing → {video_path.name}")
    compose_video([slide_path], [audio_path], video_path, "short", title, script=dialogue)

    # Upload
    hashtags = "#AI #Shorts #Tech #Viral #AIFacts"
    desc     = f"{dialogue[:500]}\n\n{hashtags}\n\nProduced by SuperShorts"
    short_title = f"{title[:80]} #Shorts"
    print(f"  Uploading → {short_title[:60]}...")
    video_id = upload_to_youtube_browser(video_path, short_title, desc,
                                         "AI,Shorts,Viral,Tech,AIFacts")
    if video_id:
        log_upload(short_title, video_id, "studio_idea")
        print(f"  Live: https://youtube.com/watch?v={video_id}")
        return {"status": "complete", "title": short_title, "youtube_id": video_id}
    else:
        print(f"  Upload failed — saved: {video_path.name}")
        return {"status": "upload_failed", "title": short_title, "path": str(video_path)}


# ─────────────────── main entry point ────────────────────────────

def start_idea_generator():
    """
    Option 6 — fully auto-pilot:
    1. Fetch real YT suggestions (or Ollama-only if no API key)
    2. Generate adapted dialogue + download thumbnails
    3. Produce Short video for each idea
    4. Upload each one with 30 s gap
    """
    print("\n  YouTube Studio Idea Generator — Auto-Pilot Mode\n")

    # ── gather ideas ─────────────────────────────────────────────
    api_key   = get_yt_api_key()
    ideas     = []

    if api_key:
        print("\n  Searching YouTube for trending AI content...")
        yt_videos = fetch_yt_suggestions("AI productivity tutorial 2025",
                                          max_results=5, api_key=api_key)
        if yt_videos:
            print(f"  Found {len(yt_videos)} trending videos — generating adapted scripts...")
            for vid in tqdm(yt_videos, desc="  Adapting", unit="video"):
                local_thumb = download_yt_thumbnail(vid)
                idea        = generate_dialogue_from_yt(vid)
                idea["local_thumbnail_path"] = local_thumb
                ideas.append(idea)
        else:
            print("  No YT results — falling back to Ollama ideas.")

    if not ideas:
        ideas = generate_ideas(num_ideas=5)

    if not ideas:
        print("  No ideas generated.")
        return

    IDEAS_FILE.write_text(json.dumps(ideas, indent=2))
    print(f"\n  {len(ideas)} ideas ready — producing + uploading all...\n")

    # ── produce + upload ─────────────────────────────────────────
    results = []
    for i, idea in enumerate(ideas):
        try:
            result = _produce_and_upload_idea(idea, i, len(ideas))
            results.append(result)
            # 30 s gap between uploads (skip after last)
            if i < len(ideas) - 1 and result.get("status") == "complete":
                print(f"\n  Waiting 30 s before next upload...")
                time.sleep(30)
        except Exception as e:
            import traceback
            print(f"  Error on idea {i+1}: {e}")
            traceback.print_exc()
            results.append({"status": "error", "error": str(e)})

    # ── summary ──────────────────────────────────────────────────
    done   = sum(1 for r in results if r.get("status") == "complete")
    failed = len(results) - done
    print(f"\n  Studio Ideas done — {done}/{len(ideas)} uploaded"
          + (f", {failed} failed/local" if failed else "") + ".")
