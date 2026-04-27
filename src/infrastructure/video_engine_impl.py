import logging
import os
import random
import math
import gc
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Tuple

logger = logging.getLogger(__name__)
from tqdm import tqdm
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import (
    AudioFileClip, ImageClip, VideoFileClip, 
    CompositeVideoClip, CompositeAudioClip, 
    concatenate_videoclips, ImageSequenceClip, ColorClip, vfx
)

from src.core.config import (
    FONT_FILE, YOUR_NAME, BACKGROUND_MUSIC_PATH, OUTPUT_DIR,
    LOW_MEMORY_MODE, VIDEO_THREADS, VIDEO_FPS, LONG_VIDEO_SIZE, SHORT_VIDEO_SIZE,
    ASSETS_PATH, BACKGROUNDS_PATH, VideoOptions
)
from src.infrastructure.video import (
    get_local_background, get_local_gameplay, 
    get_local_viral_gameplay, get_relevant_pexels_video
)
from src.utils.cleanup import safe_close
from src.core.interfaces import IVideoEngine, IBRollSelector

# Brainrot Constants
BRAINROT_PALETTES = [
    {"bg": (20, 20, 20),    "text": "white",   "accent": (255, 30, 80),   "bar": (255, 30, 80)},
    {"bg": (10, 10, 40),    "text": "white",   "accent": (0, 200, 255),   "bar": (0, 180, 220)},
    {"bg": (30, 0, 50),     "text": "white",   "accent": (180, 0, 255),   "bar": (140, 0, 200)},
    {"bg": (40, 20, 0),     "text": "white",   "accent": (255, 150, 0),   "bar": (200, 100, 0)},
    {"bg": (0, 35, 20),     "text": "white",   "accent": (0, 220, 100),   "bar": (0, 180, 80)},
]

# Rotgen Constants
CHARACTERS_PATH    = ASSETS_PATH / "characters"
CANVAS_W, CANVAS_H = 400, 500      # character drawing canvas
VIDEO_W,  VIDEO_H  = SHORT_VIDEO_SIZE
PANEL_W,  PANEL_H  = VIDEO_W, int(VIDEO_H * 0.4)     # character panel (top of frame)
SUBTITLE_H         = int(VIDEO_H * 0.0833)
GAMEPLAY_H         = VIDEO_H - PANEL_H - SUBTITLE_H
FPS                = VIDEO_FPS
ANIMATION_FRAMES   = FPS * 2             # 2-second loop

CHAR_PASTE_X = (PANEL_W - CANVAS_W) // 2   # 340
CHAR_PASTE_Y = (PANEL_H - CANVAS_H) // 2   # 134

SKIN  = (255, 220, 170)
BLUE  = (30,  120, 220)
DARK  = (40,   30,  20)

ROTGEN_PEXELS_QUERIES = [
    "subway surfers parkour",
    "minecraft gameplay",
    "satisfying sand cutting",
    "mobile endless runner game",
    "hypnotic satisfying craft",
]

def auto_scale_text(draw: ImageDraw.ImageDraw, text: str, font_path: str, start_size: int, box: Tuple[int, int, int, int], fill: str = "white", min_size: int = 24) -> None:
    """Draw text centered in box, scaling down until it fits."""
    box_left, box_top, box_right, box_bottom = box
    max_w = (box_right - box_left) - 40
    max_h = (box_bottom - box_top) - 40
    
    size = start_size
    font = None
    lines = []
    
    while size >= min_size:
        try: f = ImageFont.truetype(font_path, size)
        except Exception as e: f = ImageFont.load_default()
        
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

def draw_wrapped_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int, x: int, y: int, fill: str = "white") -> None:
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

class StandardVideoEngine(IVideoEngine):
    """Standard implementation of the video engine using PIL and MoviePy."""

    def __init__(self, broll_selector: Optional[IBRollSelector] = None) -> None:
        self.broll_selector = broll_selector

    def generate_visuals(self, output_dir: Union[str, Path], video_type: str, slide_content: Optional[Dict[str, Any]] = None,
                        slide_number: int = 1, total_slides: int = 1, is_thumbnail: bool = False, thumbnail_title: str = "") -> str:
        """PIL rendering logic moved from God Module."""
        slide_content = slide_content or {}
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
        width, height = LONG_VIDEO_SIZE if video_type == 'long' else SHORT_VIDEO_SIZE

        title = thumbnail_title if is_thumbnail else slide_content.get("title", "")
        final_bg = get_local_background(title, video_type)
        draw = ImageDraw.Draw(final_bg)
        
        try:
            title_font = ImageFont.truetype(str(FONT_FILE), 60 if video_type == 'long' else 70)
            content_font = ImageFont.truetype(str(FONT_FILE), 38 if video_type == 'long' else 44)
            footer_font = ImageFont.truetype(str(FONT_FILE), 24)
        except Exception as e:
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

    def generate_brainrot_slide(self, output_dir: Union[str, Path], text: str, slide_num: int, total_slides: int, palette: Optional[Dict[str, Any]] = None) -> str:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
        width, height = SHORT_VIDEO_SIZE
        if not palette: palette = random.choice(BRAINROT_PALETTES)
        
        img = Image.new('RGB', (width, height), palette["bg"])
        draw = ImageDraw.Draw(img)
        
        # 1. Background image (blurred)
        try:
            bg_files = list(BACKGROUNDS_PATH.glob("*.jpg")) + list(BACKGROUNDS_PATH.glob("*.png"))
            if bg_files:
                bg = Image.open(random.choice(bg_files)).convert('RGB')
                bg = bg.resize((width, height), Image.Resampling.LANCZOS)
                bg = bg.filter(ImageFilter.GaussianBlur(radius=15))
                img.paste(bg, (0, 0))
        except Exception as e:
            logger.debug("Background image load skipped: %s", e)

        # 2. Gradient overlay
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        o_draw = ImageDraw.Draw(overlay)
        for y in range(height):
            alpha = int(200 * (y / height)) 
            o_draw.line([(0, y), (width, y)], fill=(palette["bg"][0], palette["bg"][1], palette["bg"][2], alpha))
        img.paste(overlay, (0, 0), overlay)

        # 3. Text rendering
        try:
            font_main = ImageFont.truetype(str(FONT_FILE), 120)
            font_sub  = ImageFont.truetype(str(FONT_FILE), 60)
        except Exception as e:
            font_main = font_sub = ImageFont.load_default()

        # Progress bar at top
        bar_w = int((slide_num / total_slides) * (width - 100))
        draw.rectangle([50, 50, 50 + bar_w, 70], fill=palette["bar"])
        
        # Main text centered
        text_box = (100, height//3, width-100, 2*height//3)
        auto_scale_text(draw, text.upper(), str(FONT_FILE), 130, text_box, fill=palette["text"])

        # Branding
        draw.text((width//2, height - 150), f"@{YOUR_NAME.upper()}", fill=palette["accent"], font=font_sub, anchor="mm")

        path = output_dir / f"slide_{slide_num:02d}.png"
        img.convert("RGB").save(path)
        return str(path)

    def compose_brainrot_video(self, slide_paths: List[Union[str, Path]], audio_paths: List[Union[str, Path]], output_path: Union[str, Path], options: VideoOptions) -> str:
        if len(slide_paths) != len(audio_paths):
            raise ValueError(f"Slide/audio count mismatch")
            
        clips = []
        audio_clips_to_close = []
        final = None
        bg_clip = None
        bg_music = None

        try:
            for img_p, aud_p in zip(slide_paths, audio_paths):
                audio = AudioFileClip(str(aud_p))
                audio_clips_to_close.append(audio)
                img_clip = ImageClip(str(img_p)).set_duration(audio.duration).set_audio(audio)
                img_clip = img_clip.fadein(0.3).fadeout(0.3)
                clips.append(img_clip)

            final = concatenate_videoclips(clips, method="compose")
            total_duration = final.duration

            # Layered Background
            bg_source = options.custom_bg if (options.custom_bg and Path(options.custom_bg).exists()) else get_local_viral_gameplay()
            
            if bg_source and Path(bg_source).exists():
                bg_clip = VideoFileClip(str(bg_source)).subclip(0, total_duration).resize(height=SHORT_VIDEO_SIZE[1])
                if bg_clip.w > SHORT_VIDEO_SIZE[0]:
                    bg_clip = bg_clip.crop(x_center=bg_clip.w/2, width=SHORT_VIDEO_SIZE[0])
                final = CompositeVideoClip([bg_clip.volumex(0), final.set_position("center").set_opacity(0.85)])
            
            # Background Music
            music_path = Path(options.custom_music) if options.custom_music and Path(options.custom_music).exists() else BACKGROUND_MUSIC_PATH
            if music_path and music_path.exists():
                bg_music = AudioFileClip(str(music_path)).volumex(0.15).set_duration(total_duration)
                if final.audio is not None:
                    composite_audio = CompositeAudioClip([final.audio.volumex(1.2), bg_music])
                    final = final.set_audio(composite_audio)
                else:
                    final = final.set_audio(bg_music)

            temp_audio = str(output_path).replace('.mp4', 'TEMP_MPY_wvf_snd.mp4')
            final.write_videofile(
                str(output_path),
                fps=options.fps,
                codec="libx264",
                audio_codec="aac",
                threads=options.threads,
                preset="ultrafast",
                logger='bar',
                temp_audiofile=temp_audio,
            )
        finally:
            safe_close(audio_clips_to_close, final, bg_clip, bg_music)
            try:
                Path(temp_audio).unlink(missing_ok=True)
            except Exception as e:
                pass
        return str(output_path)

    def compose_rotgen_video(self, audio_path: Union[str, Path], output_path: Union[str, Path], options: VideoOptions, custom_char_path: Optional[Path] = None) -> str:
        audio_clip = AudioFileClip(str(audio_path))
        total_dur = audio_clip.duration
        
        # 1. Prepare Character
        char_img = None
        if custom_char_path and Path(custom_char_path).exists():
            char_img = self._prepare_rotgen_char(Path(custom_char_path))
        else:
            # Fallback to first in dir
            for ext in ("*.png", "*.gif", "*.jpg", "*.jpeg"):
                files = list(CHARACTERS_PATH.glob(ext))
                if files:
                    char_img = self._prepare_rotgen_char(files[0])
                    break
        
        panel_bg = self._build_rotgen_panel_bg()
        char_clip = self._build_rotgen_char_clip(True, total_dur, panel_bg, char_img)
        
        # 2. Gameplay
        bg_source = options.custom_bg if (options.custom_bg and Path(options.custom_bg).exists()) else self._get_rotgen_gameplay(topic=options.lesson_title or "")
        gameplay_clip = self._build_rotgen_gameplay_clip(bg_source, total_dur)
        
        # 3. Composite
        game_pos  = gameplay_clip.set_position((0, PANEL_H))            # y=768
        char_pos  = char_clip.set_position((0, 0))                 # y=0
        
        composite = CompositeVideoClip([game_pos, char_pos], size=(VIDEO_W, VIDEO_H))

        if options.script:
            from src.utils.captions import add_subtitle_overlay
            composite = add_subtitle_overlay(composite, options.script, 'short')

        final_composite = None
        bg_music = None
        temp_audio = str(output_path).replace('.mp4', 'TEMP_MPY_wvf_snd.mp4')
        
        try:
            music_path = Path(options.custom_music) if options.custom_music and Path(options.custom_music).exists() else BACKGROUND_MUSIC_PATH
            if music_path and music_path.exists():
                bg_music = AudioFileClip(str(music_path)).volumex(0.22)
                if bg_music.duration < composite.duration:
                    from moviepy.audio.fx.audio_loop import audio_loop
                    bg_music = audio_loop(bg_music, duration=composite.duration)
                else:
                    bg_music = bg_music.subclip(0, composite.duration)
                final_audio = CompositeAudioClip([audio_clip.volumex(1.3), bg_music])
            else:
                final_audio = audio_clip.volumex(1.3)

            final_composite = composite.set_audio(final_audio)

            final_composite.write_videofile(
                str(output_path),
                fps=options.fps,
                codec="libx264",
                audio_codec="aac",
                audio_bitrate="192k",
                preset="ultrafast",
                threads=options.threads,
                logger="bar",
                temp_audiofile=temp_audio,
            )
        finally:
            safe_close(composite, final_composite, bg_music, game_pos, char_pos, audio_clip)
            try:
                Path(temp_audio).unlink(missing_ok=True)
            except Exception as e:
                pass
        return str(output_path)

    def extract_short(self, input_path: Union[str, Path], output_path: Union[str, Path], duration: int = 30) -> str:
        """Extract a vertical short from a longer video using MoviePy."""
        clip = None
        final = None
        try:
            clip = VideoFileClip(str(input_path))
            actual_duration = min(duration, max(1, int(clip.duration)))
            final = clip.subclip(0, actual_duration).resize(height=SHORT_VIDEO_SIZE[1])
            if final.w > SHORT_VIDEO_SIZE[0]:
                final = final.crop(x_center=final.w / 2, width=SHORT_VIDEO_SIZE[0])
            else:
                final = final.resize(width=SHORT_VIDEO_SIZE[0])
            
            final.write_videofile(
                str(output_path),
                fps=VIDEO_FPS,
                codec="libx264",
                audio_codec="aac",
                preset="ultrafast",
                threads=VIDEO_THREADS,
                logger="bar",
            )
            return str(output_path)
        finally:
            if final:
                final.close()
            if clip:
                clip.close()

    def _prepare_rotgen_char(self, path: Path) -> Image.Image:
        img = Image.open(path).convert("RGBA")
        img.thumbnail((CANVAS_W, CANVAS_H), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        ox = (CANVAS_W - img.width) // 2
        oy = (CANVAS_H - img.height) // 2
        canvas.paste(img, (ox, oy), img)
        return canvas

    def _build_rotgen_panel_bg(self) -> np.ndarray:
        arr = np.zeros((PANEL_H, PANEL_W, 3), dtype=np.uint8)
        top    = np.array([15, 15, 25],  dtype=np.float32)
        bottom = np.array([30, 30, 55],  dtype=np.float32)
        t = np.linspace(0, 1, PANEL_H)[:, np.newaxis, np.newaxis]
        arr = (top * (1 - t) + bottom * t).astype(np.uint8)
        arr[762:768, :] = np.array([0, 200, 255], dtype=np.uint8)
        panel_img = Image.fromarray(arr, "RGB")
        d = ImageDraw.Draw(panel_img)
        try:
            lbl_font = ImageFont.truetype(str(FONT_FILE), 28)
        except IOError:
            lbl_font = ImageFont.load_default()
        d.text((20, 18), f"ByteBot  ·  AI for Developers by {YOUR_NAME}", fill=(0, 200, 255), font=lbl_font)
        return np.array(panel_img)

    def _draw_rotgen_char(self, canvas: Image.Image, speaking: bool, frame_index: int, num_frames: int = ANIMATION_FRAMES, custom_img: Image.Image | None = None) -> None:
        yo = int(math.sin(frame_index * 2 * math.pi / num_frames) * 8)
        blink = frame_index in (20, 21)
        if custom_img is not None:
            canvas.paste(custom_img, (0, yo), custom_img)
            return
        d = ImageDraw.Draw(canvas)
        def y(v): return v + yo
        d.ellipse([(70, y(30)), (330, y(160))],  fill=DARK)
        d.rectangle([(70, y(95)), (330, y(140))], fill=DARK)
        d.ellipse([(75, y(40)), (325, y(280))],  fill=SKIN, outline=(200, 160, 110), width=3)
        d.ellipse([(60, y(130)), (95,  y(200))],  fill=SKIN, outline=(200, 160, 110), width=2)
        d.ellipse([(305, y(130)), (340, y(200))], fill=SKIN, outline=(200, 160, 110), width=2)
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
                d.ellipse([(gx-3, y(gy)-3), (gx+3, y(gy)+3)], fill="white")
        d.arc([(130, y(95)), (180, y(118))],  start=200, end=340, fill=(80, 50, 20), width=4)
        d.arc([(220, y(95)), (270, y(118))],  start=200, end=340, fill=(80, 50, 20), width=4)
        d.arc([(185, y(178)), (215, y(200))], start=0, end=180, fill=(180, 130, 90), width=3)
        if speaking:
            pulse_h = 12 + int(8 * abs(math.sin(frame_index * math.pi / 6)))
            mx1, mx2 = 165, 235
            mcy = y(215)
            d.ellipse([(mx1, mcy - pulse_h), (mx2, mcy + pulse_h)], fill=(60, 20, 10), outline=(160, 90, 60), width=3)
            d.line([(mx1 + 8, mcy - 2), (mx2 - 8, mcy - 2)], fill=(235, 235, 235), width=3)
        else:
            d.arc([(155, y(195)), (245, y(240))], start=0, end=180, fill=(160, 90, 60), width=4)
        d.rectangle([(170, y(275)), (230, y(330))], fill=SKIN, outline=(200, 160, 110), width=2)
        body_pts = [(100, y(325)), (300, y(325)), (360, y(500)), (40, y(500))]
        d.polygon(body_pts, fill=BLUE, outline=(20, 80, 160))
        d.polygon([(170, y(325)), (200, y(380)), (130, y(340))], fill=(240, 240, 255))
        d.polygon([(230, y(325)), (200, y(380)), (270, y(340))], fill=(240, 240, 255))
        d.rectangle([(155, y(395)), (245, y(430))], fill="white", outline=(180, 180, 200))
        try: badge_font = ImageFont.truetype(str(FONT_FILE), 22)
        except Exception as e: badge_font = ImageFont.load_default()
        d.text((200, y(412)), "AI", fill=BLUE, font=badge_font, anchor="mm")

    def _build_rotgen_char_clip(self, speaking: bool, duration: float, panel_bg: np.ndarray, custom_img: Image.Image | None = None) -> ImageSequenceClip:
        frames = []
        for i in range(ANIMATION_FRAMES):
            panel = Image.fromarray(panel_bg.copy(), "RGB")
            canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
            self._draw_rotgen_char(canvas, speaking, i, ANIMATION_FRAMES, custom_img)
            panel.paste(canvas, (CHAR_PASTE_X, CHAR_PASTE_Y), canvas)
            frames.append(np.array(panel))
        clip = ImageSequenceClip(frames, fps=FPS)
        clip = clip.fx(vfx.loop, duration=duration)
        del frames
        gc.collect()
        return clip

    def _get_rotgen_gameplay(self, topic: str = "") -> str | None:
        p = get_local_viral_gameplay()
        if p: return p
        p = get_local_gameplay("short")
        if p: return p
        # AI-driven selection when a selector is injected
        if self.broll_selector and topic:
            p = self.broll_selector.select(topic, "short")
            if p: return p
        # Fallback: static query list
        for query in ROTGEN_PEXELS_QUERIES:
            p = get_relevant_pexels_video(query, "short")
            if p: return p
        return None

    def _build_rotgen_gameplay_clip(self, bg_path: str | None, duration: float):
        if bg_path:
            try:
                raw = VideoFileClip(bg_path)
                src_w, src_h = raw.size
                if src_w > src_h:
                    crop_x = (src_w - src_h * VIDEO_W // GAMEPLAY_H) // 2
                    cropped = raw.crop(x1=max(0, crop_x), y1=0, x2=min(src_w, crop_x + src_h * VIDEO_W // GAMEPLAY_H), y2=src_h)
                    try: raw.reader.close()
                    except Exception: pass
                    raw = cropped
                clip = raw.resize((VIDEO_W, GAMEPLAY_H))
                if clip.duration < duration: clip = clip.fx(vfx.loop, duration=duration)
                else: clip = clip.subclip(0, duration)
                clip = clip.fx(vfx.colorx, 0.55)
                return clip
            except Exception as e:
                logger.warning("Failed to load gameplay clip from %s: %s", bg_path, e)
        return ColorClip(size=(VIDEO_W, GAMEPLAY_H), color=(10, 10, 30)).set_duration(duration)

    def compose_video(self, slide_paths: List[Union[str, Path]], audio_paths: List[Union[str, Path]], output_path: Union[str, Path], 
                      options: VideoOptions) -> str:
        """OPTIMIZED dynamic video composition logic."""
        video_type = options.video_type
        lesson_title = options.lesson_title
        is_tutorial = options.is_tutorial
        force_viral_bg = options.force_viral_bg
        script = options.script
        bg_query = options.bg_query

        label = 'Tutorial' if is_tutorial else ('Viral' if force_viral_bg else 'Dynamic')
        print(f"🎥 Creating {label} {video_type} video for: {lesson_title}")

        target_size = LONG_VIDEO_SIZE if video_type == 'long' else SHORT_VIDEO_SIZE
        low_memory_mode = LOW_MEMORY_MODE or len(slide_paths) > 3
        # If custom_bg is provided, we override static_mode to ensure it's used
        static_mode = low_memory_mode and not force_viral_bg and not options.custom_bg
        slide_fade = 0.2 if low_memory_mode else 0.5

        bg_music = None
        bg_clip = None
        final_video = None
        audio_clips_to_close = []
        image_clips = []
        temp_audio = str(output_path).replace('.mp4', 'TEMP_MPY_wvf_snd.mp4')

        try:
            if not slide_paths or not audio_paths or len(slide_paths) != len(audio_paths):
                raise ValueError("Slide/audio mismatch")

            query = bg_query if bg_query else lesson_title
            if options.custom_bg and Path(options.custom_bg).exists():
                bg_path = options.custom_bg
            elif force_viral_bg:
                bg_path = get_local_viral_gameplay() or get_relevant_pexels_video(query, video_type)
            elif self.broll_selector:
                bg_path = self.broll_selector.select(query, video_type)
            else:
                bg_path = get_relevant_pexels_video(query, video_type)

            if not bg_path:
                bg_path = get_local_gameplay(video_type)

            _dur_clips = [AudioFileClip(str(a)) for a in audio_paths]
            total_duration = sum(c.duration for c in _dur_clips) + 0.5 * len(audio_paths)
            safe_close(_dur_clips)

            if bg_path and not static_mode:
                if str(bg_path).lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    bg_clip = ImageClip(str(bg_path)).set_duration(total_duration)
                else:
                    bg_clip = VideoFileClip(str(bg_path))
                
                if bg_clip.duration < total_duration:
                    bg_clip = bg_clip.fx(vfx.loop, duration=total_duration)
                else:
                    bg_clip = bg_clip.subclip(0, total_duration)
                bg_clip = bg_clip.fx(vfx.colorx, 0.78)
                bg_clip = bg_clip.resize(target_size)

            image_clips = []
            bg_cursor = 0.0
            for i, (img_path, audio_path) in enumerate(zip(slide_paths, audio_paths)):
                audio_clip = AudioFileClip(str(audio_path))
                audio_clips_to_close.append(audio_clip)
                duration = audio_clip.duration + 0.5
                img_clip = (
                    ImageClip(str(img_path))
                    .set_duration(duration)
                    .resize(height=target_size[1])
                    .fadein(slide_fade)
                    .fadeout(slide_fade)
                )

                if bg_clip:
                    segment_bg = bg_clip.subclip(bg_cursor, min(bg_cursor + duration, bg_clip.duration))
                    bg_cursor = min(bg_cursor + duration, bg_clip.duration)
                    final_clip = CompositeVideoClip([
                        segment_bg,
                        img_clip.set_opacity(0.93).set_position('center')
                    ], size=target_size)
                else:
                    final_clip = CompositeVideoClip([img_clip.set_position('center')], size=target_size)

                final_clip = final_clip.set_audio(audio_clip)
                image_clips.append(final_clip)

            final_video = concatenate_videoclips(image_clips, method="chain")

            if script:
                try:
                    from src.utils.captions import add_subtitle_overlay
                    final_video = add_subtitle_overlay(final_video, script, video_type)
                except Exception as e:
                    print(f"⚠️ Subtitle overlay failed ({e})")

            music_path = Path(options.custom_music) if options.custom_music and Path(options.custom_music).exists() else BACKGROUND_MUSIC_PATH
            if music_path and music_path.exists():
                bg_music = AudioFileClip(str(music_path)).volumex(0.15)
                if bg_music.duration < final_video.duration:
                    from moviepy.audio.fx.audio_loop import audio_loop
                    bg_music = audio_loop(bg_music, duration=final_video.duration)
                else:
                    bg_music = bg_music.subclip(0, final_video.duration)
                if final_video.audio:
                    final_video = final_video.set_audio(CompositeAudioClip([final_video.audio.volumex(1.2), bg_music]))
                else:
                    final_video = final_video.set_audio(bg_music)

            final_video.write_videofile(
                str(output_path),
                fps=options.fps,
                codec="libx264",
                audio_codec="aac",
                audio_bitrate="192k",
                preset="ultrafast",
                threads=options.threads,
                logger='bar',
                temp_audiofile=temp_audio,
                ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
            )
        finally:
            safe_close(audio_clips_to_close, image_clips, final_video, bg_clip, bg_music)
            try:
                Path(temp_audio).unlink(missing_ok=True)
            except Exception:
                pass
        return str(output_path)
