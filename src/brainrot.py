"""src/brainrot.py - Brain Rot / High-Engagement Viral Shorts Generator"""
import json
import os
import random
import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import (
    AudioFileClip, ImageClip, VideoFileClip,
    CompositeVideoClip, CompositeAudioClip,
    concatenate_videoclips, vfx
)
from tqdm import tqdm

from src.generator import (
    ollama_generate,
    text_to_speech,
    strip_emojis,
    get_local_gameplay,
    get_relevant_pexels_video,
    get_local_background,
    auto_scale_text,
    draw_wrapped_text,
    get_encoder_kwargs,
    FONT_FILE,
    ASSETS_PATH,
    YOUR_NAME,
    BACKGROUNDS_PATH,
    GAMEPLAY_PATH,
    BACKGROUND_MUSIC_PATH,
    PEXELS_CACHE_DIR,
)

BRAINROT_PLAN_FILE = Path("brainrot_plan.json")
OUTPUT_DIR = Path("output")

# Attention-grabbing color palettes
BRAINROT_PALETTES = [
    {"bg": (20, 20, 20),    "text": "white",   "accent": (255, 30, 80),   "bar": (255, 30, 80)},
    {"bg": (10, 10, 40),    "text": "white",   "accent": (0, 200, 255),   "bar": (0, 180, 220)},
    {"bg": (30, 0, 50),     "text": "white",   "accent": (180, 0, 255),   "bar": (140, 0, 200)},
    {"bg": (40, 20, 0),     "text": "white",   "accent": (255, 150, 0),   "bar": (200, 100, 0)},
    {"bg": (0, 35, 20),     "text": "white",   "accent": (0, 220, 100),   "bar": (0, 180, 80)},
]


def load_brainrot_plan():
    if not BRAINROT_PLAN_FILE.exists():
        return {"topics": []}
    try:
        with open(BRAINROT_PLAN_FILE) as f:
            return json.load(f)
    except Exception:
        return {"topics": []}


def save_brainrot_plan(plan):
    with open(BRAINROT_PLAN_FILE, 'w') as f:
        json.dump(plan, f, indent=2)


def generate_brainrot_topics(count=10, previous_topics=None):
    """Generate viral short-form AI topics with hooks and curiosity gaps."""
    print("🧠 Generating brain rot topics...")
    history = ""
    if previous_topics:
        formatted = "\n".join(f"- {t}" for t in previous_topics)
        history = f"\nAlready created:\n{formatted}\n\nCreate NEW topics, don't repeat.\n"

    prompt = f"""You are a viral content strategist for AI/tech YouTube Shorts.
{history}
Generate {count} SHORT video topic ideas that are:
- Sensationalized but factually grounded
- Use curiosity gaps: "This AI can...", "Nobody talks about...", "Why X is secretly..."
- Cover TRENDING AI: GPT models, open source LLMs, AI taking jobs, local AI, deepfakes, AI agents, AI coding, AI vs humans
- Each topic works as a video under 60 seconds
- Mix shocking facts, controversial takes, and mind-blowing reveals

Return ONLY valid JSON:
{{
  "topics": [
    {{
      "title": "short clickbait title",
      "hook": "first 2 seconds — 1 shocking sentence",
      "angle": "the specific take/angle to cover"
    }}
  ]
}}"""
    result = ollama_generate(prompt, json_mode=True)
    return result.get("topics", [])


def generate_brainrot_script(topic):
    """Generate punchy meme-like script for a brain rot short."""
    from src.learning import get_learning_context
    print(f"📝 Scripting: '{topic['title']}'...")
    learning_context = get_learning_context()
    prompt = f"""You are writing a viral 30-45 second YouTube Short script about AI.

Topic: {topic['title']}
Hook: {topic['hook']}
Angle: {topic['angle']}
{learning_context}
Rules:
- Total script UNDER 80 words
- First sentence = the HOOK (instant curiosity, shocking)
- Short punchy sentences. No academic language.
- Use "you" and "your" to speak directly to viewer
- Include 1 "wait, what?" moment
- End with controversial statement OR "follow for more"
- 4 slides total: hook, point 1, point 2, CTA

Return ONLY valid JSON:
{{
  "slides": [
    {{"text": "hook text — 1-2 sentences max", "duration_hint": "short"}},
    {{"text": "main point 1 — 1-2 sentences", "duration_hint": "medium"}},
    {{"text": "main point 2 — 1-2 sentences", "duration_hint": "medium"}},
    {{"text": "CTA or mind-blow — 1 sentence", "duration_hint": "short"}}
  ],
  "full_script": "complete narration under 80 words",
  "title": "YouTube title with emoji",
  "hashtags": "#AI #Shorts #Tech"
}}"""
    result = ollama_generate(prompt, json_mode=True)
    # Validate minimal structure
    if not result.get("slides") or not result.get("full_script"):
        result = {
            "slides": [
                {"text": topic["hook"], "duration_hint": "short"},
                {"text": topic["angle"], "duration_hint": "medium"},
                {"text": "AI is changing everything. Are you ready?", "duration_hint": "short"},
                {"text": "Follow for more AI facts. 🔥", "duration_hint": "short"},
            ],
            "full_script": f"{topic['hook']} {topic['angle']} AI is changing everything. Follow for more.",
            "title": f"{topic['title']} 🤯",
            "hashtags": "#AI #Shorts #Tech #AIFacts",
        }
    return result


def render_brainrot_slide(output_dir, text, slide_index, total_slides, palette=None):
    """Render a single brain rot slide — bold, centered, full-frame with text stroke."""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    width, height = 1080, 1920

    if palette is None:
        palette = random.choice(BRAINROT_PALETTES)

    # Background: dark gradient via solid + gradient layer
    img = Image.new('RGBA', (width, height), palette["bg"])

    # Add subtle vignette / gradient overlay — numpy (285x faster than pixel loop)
    arr = np.zeros((height, width, 4), dtype=np.uint8)
    ys = np.arange(height)
    alpha_col = (120 * (np.abs(ys - height / 2) / (height / 2)) ** 1.5).clip(0, 255).astype(np.uint8)
    arr[:, :, 3] = alpha_col[:, np.newaxis]   # broadcast across width
    gradient = Image.fromarray(arr, 'RGBA')

    img = Image.alpha_composite(img, gradient)

    # Accent bar at bottom (branding)
    draw = ImageDraw.Draw(img)
    bar_h = 80
    draw.rectangle([0, height - bar_h, width, height], fill=(*palette["accent"][:3], 220))
    try:
        brand_font = ImageFont.truetype(str(FONT_FILE), 28)
    except IOError:
        brand_font = ImageFont.load_default()
    brand_text = f"AI for Developers by {YOUR_NAME} • #{slide_index}/{total_slides}"
    bw = draw.textlength(brand_text, font=brand_font)
    draw.text(((width - bw) / 2, height - bar_h + 22), brand_text, fill="white", font=brand_font)

    # Content box — center of frame, leaving room for brand bar
    margin = 60
    content_box = (margin, 100, width - margin, height - bar_h - 60)

    # Text stroke effect: draw text in black at 8 offsets, then white on top
    def draw_outlined_text(d, txt, font_path, start_size, box, text_color="white"):
        box_left, box_top, box_right, box_bottom = box
        max_w = (box_right - box_left) - 40
        avail_h = (box_bottom - box_top) - 40

        # Find fitting size
        size = start_size
        chosen_font = None
        chosen_lines = None
        while size >= 24:
            try:
                f = ImageFont.truetype(font_path, size)
            except IOError:
                f = ImageFont.load_default()
            ls = int(size * 1.35)
            lines = []
            for para in txt.split('\n'):
                words = para.split()
                if not words:
                    lines.append("")
                    continue
                line = ""
                for word in words:
                    tl = (line + " " + word).strip()
                    if d.textlength(tl, font=f) <= max_w:
                        line = tl
                    else:
                        if line:
                            lines.append(line)
                        if d.textlength(word, font=f) > max_w:
                            chunk = ""
                            for ch in word:
                                if d.textlength(chunk + ch + "-", font=f) > max_w:
                                    lines.append(chunk + "-")
                                    chunk = ch
                                else:
                                    chunk += ch
                            line = chunk
                        else:
                            line = word
                if line:
                    lines.append(line)
            total_h = len(lines) * ls
            if total_h <= avail_h:
                chosen_font = f
                chosen_lines = lines
                break
            size -= 4

        if not chosen_font:
            chosen_font = ImageFont.truetype(font_path, 24) if Path(font_path).exists() else ImageFont.load_default()
            chosen_lines = [txt[:60]]
            ls = int(24 * 1.35)

        total_h = len(chosen_lines) * ls
        y_start = box_top + (avail_h - total_h) // 2 + 20

        for line_txt in chosen_lines:
            tw = d.textlength(line_txt, font=chosen_font)
            x = box_left + ((box_right - box_left) - tw) / 2
            # Stroke (outline)
            for dx, dy in [(-3, -3), (-3, 3), (3, -3), (3, 3), (-3, 0), (3, 0), (0, -3), (0, 3)]:
                d.text((x + dx, y_start + dy), line_txt, fill="black", font=chosen_font)
            # Main text
            d.text((x, y_start), line_txt, fill=text_color, font=chosen_font)
            y_start += ls

    draw_outlined_text(draw, text, str(FONT_FILE), 90, content_box, text_color=palette["text"])

    path = output_dir / f"slide_{slide_index:02d}.png"
    img.convert("RGB").save(path)
    print(f"🎨 Brain rot slide saved: {path.name}")
    return str(path)


def create_brainrot_video(slide_paths, audio_paths, output_path, title):
    """Compose brain rot video: fast pacing, dynamic bg, high music vol."""
    print(f"🎥 Creating brain rot video: {title}")
    try:
        if not slide_paths or not audio_paths or len(slide_paths) != len(audio_paths):
            raise ValueError("Slide/audio count mismatch")

        # Prefer viral gameplay, then normal gameplay, then Pexels
        from src.generator import get_local_viral_gameplay
        bg_path = get_local_viral_gameplay() or get_local_gameplay('short')
        if not bg_path:
            for query in ["satisfying", "gaming", "coding", "technology"]:
                bg_path = get_relevant_pexels_video(query, 'short')
                if bg_path:
                    break

        total_duration = sum(AudioFileClip(str(a)).duration for a in audio_paths) + 0.3 * len(audio_paths)

        if bg_path:
            print(f"🎮 Background: {Path(bg_path).name}")
            bg_clip = VideoFileClip(bg_path)
            if bg_clip.duration < total_duration:
                bg_clip = bg_clip.fx(vfx.loop, duration=total_duration)
            else:
                bg_clip = bg_clip.subclip(0, total_duration)
            bg_clip = bg_clip.fx(vfx.colorx, 0.6)
        else:
            bg_clip = None

        clips = []
        pairs = list(zip(slide_paths, audio_paths))
        for i, (img_path, audio_path) in enumerate(tqdm(pairs, desc="  Building clips", unit="clip", leave=False,
                                                         bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")):
            audio_clip = AudioFileClip(str(audio_path))
            duration = audio_clip.duration + 0.3
            img_clip = ImageClip(str(img_path)).set_duration(duration).fadein(0.2).fadeout(0.2)

            if bg_clip:
                segment = CompositeVideoClip([
                    bg_clip.set_duration(duration),
                    img_clip.set_opacity(0.88).set_position('center')
                ])
            else:
                segment = img_clip

            segment = segment.set_audio(audio_clip)
            clips.append(segment)

        final = concatenate_videoclips(clips, method="compose")

        if BACKGROUND_MUSIC_PATH.exists():
            print("🎵 Adding music...")
            bg_music = AudioFileClip(str(BACKGROUND_MUSIC_PATH)).volumex(0.25)
            if bg_music.duration < final.duration:
                bg_music = bg_music.fx(vfx.loop, duration=final.duration)
            else:
                bg_music = bg_music.subclip(0, final.duration)
            composite_audio = CompositeAudioClip([final.audio.volumex(1.2), bg_music])
            final = final.set_audio(composite_audio)

        print(f"🎬 Encoding → {Path(output_path).name}")
        try:
            final.write_videofile(
                str(output_path),
                fps=24,
                **get_encoder_kwargs(),
            )
            print(f"✅ Brain rot video saved: {Path(output_path).name}")
        finally:
            for c in clips:
                try: c.close()
                except Exception: pass
            for attr in ("audio",):
                try:
                    getattr(final, attr, None) and final.audio.close()
                except Exception: pass
            try: final.close()
            except Exception: pass
            if bg_clip is not None:
                try: bg_clip.close()
                except Exception: pass

    except Exception as e:
        print(f"❌ Brain rot video error: {e}")
        import traceback
        traceback.print_exc()
        raise


def run_brainrot_pipeline():
    """Main entry point: generate and upload brain rot shorts."""
    print("🧠 Starting Brain Rot Shorts Pipeline...")
    OUTPUT_DIR.mkdir(exist_ok=True)

    plan = load_brainrot_plan()
    pending = [t for t in plan["topics"] if t.get("status") == "pending"]

    if not pending:
        print("📋 No pending topics. Generating new batch...")
        prev_titles = [t["title"] for t in plan["topics"]]
        new_topics = generate_brainrot_topics(count=10, previous_topics=prev_titles if prev_titles else None)
        for t in new_topics:
            plan["topics"].append({
                "title": t.get("title", "AI Fact"),
                "hook": t.get("hook", ""),
                "angle": t.get("angle", ""),
                "status": "pending",
                "youtube_id": None,
                "created_at": datetime.date.today().isoformat(),
            })
        save_brainrot_plan(plan)
        pending = [t for t in plan["topics"] if t.get("status") == "pending"]

    from src.browser_uploader import upload_to_youtube_browser
    import menu

    shorts_this_run = menu.ask_count("brainrot", "Brain rot shorts this run", 3)
    batch = pending[:shorts_this_run]
    processed = 0
    for topic in tqdm(batch, desc="Brain Rot Shorts", unit="short",
                      bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} shorts [{elapsed}<{remaining}]"):
        try:
            print(f"\n▶️  Topic: '{topic['title']}'")
            script = generate_brainrot_script(topic)

            unique_id = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            slide_dir = OUTPUT_DIR / f"brainrot_{unique_id}"
            palette = random.choice(BRAINROT_PALETTES)
            slides_data = script.get("slides", [])

            full_script = strip_emojis(script.get("full_script", " ".join(s["text"] for s in slides_data)))

            # Per-slide TTS + visuals in parallel (preserves slide order)
            total_slides = len(slides_data)
            slide_audio_paths = [None] * total_slides
            slide_image_paths = [None] * total_slides

            def _produce_slide(idx, slide):
                slide_text = strip_emojis(slide.get("text", ""))
                audio = text_to_speech(slide_text,
                                       OUTPUT_DIR / f"brainrot_s{idx+1}_{unique_id}.mp3")
                img = render_brainrot_slide(
                    slide_dir, slide_text, idx + 1, total_slides, palette=palette
                )
                return audio, img

            from src.hardware import max_parallel_slides
            with ThreadPoolExecutor(max_workers=max_parallel_slides()) as pool:
                futures = {pool.submit(_produce_slide, idx, s): idx
                           for idx, s in enumerate(slides_data)}
                for fut in tqdm(futures, desc="  Slides", unit="slide", leave=False,
                                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"):
                    idx = futures[fut]
                    slide_audio_paths[idx], slide_image_paths[idx] = fut.result()

            video_path = OUTPUT_DIR / f"brainrot_video_{unique_id}.mp4"
            create_brainrot_video(slide_image_paths, slide_audio_paths, video_path, topic["title"])

            # Upload
            title = script.get("title", topic["title"])[:100]
            hashtags = script.get("hashtags", "#AI #Shorts #Tech")
            desc = f"{full_script}\n\n{hashtags}\n\nAI for Developers by {YOUR_NAME}"
            tags = "AI,Shorts,Tech,BrainRot,AIFacts"

            print(f"\n📤 Uploading: {title}")
            video_id = upload_to_youtube_browser(video_path, title, desc, tags)
            if video_id:
                from src.learning import log_upload
                from src.artefacts import record_and_cleanup
                log_upload(title, video_id, "brainrot")
                record_and_cleanup(
                    mode="brainrot",
                    title=title,
                    video_id=video_id,
                    video_path=video_path,
                    audio_paths=slide_audio_paths,
                    slide_dir=slide_dir,
                )

            # Mark complete
            for t in plan["topics"]:
                if t["title"] == topic["title"]:
                    t["status"] = "complete"
                    t["youtube_id"] = video_id or "UPLOAD_ATTEMPTED"
                    break
            save_brainrot_plan(plan)
            print(f"✅ Done: {topic['title']}")
            processed += 1

        except Exception as e:
            print(f"❌ Failed topic '{topic['title']}': {e}")
            import traceback
            traceback.print_exc()
        finally:
            import gc
            gc.collect()

    print(f"\n🏁 Brain Rot Pipeline complete. Processed {processed} shorts.")
    try:
        from src.learning import suggest_improvements
        suggest_improvements()
    except Exception as e:
        print(f"⚠️ Learning refresh skipped: {e}")
