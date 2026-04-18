import os
import random
from pathlib import Path
from tqdm import tqdm
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    AudioFileClip, ImageClip, VideoFileClip, 
    CompositeVideoClip, CompositeAudioClip, 
    concatenate_videoclips, vfx
)

from src.core.config import (
    FONT_FILE, YOUR_NAME, BACKGROUND_MUSIC_PATH, OUTPUT_DIR
)
from src.infrastructure.video import (
    get_local_background, get_local_gameplay, 
    get_local_viral_gameplay, get_relevant_pexels_video
)
from src.utils.cleanup import safe_close

def auto_scale_text(draw, text, font_path, start_size, box, fill="white", min_size=24):
    """Draw text centered in box, scaling down until it fits."""
    box_left, box_top, box_right, box_bottom = box
    max_w = (box_right - box_left) - 40
    max_h = (box_bottom - box_top) - 40
    
    size = start_size
    font = None
    lines = []
    
    while size >= min_size:
        try: f = ImageFont.truetype(font_path, size)
        except: f = ImageFont.load_default()
        
        # simple word wrap
        words = text.split()
        curr_lines = []
        curr_line = ""
        for w in words:
            test = (curr_line + " " + w).strip()
            if draw.textlength(test, font=f) <= max_w:
                curr_line = test
            else:
                curr_lines.append(curr_line)
                curr_line = w
        curr_lines.append(curr_line)
        
        line_h = size * 1.2
        if len(curr_lines) * line_h <= max_h:
            font = f
            lines = curr_lines
            break
        size -= 4
    
    if not font:
        font = ImageFont.load_default()
        lines = [text[:50]]
        size = 20

    line_h = size * 1.2
    total_h = len(lines) * line_h
    y = box_top + (max_h - total_h) // 2 + 20
    for line in lines:
        tw = draw.textlength(line, font=font)
        draw.text((box_left + (max_w+40-tw)//2, y), line, fill=fill, font=font)
        y += line_h

def draw_wrapped_text(draw, text, font, max_width, x, y, fill="white"):
    words = text.split()
    lines = []
    line = ""
    for w in words:
        if draw.textlength(line + " " + w, font=font) <= max_width:
            line = (line + " " + w).strip()
        else:
            lines.append(line)
            line = w
    lines.append(line)
    for l in lines:
        draw.text((x, y), l, fill=fill, font=font)
        y += font.size + 10

def generate_visuals(output_dir, video_type, slide_content=None,
                    slide_number=1, total_slides=1, is_thumbnail=False, thumbnail_title=""):
    """PIL rendering logic moved from God Module."""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    width, height = (1920, 1080) if video_type == 'long' else (1080, 1920)
    
    title = thumbnail_title if is_thumbnail else slide_content.get("title", "")
    final_bg = get_local_background(title, video_type)
    draw = ImageDraw.Draw(final_bg)
    
    try:
        title_font = ImageFont.truetype(str(FONT_FILE), 60 if video_type == 'long' else 70)
        content_font = ImageFont.truetype(str(FONT_FILE), 38 if video_type == 'long' else 44)
        footer_font = ImageFont.truetype(str(FONT_FILE), 24)
    except:
        title_font = content_font = footer_font = ImageFont.load_default()

    if not is_thumbnail:
        # Title box
        draw.text((80, 80), title.upper(), fill=(0, 200, 255), font=title_font)
        # Content box
        content_text = slide_content.get("content", "")
        draw_wrapped_text(draw, content_text, content_font, width - 160, 80, 180)
        # Footer
        footer_y = height - 80
        footer_text = f"AI for Developers by {YOUR_NAME} • Slide {slide_number}/{total_slides}"
        draw.text((width//2, footer_y), footer_text, fill="white", font=footer_font, anchor="mm")
    else:
        thumb_box = (60, height // 4, width - 60, 3 * height // 4)
        auto_scale_text(draw, title, str(FONT_FILE), 80 if video_type == 'long' else 90, thumb_box)
        
    file_prefix = "thumbnail" if is_thumbnail else f"slide_{slide_number:02d}"
    path = output_dir / f"{file_prefix}.png"
    final_bg.save(path)
    final_bg.close()
    return str(path)

def compose_video(slide_paths, audio_paths, output_path, video_type, lesson_title,
                  is_tutorial=False, force_viral_bg=False, script=None, bg_query=None):
    """OPTIMIZED dynamic video composition logic."""
    label = 'Tutorial' if is_tutorial else ('Viral' if force_viral_bg else 'Dynamic')
    print(f"🎥 Creating {label} {video_type} video for: {lesson_title}")

    STATIC_MODE = False
    bg_music = None
    bg_clip = None
    final_video = None
    audio_clips_to_close = []
    image_clips = []

    try:
        if not slide_paths or not audio_paths or len(slide_paths) != len(audio_paths):
            raise ValueError("Slide/audio mismatch")

        query = bg_query if bg_query else lesson_title
        if force_viral_bg:
            bg_path = get_local_viral_gameplay() or get_relevant_pexels_video(query, video_type)
        else:
            bg_path = get_relevant_pexels_video(query, video_type)
        if not bg_path:
            bg_path = get_local_gameplay(video_type)

        _dur_clips = [AudioFileClip(str(a)) for a in audio_paths]
        total_duration = sum(c.duration for c in _dur_clips) + 0.5 * len(audio_paths)
        safe_close(_dur_clips)

        if bg_path and not STATIC_MODE:
            bg_clip = VideoFileClip(bg_path)
            if bg_clip.duration < total_duration:
                bg_clip = bg_clip.fx(vfx.loop, duration=total_duration)
            else:
                bg_clip = bg_clip.subclip(0, total_duration)
            bg_clip = bg_clip.fx(vfx.colorx, 0.78)
            bg_clip = bg_clip.resize(1.06).set_position(lambda t: (0 + (t * 2), 0 + (t * 1.2)))

        image_clips = []
        for i, (img_path, audio_path) in enumerate(zip(slide_paths, audio_paths)):
            audio_clip = AudioFileClip(str(audio_path))
            audio_clips_to_close.append(audio_clip)
            duration = audio_clip.duration + 0.5
            img_clip = ImageClip(str(img_path)).set_duration(duration).fadein(0.5).fadeout(0.5)

            target_size = (1920, 1080) if video_type == 'long' else (1080, 1920)
            if bg_clip:
                final_clip = CompositeVideoClip([
                    bg_clip.subclip(0, min(duration, bg_clip.duration)),
                    img_clip.set_opacity(0.93).set_position('center')
                ], size=target_size)
            else:
                final_clip = CompositeVideoClip([img_clip], size=target_size)

            final_clip = final_clip.set_audio(audio_clip)
            image_clips.append(final_clip)

        final_video = concatenate_videoclips(image_clips, method="compose")

        if script:
            try:
                from src.captions import add_subtitle_overlay
                final_video = add_subtitle_overlay(final_video, script, video_type)
            except Exception as e:
                print(f"⚠️ Subtitle overlay failed ({e})")

        if BACKGROUND_MUSIC_PATH.exists():
            bg_music = AudioFileClip(str(BACKGROUND_MUSIC_PATH)).volumex(0.15)
            if bg_music.duration < final_video.duration:
                from moviepy.audio.fx.audio_loop import audio_loop
                bg_music = audio_loop(bg_music, duration=final_video.duration)
            else:
                bg_music = bg_music.subclip(0, final_video.duration)
            if final_video.audio:
                final_video = final_video.set_audio(CompositeAudioClip([final_video.audio.volumex(1.2), bg_music]))
            else:
                final_video = final_video.set_audio(bg_music)

        temp_audio = str(output_path).replace('.mp4', 'TEMP_MPY_wvf_snd.mp4')
        final_video.write_videofile(
            str(output_path),
            fps=24,
            codec="libx264",
            audio_codec="aac",
            audio_bitrate="192k",
            preset="ultrafast",
            threads=3,
            logger='bar',
            temp_audiofile=temp_audio,
        )
    finally:
        safe_close(audio_clips_to_close, image_clips, final_video, bg_clip, bg_music)
