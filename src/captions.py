# src/captions.py — Universal subtitle overlay system
# Used by generator.compose_video, brainrot.create_brainrot_video,
# and (optionally) rotgen.compose_rotgen_video.
#
# Renders timed word-chunk subtitles as PIL images, positions them within
# the YouTube safe zone (~10% from edges), and composites them over any
# base MoviePy clip.

import re
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, CompositeVideoClip

FONT_FILE = Path("assets/fonts/arial.ttf")

SUBTITLE_H        = 160     # height of subtitle bar
SAFE_BOTTOM_SHORT = 190     # px from bottom for 9:16 → bar starts y=1570
SAFE_BOTTOM_LONG  = 60      # px from bottom for 16:9 → bar starts y=860
WORDS_PER_CHUNK   = 4


def chunk_script(text: str, words_per_chunk: int = WORDS_PER_CHUNK) -> list:
    """Split script into N-word chunks for timed subtitle display."""
    words = re.sub(r'\s+', ' ', text.strip()).split()
    if not words:
        return []
    return [' '.join(words[i:i + words_per_chunk])
            for i in range(0, len(words), words_per_chunk)]


def assign_timings(chunks: list, total_dur: float) -> list:
    """Assign start/end timestamps proportional to word count of each chunk."""
    if not chunks or total_dur <= 0:
        return []
    total_words = sum(len(c.split()) for c in chunks) or 1
    t = 0.0
    out = []
    for c in chunks:
        dur = (len(c.split()) / total_words) * total_dur
        out.append((c, t, min(t + dur, total_dur)))
        t += dur
    return out


def render_subtitle_frame(text: str, video_w: int, subtitle_h: int = SUBTITLE_H) -> np.ndarray:
    """
    PIL-rendered subtitle bar — semi-transparent black bg + white text + black stroke.
    Auto-scales 36 → 20 px to fit video width, falls back to 2-line wrap.
    Returns RGBA numpy array suitable for MoviePy ImageClip.
    """
    img = Image.new("RGBA", (video_w, subtitle_h), (0, 0, 0, 190))
    d = ImageDraw.Draw(img)
    MAX_W = video_w - 80     # 40 px margin each side

    chosen_font = None
    chosen_lines = None

    for size in range(36, 19, -2):
        try:
            f = ImageFont.truetype(str(FONT_FILE), size)
        except (IOError, OSError):
            f = ImageFont.load_default()

        # Try single-line fit
        if d.textlength(text, font=f) <= MAX_W:
            chosen_font = f
            chosen_lines = [text]
            break

        # Try 2-line split at midpoint
        words = text.split()
        if len(words) >= 2:
            mid = max(1, len(words) // 2)
            l1 = ' '.join(words[:mid])
            l2 = ' '.join(words[mid:])
            if max(d.textlength(l1, font=f), d.textlength(l2, font=f)) <= MAX_W:
                chosen_font = f
                chosen_lines = [l1, l2]
                break

    if not chosen_font:
        # Force midpoint 2-line split so text never overflows MAX_W
        words = text.split()
        if len(words) >= 2:
            mid = max(1, len(words) // 2)
            chosen_lines = [' '.join(words[:mid]), ' '.join(words[mid:])]
        else:
            chosen_lines = [text]
        try:
            chosen_font = ImageFont.truetype(str(FONT_FILE), 20)
        except (IOError, OSError):
            chosen_font = ImageFont.load_default()

    line_h = (chosen_font.size if hasattr(chosen_font, 'size') else 20) + 6
    total_h = len(chosen_lines) * line_h
    start_y = (subtitle_h - total_h) // 2 + line_h // 2

    stroke_offsets = [(-2, -2), (-2, 2), (2, -2), (2, 2),
                      (-2, 0), (2, 0), (0, -2), (0, 2)]

    for i, line in enumerate(chosen_lines):
        x = video_w // 2
        y = start_y + i * line_h
        # Black stroke
        for dx, dy in stroke_offsets:
            d.text((x + dx, y + dy), line, fill=(0, 0, 0, 255),
                   font=chosen_font, anchor="mm")
        # White fill
        d.text((x, y), line, fill="white", font=chosen_font, anchor="mm")

    return np.array(img)


def add_subtitle_overlay(base_clip, script: str, video_type: str):
    """
    Wrap a MoviePy VideoClip with timed subtitle ImageClips.
    Returns a CompositeVideoClip with subtitles positioned within safe zone.

    Args:
        base_clip: MoviePy clip with .w, .h, .duration
        script:    Full text to chunk into subtitles
        video_type: 'short' (9:16) or 'long' (16:9)
    """
    if not script or not script.strip():
        return base_clip

    W, H = base_clip.w, base_clip.h
    safe = SAFE_BOTTOM_SHORT if video_type == 'short' else SAFE_BOTTOM_LONG
    sub_y = max(0, H - SUBTITLE_H - safe)

    chunks = chunk_script(script)
    timed  = assign_timings(chunks, base_clip.duration)
    if not timed:
        return base_clip

    sub_clips = []
    for text, start, end in timed:
        dur = end - start
        if dur <= 0:
            continue
        frame = render_subtitle_frame(text, W)
        clip = (ImageClip(frame)
                .set_start(start)
                .set_duration(dur)
                .set_position((0, sub_y)))
        sub_clips.append(clip)

    if not sub_clips:
        return base_clip

    return CompositeVideoClip([base_clip] + sub_clips, size=(W, H))
