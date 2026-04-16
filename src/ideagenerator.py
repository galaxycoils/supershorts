# src/ideagenerator.py
# YouTube Studio Idea Generator — real YT suggestions + downloaded thumbnails + Ollama dialogue
import json
import re
import requests
import ollama
import datetime
from pathlib import Path
from src.generator import generate_visuals  # reuse for Ollama-only thumbnails

LOG_FILE    = Path("performance_log.json")
IDEAS_FILE  = Path("youtube_studio_ideas.json")
CONFIG_FILE = Path("config.json")


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
    key = input("  Paste API key (Enter to skip, use Ollama-only mode): ").strip()
    if key:
        cfg["youtube_api_key"] = key
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
        print("  Key saved to config.json")
    return key or None


# ─────────────────── YouTube Data API v3 ────────────────────────

def fetch_yt_suggestions(query: str = "AI tutorial 2025",
                          max_results: int = 5,
                          api_key: str = None) -> list:
    """Search YouTube for trending videos. Returns list of dicts with metadata."""
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
            msg = data["error"].get("message", "unknown error")
            print(f"  YT API error: {msg}")
            return []
        results = []
        for item in data.get("items", []):
            snippet  = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId", "")
            thumbs   = snippet.get("thumbnails", {})
            # Prefer highest-res thumbnail available
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
    """Download actual YouTube thumbnail to output/thumbnails/. Returns local path."""
    url      = video_data.get("thumbnail_url", "")
    video_id = video_data.get("video_id", "unknown")
    if not url:
        return None
    out_dir = Path("output/thumbnails")
    out_dir.mkdir(exist_ok=True, parents=True)
    dest = out_dir / f"yt_{video_id}.jpg"
    if dest.exists():
        print(f"  Thumbnail cached: {dest.name}")
        return str(dest)
    try:
        r = requests.get(url, timeout=10)
        dest.write_bytes(r.content)
        print(f"  Downloaded thumbnail: {dest.name}")
        return str(dest)
    except Exception as e:
        print(f"  Thumbnail download failed: {e}")
        return None


def generate_dialogue_from_yt(video_data: dict) -> dict:
    """Ollama generates adapted short-form script inspired by a real YT video."""
    title = video_data.get("title", "")
    desc  = video_data.get("description", "")[:600]
    prompt = f"""
You are a YouTube Shorts scriptwriter for SuperShorts channel.
A trending YouTube video exists with this metadata:
TITLE: {title}
DESCRIPTION: {desc}

Write a punchier, hook-driven 60-90 second YouTube Short script on the same topic.
Rules: hook first 2 seconds, plain spoken language, "you" addressing viewer, end with CTA.
Return ONLY JSON:
{{
  "title": "clickbait title with emoji",
  "hook": "first 2-second sentence",
  "dialogue": "full spoken script here",
  "thumbnail_prompt": "visual style description for thumbnail image"
}}"""
    try:
        resp = ollama.chat(
            model="qwen2.5-coder:3b",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.75, "num_ctx": 2048},
        )
        text = resp["message"]["content"]
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1]
        result = json.loads(text)
    except Exception as e:
        print(f"  Dialogue gen failed ({e}), using fallback.")
        result = {
            "title":            title,
            "hook":             f"Nobody is talking about this AI secret...",
            "dialogue":         desc or "This AI technology is changing everything. Here is how it works.",
            "thumbnail_prompt": "cinematic neon AI background",
        }
    # Attach source metadata
    result["yt_thumbnail_url"] = video_data.get("thumbnail_url", "")
    result["yt_video_id"]      = video_data.get("video_id", "")
    result["yt_link"]          = video_data.get("yt_link", "")
    result["source_title"]     = title
    return result


# ─────────────────── Ollama-only flow (fallback) ─────────────────

def generate_ideas(num_ideas: int = 5) -> list:
    """Pure Ollama idea generation (no YouTube API needed)."""
    data    = load_performance_data()
    trending = get_trending_context()

    if not data:
        past_data = "No past data yet. Generate fresh ideas based on trending topics only."
    else:
        lines     = [f"- {e.get('title','Untitled')} (mode: {e.get('mode','?')})" for e in data[-10:]]
        past_data = "\n".join(lines)

    prompt = f"""
You are YouTube Studio's AI Idea Generator.
TRENDING: {trending}
PAST PERFORMANCE: {past_data}

Generate {num_ideas} YouTube Short ideas. Each needs:
- title (clickbait + searchable, include emoji)
- hook (first 2-second sentence)
- dialogue (full 60-90 second script)
- thumbnail_prompt (describe the image)

Return ONLY a valid JSON array of objects."""

    print("  Asking Ollama for ideas...")
    try:
        resp  = ollama.chat(
            model="qwen2.5-coder:3b",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.8, "num_ctx": 4096},
        )
        text  = resp["message"]["content"]
        if "```json" in text: text = text.split("```json")[1].split("```")[0]
        elif "```" in text:   text = text.split("```")[1]
        try:
            ideas = json.loads(text)
        except Exception:
            match = re.search(r'\[.*\]', text, re.DOTALL)
            ideas = json.loads(match.group(0)) if match else []
        if not isinstance(ideas, list):
            ideas = ideas.get("ideas", [ideas]) if isinstance(ideas, dict) else []
    except Exception as e:
        print(f"  Ollama failed ({e}), using fallback ideas.")
        ideas = [
            {"title": f"AI Secret #{i+1}", "hook": "Nobody talks about this...",
             "dialogue": "Here is an AI trick that will change how you work forever.",
             "thumbnail_prompt": "neon circuits dark background"}
            for i in range(num_ideas)
        ]
    IDEAS_FILE.write_text(json.dumps(ideas, indent=2))
    return ideas


def create_thumbnail_from_idea(idea: dict) -> str:
    """Generate thumbnail using existing slide renderer."""
    title      = idea.get("title", "New Idea")
    output_dir = Path("output/thumbnails")
    output_dir.mkdir(exist_ok=True, parents=True)
    return generate_visuals(output_dir=output_dir, video_type='long', thumbnail_title=title)


# ──────────────── sub-flow helpers ───────────────────────────────

def _yt_ideas_flow():
    """Fetch real YouTube suggestions, download thumbnails, gen dialogue."""
    api_key = get_yt_api_key()
    if not api_key:
        print("  No API key — switching to Ollama-only mode.")
        _ollama_ideas_flow()
        return

    query = input("  Search query (Enter = 'AI tutorial 2025'): ").strip() or "AI tutorial 2025"
    print(f"\n  Searching YouTube for '{query}'...")
    yt_videos = fetch_yt_suggestions(query, max_results=5, api_key=api_key)

    if not yt_videos:
        print("  No results from YouTube — switching to Ollama mode.")
        _ollama_ideas_flow()
        return

    print(f"\n  Found {len(yt_videos)} trending videos:\n")
    for i, v in enumerate(yt_videos):
        print(f"  [{i+1}] {v['title']}")
        print(f"       Channel: {v['channel']}")
        print(f"       Link:    {v['yt_link']}")
        print()

    sel = input("  Pick one as inspiration (number) or 0 to use all: ").strip()
    if sel == "0" or not sel.isdigit():
        targets = yt_videos
    else:
        idx     = int(sel) - 1
        targets = [yt_videos[idx]] if 0 <= idx < len(yt_videos) else yt_videos

    ideas = []
    for vid in targets:
        print(f"\n  Downloading thumbnail: {vid['title'][:50]}...")
        local_thumb      = download_yt_thumbnail(vid)
        print(f"  Generating adapted dialogue...")
        idea             = generate_dialogue_from_yt(vid)
        idea["local_thumbnail_path"] = local_thumb
        ideas.append(idea)

    IDEAS_FILE.write_text(json.dumps(ideas, indent=2))
    print(f"\n  Generated {len(ideas)} ideas from YouTube:\n")
    for i, idea in enumerate(ideas):
        print(f"  [{i+1}] {idea.get('title','?')}")
        print(f"       Hook:      {idea.get('hook','?')[:80]}")
        if idea.get("local_thumbnail_path"):
            print(f"       Thumbnail: {idea['local_thumbnail_path']}")
        print()

    use = input("  View full dialogue for one? (number or 0 to skip): ").strip()
    if use.isdigit() and 1 <= int(use) <= len(ideas):
        s = ideas[int(use) - 1]
        print(f"\n  TITLE: {s.get('title')}")
        print(f"  HOOK:  {s.get('hook')}")
        print(f"\n  DIALOGUE:\n{s.get('dialogue','N/A')}")
        if s.get("local_thumbnail_path"):
            print(f"\n  THUMBNAIL SAVED AT: {s['local_thumbnail_path']}")
        print(f"\n  ORIGINAL YT VIDEO: {s.get('yt_link','N/A')}")


def _ollama_ideas_flow():
    """Pure Ollama ideas flow."""
    ideas = generate_ideas(num_ideas=5)
    if not ideas:
        print("  No ideas generated.")
        return
    print(f"\n  Generated {len(ideas)} ideas:\n")
    for i, idea in enumerate(ideas):
        print(f"  [{i+1}] {idea.get('title','?')}")
        hook = idea.get('hook') or idea.get('description','?')
        print(f"       Hook: {str(hook)[:80]}")
    use = input("\n  Use one? (number or 0): ").strip()
    if use.isdigit() and 1 <= int(use) <= len(ideas):
        selected   = ideas[int(use) - 1]
        thumb_path = create_thumbnail_from_idea(selected)
        print(f"  Thumbnail saved: {thumb_path}")
        dialogue   = selected.get("dialogue") or selected.get("script","No dialogue")
        print(f"\n  DIALOGUE:\n{str(dialogue)[:800]}")


def _view_saved_ideas_flow():
    """Browse previously saved ideas."""
    if not IDEAS_FILE.exists():
        print("  No saved ideas yet.")
        return
    try:
        ideas = json.loads(IDEAS_FILE.read_text())
        print(f"\n  Saved ideas ({len(ideas)}):\n")
        for i, idea in enumerate(ideas):
            src = " [YT]" if idea.get("yt_video_id") else " [Ollama]"
            print(f"  [{i+1}]{src} {idea.get('title','?')}")
        sel = input("\n  View which? (number or 0): ").strip()
        if sel.isdigit() and 1 <= int(sel) <= len(ideas):
            s = ideas[int(sel) - 1]
            print(f"\n  TITLE:    {s.get('title')}")
            print(f"  HOOK:     {s.get('hook') or s.get('description')}")
            if s.get("local_thumbnail_path"):
                print(f"  THUMBNAIL: {s['local_thumbnail_path']}")
            elif s.get("yt_thumbnail_url"):
                print(f"  YT THUMB:  {s['yt_thumbnail_url']}")
            if s.get("yt_link"):
                print(f"  SOURCE:    {s['yt_link']}")
            print(f"\n  DIALOGUE:\n{s.get('dialogue') or s.get('script','N/A')}")
    except Exception as e:
        print(f"  Error reading ideas file: {e}")


# ─────────────────── main entry point ────────────────────────────

def start_idea_generator():
    print("\n  YouTube Studio Idea Generator\n")
    print("  [1]  Fetch real YouTube suggestions + download thumbnails + gen dialogue")
    print("  [2]  Generate Ollama-only ideas (no API key needed)")
    print("  [3]  Browse saved ideas / scripts")
    print()
    choice = input("  Choose (1-3): ").strip()

    if choice == "1":
        _yt_ideas_flow()
    elif choice == "2":
        _ollama_ideas_flow()
    elif choice == "3":
        _view_saved_ideas_flow()
    else:
        print("  Invalid choice.")

    input("\n  Press Enter to return to menu...")
