# src/rotgen.py — RotGen Character Mode
# Split-screen brain rot: animated AI character (top) + gameplay (middle) + subtitles (bottom)
# Layout: 1080×1920  │  Character panel 0–768  │  Gameplay 768–1760  │  Subtitle bar 1760–1920

import gc
import math
import json
import random
import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from moviepy.editor import (
    AudioFileClip,
    ImageClip,
    VideoFileClip,
    CompositeVideoClip,
    CompositeAudioClip,
    ImageSequenceClip,
    ColorClip,
    vfx,
)

from src.generator import (
    text_to_speech,
    ollama_generate,
    strip_emojis,
    get_local_viral_gameplay,
    get_local_gameplay,
    get_relevant_pexels_video,
    FONT_FILE,
    ASSETS_PATH,
    BACKGROUND_MUSIC_PATH,
    OUTPUT_DIR,
    YOUR_NAME,
)

# ─────────────────────────── constants ──────────────────────────────────────

CHARACTERS_PATH    = ASSETS_PATH / "characters"
ROTGEN_PLAN_FILE   = Path("rotgen_plan.json")

CANVAS_W, CANVAS_H = 400, 500      # character drawing canvas
PANEL_W,  PANEL_H  = 1080, 768     # character panel (top of frame)
GAMEPLAY_H         = 992            # 1920 - 768 - 160
SUBTITLE_H         = 160
VIDEO_W,  VIDEO_H  = 1080, 1920
FPS                = 24
ANIMATION_FRAMES   = 48             # 2-second loop

CHAR_PASTE_X = (PANEL_W - CANVAS_W) // 2   # 340
CHAR_PASTE_Y = (PANEL_H - CANVAS_H) // 2   # 134

SKIN  = (255, 220, 170)
BLUE  = (30,  120, 220)
DARK  = (40,   30,  20)

VIRAL_TOPICS = [
    "Why AI Will Replace 90% of Jobs by 2030",
    "This FREE AI Codes Better Than ChatGPT",
    "Nobody Is Talking About This AI Secret",
    "How To Build Your Own AI Agent in 5 Minutes",
    "The AI Tool That Automates Everything",
    "AI Just Beat Every Human At This Task",
    "The Dark Side of AI Nobody Shows You",
    "This AI Model Runs Entirely On Your Phone",
    "Why Big Tech Is Scared Of Open-Source AI",
    "How DeepSeek Destroyed a $600B Company Overnight",
]

ROTGEN_PEXELS_QUERIES = [
    "subway surfers parkour",
    "minecraft gameplay",
    "satisfying sand cutting",
    "mobile endless runner game",
    "hypnotic satisfying craft",
]


# ─────────────────────────── helpers ────────────────────────────────────────

def ensure_dirs() -> None:
    CHARACTERS_PATH.mkdir(exist_ok=True, parents=True)
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def load_rotgen_plan() -> dict:
    if not ROTGEN_PLAN_FILE.exists():
        return {"videos": []}
    try:
        return json.loads(ROTGEN_PLAN_FILE.read_text())
    except Exception:
        return {"videos": []}


def save_rotgen_plan(plan: dict) -> None:
    ROTGEN_PLAN_FILE.write_text(json.dumps(plan, indent=2))


# ─────────────────────────── script gen ─────────────────────────────────────

def generate_rotgen_script(topic: str | None = None) -> dict:
    if not topic:
        topic = random.choice(VIRAL_TOPICS)
    print(f"  Topic: {topic}")
    prompt = f"""
You are scripting a 30-45 second YouTube Short for a character called ByteBot.
ByteBot is an enthusiastic AI educator who talks directly to camera.
Topic: {topic}

Rules:
- Under 60 words total
- First-person, conversational, energetic
- No emojis (TTS will read them aloud)
- Start with a shocking hook sentence
- End with exactly: "Follow for more AI facts"

Return ONLY valid JSON:
{{
  "script": "full narration text under 60 words",
  "title": "YouTube title for this short",
  "hashtags": "#AI #Shorts #Tech"
}}"""
    try:
        result = ollama_generate(prompt, json_mode=True)
        if result.get("script"):
            return result
    except Exception as e:
        print(f"  Ollama failed ({e}), using fallback script.")
    return {
        "script": (
            f"{topic}. Most people have no idea this is already happening. "
            "AI systems are changing the world faster than any technology in history. "
            "The question is not if it will affect you, but when. Follow for more AI facts."
        ),
        "title":    f"{topic[:80]} #Shorts",
        "hashtags": "#AI #Shorts #Tech #AIFacts #ByteBot",
    }


# ─────────────────────────── character drawing ──────────────────────────────

def _load_custom_character() -> Image.Image | None:
    """Load first PNG/GIF found in assets/characters/. Returns RGBA 400×500 or None."""
    for ext in ("*.png", "*.gif", "*.jpg", "*.jpeg"):
        files = list(CHARACTERS_PATH.glob(ext))
        if files:
            img = Image.open(files[0]).convert("RGBA")
            img.thumbnail((CANVAS_W, CANVAS_H), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
            ox = (CANVAS_W - img.width) // 2
            oy = (CANVAS_H - img.height) // 2
            canvas.paste(img, (ox, oy), img)
            print(f"  Custom character loaded: {files[0].name}")
            return canvas
    return None


def _draw_character_on_canvas(
    canvas: Image.Image,
    speaking: bool,
    frame_index: int,
    num_frames: int = ANIMATION_FRAMES,
    custom_img: Image.Image | None = None,
) -> None:
    """Draw ByteBot onto a transparent RGBA canvas. Applies head-bob per frame."""
    yo = int(math.sin(frame_index * 2 * math.pi / num_frames) * 8)  # head bob ±8px
    blink = frame_index in (20, 21)

    if custom_img is not None:
        # Custom image: just paste with bob offset
        canvas.paste(custom_img, (0, yo), custom_img)
        return

    d = ImageDraw.Draw(canvas)

    def y(v):   return v + yo   # apply bob to all y-coords

    # ── Hair cap ─────────────────────────────────────────────────────────────
    d.ellipse([(70, y(30)), (330, y(160))],  fill=DARK)
    d.rectangle([(70, y(95)), (330, y(140))], fill=DARK)

    # ── Head ─────────────────────────────────────────────────────────────────
    d.ellipse([(75, y(40)), (325, y(280))],  fill=SKIN, outline=(200, 160, 110), width=3)

    # ── Ears ─────────────────────────────────────────────────────────────────
    d.ellipse([(60, y(130)), (95,  y(200))],  fill=SKIN, outline=(200, 160, 110), width=2)
    d.ellipse([(305, y(130)), (340, y(200))], fill=SKIN, outline=(200, 160, 110), width=2)

    # ── Eyes ─────────────────────────────────────────────────────────────────
    if blink:
        d.line([(133, y(140)), (177, y(140))], fill=(30, 80, 220), width=4)
        d.line([(223, y(140)), (267, y(140))], fill=(30, 80, 220), width=4)
    else:
        for (ex1, ey1, ex2, ey2), (ix1, iy1, ix2, iy2), (px1, py1, px2, py2), (gx, gy) in [
            ((133, 118, 177, 162), (143, 128, 167, 152), (150, 135, 160, 145), (159, 136)),
            ((223, 118, 267, 162), (233, 128, 257, 152), (240, 135, 250, 145), (249, 136)),
        ]:
            d.ellipse([(ex1, y(ey1)), (ex2, y(ey2))],   fill="white")
            d.ellipse([(ix1, y(iy1)), (ix2, y(iy2))],   fill=(30, 80, 220))
            d.ellipse([(px1, y(py1)), (px2, y(py2))],   fill="black")
            # glint
            d.ellipse([(gx-3, y(gy)-3), (gx+3, y(gy)+3)], fill="white")

    # ── Eyebrows ─────────────────────────────────────────────────────────────
    d.arc([(130, y(95)), (180, y(118))],  start=200, end=340, fill=(80, 50, 20), width=4)
    d.arc([(220, y(95)), (270, y(118))],  start=200, end=340, fill=(80, 50, 20), width=4)

    # ── Nose ─────────────────────────────────────────────────────────────────
    d.arc([(185, y(178)), (215, y(200))], start=0, end=180, fill=(180, 130, 90), width=3)

    # ── Mouth ────────────────────────────────────────────────────────────────
    if speaking:
        # Pulsing open oval
        pulse_h = 12 + int(8 * abs(math.sin(frame_index * math.pi / 6)))
        mx1, mx2 = 165, 235
        mcy = y(215)
        d.ellipse([(mx1, mcy - pulse_h), (mx2, mcy + pulse_h)],
                  fill=(60, 20, 10), outline=(160, 90, 60), width=3)
        # Teeth hint
        d.line([(mx1 + 8, mcy - 2), (mx2 - 8, mcy - 2)], fill=(235, 235, 235), width=3)
    else:
        d.arc([(155, y(195)), (245, y(240))], start=0, end=180,
              fill=(160, 90, 60), width=4)

    # ── Neck ─────────────────────────────────────────────────────────────────
    d.rectangle([(170, y(275)), (230, y(330))], fill=SKIN, outline=(200, 160, 110), width=2)

    # ── Body / shirt ─────────────────────────────────────────────────────────
    body_pts = [(100, y(325)), (300, y(325)), (360, y(500)), (40, y(500))]
    d.polygon(body_pts, fill=BLUE, outline=(20, 80, 160))

    # Collars
    d.polygon([(170, y(325)), (200, y(380)), (130, y(340))], fill=(240, 240, 255))
    d.polygon([(230, y(325)), (200, y(380)), (270, y(340))], fill=(240, 240, 255))

    # Name badge
    d.rectangle([(155, y(395)), (245, y(430))], fill="white", outline=(180, 180, 200))
    try:
        badge_font = ImageFont.truetype(str(FONT_FILE), 22)
    except IOError:
        badge_font = ImageFont.load_default()
    d.text((200, y(412)), "AI", fill=BLUE, font=badge_font, anchor="mm")


# ─────────────────────────── panel background ───────────────────────────────

def _build_panel_background() -> np.ndarray:
    """Dark gradient panel (1080×768). Returns (768, 1080, 3) uint8 numpy array."""
    # Vertical gradient: near-black top → slightly lighter bottom
    arr = np.zeros((PANEL_H, PANEL_W, 3), dtype=np.uint8)
    top    = np.array([15, 15, 25],  dtype=np.float32)
    bottom = np.array([30, 30, 55],  dtype=np.float32)
    for row in range(PANEL_H):
        t = row / PANEL_H
        arr[row, :] = (top * (1 - t) + bottom * t).astype(np.uint8)

    # Accent glow line at very bottom of panel (cyan)
    arr[762:768, :] = np.array([0, 200, 255], dtype=np.uint8)

    # "ByteBot" label in top-left corner
    panel_img = Image.fromarray(arr, "RGB")
    d = ImageDraw.Draw(panel_img)
    try:
        lbl_font = ImageFont.truetype(str(FONT_FILE), 28)
    except IOError:
        lbl_font = ImageFont.load_default()
    d.text((20, 18), f"ByteBot  ·  AI for Developers by {YOUR_NAME}",
           fill=(0, 200, 255), font=lbl_font)
    return np.array(panel_img)


# ─────────────────────────── frame generation ───────────────────────────────

def generate_panel_frames(
    speaking: bool,
    panel_bg: np.ndarray,
    num_frames: int = ANIMATION_FRAMES,
    custom_img: Image.Image | None = None,
) -> list[np.ndarray]:
    """
    Pre-generate `num_frames` full 1080×768 RGB numpy arrays.
    Each frame = panel_bg copy + character drawn on top via RGBA composite.
    """
    print(f"  Generating {num_frames} character frames ({'speaking' if speaking else 'idle'})...")
    frames = []
    for i in range(num_frames):
        # Start from a copy of the panel background
        panel = Image.fromarray(panel_bg.copy(), "RGB")

        # Draw character onto a transparent canvas
        canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        _draw_character_on_canvas(canvas, speaking, i, num_frames, custom_img)

        # Composite: paste RGBA character onto RGB panel
        panel.paste(canvas, (CHAR_PASTE_X, CHAR_PASTE_Y), canvas)
        frames.append(np.array(panel))

    return frames


def build_character_clip(
    speaking: bool,
    duration: float,
    panel_bg: np.ndarray,
    custom_img: Image.Image | None = None,
) -> ImageSequenceClip:
    """Build a looping ImageSequenceClip at 24fps for the character panel."""
    frames = generate_panel_frames(speaking, panel_bg, ANIMATION_FRAMES, custom_img)
    clip = ImageSequenceClip(frames, fps=FPS)
    clip = clip.fx(vfx.loop, duration=duration)
    del frames
    gc.collect()
    return clip


# ─────────────────────────── subtitles ──────────────────────────────────────

def chunk_script(script: str, words_per_chunk: int = 6) -> list[str]:
    words = script.split()
    return [" ".join(words[i:i + words_per_chunk]) for i in range(0, len(words), words_per_chunk)]


def assign_subtitle_timings(chunks: list[str], total_audio_duration: float) -> list[dict]:
    total_words = sum(len(c.split()) for c in chunks)
    if total_words == 0:
        return []
    timings, cursor = [], 0.0
    for chunk in chunks:
        n = len(chunk.split())
        dur = (n / total_words) * total_audio_duration
        timings.append({"text": chunk, "start": cursor, "end": cursor + dur})
        cursor += dur
    return timings


def render_subtitle_frame(text: str) -> np.ndarray:
    """Returns (160, 1080, 3) uint8 numpy array — one subtitle bar."""
    img = Image.new("RGBA", (1080, SUBTITLE_H), (10, 10, 20, 230))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(str(FONT_FILE), 48)
    except IOError:
        font = ImageFont.load_default()
    # Stroke effect: black outline at 8 offsets, then white text
    for dx, dy in [(-3, -3), (-3, 3), (3, -3), (3, 3), (-3, 0), (3, 0), (0, -3), (0, 3)]:
        d.text((540 + dx, 80 + dy), text, fill="black", font=font, anchor="mm")
    d.text((540, 80), text, fill="white", font=font, anchor="mm")
    return np.array(img.convert("RGB"))


def build_subtitle_clips(timings: list[dict]) -> list[ImageClip]:
    clips = []
    for t in timings:
        arr = render_subtitle_frame(t["text"])
        dur = max(0.1, t["end"] - t["start"])
        clip = (
            ImageClip(arr)
            .set_duration(dur)
            .set_start(t["start"])
        )
        clips.append(clip)
    return clips


# ─────────────────────────── gameplay selection ──────────────────────────────

def get_rotgen_gameplay() -> str | None:
    # 1. Local viral gameplay clips
    p = get_local_viral_gameplay()
    if p:
        return p
    # 2. Local normal gameplay
    p = get_local_gameplay("short")
    if p:
        return p
    # 3. Pexels fallback — try each query
    for query in ROTGEN_PEXELS_QUERIES:
        print(f"  Trying Pexels: '{query}'...")
        p = get_relevant_pexels_video(query, "short")
        if p:
            return p
    print("  No gameplay found — using dark fallback background.")
    return None


def build_gameplay_clip(bg_path: str | None, duration: float):
    """Return a 1080×992 clip (VideoFileClip or dark ColorClip), looped to duration."""
    if bg_path:
        try:
            raw = VideoFileClip(bg_path)
            # Handle landscape vs portrait source
            src_w, src_h = raw.size
            if src_w > src_h:
                # Landscape (e.g. 1920×1080) — crop to centre portrait region
                crop_x = (src_w - src_h * 1080 // 992) // 2
                raw = raw.crop(x1=max(0, crop_x), y1=0,
                               x2=min(src_w, crop_x + src_h * 1080 // 992), y2=src_h)
            clip = raw.resize((1080, GAMEPLAY_H))
            if clip.duration < duration:
                clip = clip.fx(vfx.loop, duration=duration)
            else:
                clip = clip.subclip(0, duration)
            clip = clip.fx(vfx.colorx, 0.55)   # darken so character stands out
            return clip
        except Exception as e:
            print(f"  Gameplay load error ({e}), using dark fallback.")
    # Fallback: solid dark colour
    return ColorClip(size=(1080, GAMEPLAY_H), color=(10, 10, 30)).set_duration(duration)


# ─────────────────────────── final composite ────────────────────────────────

def compose_rotgen_video(
    character_clip,
    gameplay_clip,
    subtitle_clips: list,
    audio_clip,
    output_path: Path,
) -> None:
    """Layer order (bottom → top): gameplay | character panel | subtitle clips."""
    game_pos  = gameplay_clip.set_position((0, PANEL_H))            # y=768
    char_pos  = character_clip.set_position((0, 0))                 # y=0
    sub_clips = [sc.set_position((0, PANEL_H + GAMEPLAY_H))         # y=1760
                 for sc in subtitle_clips]

    all_clips = [game_pos, char_pos] + sub_clips
    composite = CompositeVideoClip(all_clips, size=(VIDEO_W, VIDEO_H))

    # Audio mix: TTS loud + gentle bg music
    if BACKGROUND_MUSIC_PATH.exists():
        bg_music = AudioFileClip(str(BACKGROUND_MUSIC_PATH)).volumex(0.18)
        if bg_music.duration < composite.duration:
            bg_music = bg_music.fx(vfx.loop, duration=composite.duration)
        else:
            bg_music = bg_music.subclip(0, composite.duration)
        final_audio = CompositeAudioClip([audio_clip.volumex(1.3), bg_music])
    else:
        final_audio = audio_clip.volumex(1.3)

    composite.set_audio(final_audio).write_videofile(
        str(output_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        audio_bitrate="192k",
        preset="ultrafast",
        threads=3,
        logger="bar",
    )
    print(f"  Saved: {output_path.name}")


# ─────────────────────────── main entry ─────────────────────────────────────

def run_rotgen_pipeline() -> None:
    """RotGen Character Mode — fully auto-pilot brain rot video."""
    print("\n  ByteBot RotGen — AI Character Mode\n")
    ensure_dirs()

    # ── Script ───────────────────────────────────────────────────────────────
    topic       = random.choice(VIRAL_TOPICS)
    script_data = generate_rotgen_script(topic)
    script_text = strip_emojis(script_data.get("script", ""))
    title       = script_data.get("title", topic)[:100]
    hashtags    = script_data.get("hashtags", "#AI #Shorts #ByteBot")

    if not script_text.strip():
        print("  No script generated.")
        return

    print(f"  Script ({len(script_text.split())} words): {script_text[:80]}...")

    # ── TTS ───────────────────────────────────────────────────────────────────
    unique_id  = datetime.datetime.now().strftime("rotgen_%Y%m%d_%H%M%S")
    audio_src  = OUTPUT_DIR / f"{unique_id}_vo.mp3"
    audio_path = text_to_speech(script_text, audio_src)
    audio_clip = AudioFileClip(str(audio_path))
    total_dur  = audio_clip.duration
    print(f"  Audio duration: {total_dur:.1f}s")

    # ── Character clip ────────────────────────────────────────────────────────
    panel_bg   = _build_panel_background()
    custom_img = _load_custom_character()
    print("  Building character animation...")
    char_clip  = build_character_clip(
        speaking=True,
        duration=total_dur,
        panel_bg=panel_bg,
        custom_img=custom_img,
    )

    # ── Subtitles ─────────────────────────────────────────────────────────────
    print("  Building subtitles...")
    chunks        = chunk_script(script_text)
    timings       = assign_subtitle_timings(chunks, total_dur)
    sub_clips     = build_subtitle_clips(timings)
    print(f"  {len(sub_clips)} subtitle chunks")

    # ── Gameplay ──────────────────────────────────────────────────────────────
    print("  Selecting gameplay video...")
    bg_path       = get_rotgen_gameplay()
    gameplay_clip = build_gameplay_clip(bg_path, total_dur)

    # ── Compose + encode ──────────────────────────────────────────────────────
    output_path = OUTPUT_DIR / f"{unique_id}.mp4"
    print(f"\n  Composing video → {output_path.name}")
    compose_rotgen_video(char_clip, gameplay_clip, sub_clips, audio_clip, output_path)

    # ── Log ───────────────────────────────────────────────────────────────────
    plan = load_rotgen_plan()
    plan["videos"].append({
        "title":      title,
        "topic":      topic,
        "path":       str(output_path),
        "created_at": datetime.date.today().isoformat(),
        "status":     "complete",
    })
    save_rotgen_plan(plan)

    print(f"\n  ByteBot video complete!")
    print(f"  Title:    {title}")
    print(f"  Hashtags: {hashtags}")
    print(f"  File:     {output_path}")
