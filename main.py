# main.py - SuperShorts v2.6
import gc
import os
import json
import datetime
import time
import traceback
from pathlib import Path
from tqdm import tqdm
from rich.prompt import Prompt

from src.generator import (
    generate_curriculum,
    generate_lesson_content,
    text_to_speech,
    generate_visuals,
    compose_video,
    YOUR_NAME,
    start_viral_gameplay_mode,
    start_tutorial_generation,
    generate_youtube_content_package,
    run_brainrot_pipeline,
    run_rotgen_pipeline,
    run_tcm_mode,
    run_video_clipper,
    start_idea_generator,
    log_upload,
    PROJECT_ROOT,
    start_learning_mode
)
from src.core.learning import suggest_improvements # learning.py renamed

# Alias for legacy main.py names
start_brainrot_generation = run_brainrot_pipeline
start_rotgen_mode = run_rotgen_pipeline
upload_to_youtube = lambda *args, **kwargs: __import__('src.infrastructure.browser_uploader', fromlist=['upload_to_youtube_browser']).upload_to_youtube_browser(*args, **kwargs)
import menu
from menu import console

CONTENT_PLAN_FILE = Path("content_plan.json")
OUTPUT_DIR = Path("output")


def cleanup_after_upload(video_path: Path, title: str, video_id: str, mode: str):
    """Save tiny reference JSON then delete the mp4 to free disk space."""
    try:
        ref_dir = OUTPUT_DIR / "uploaded"
        ref_dir.mkdir(exist_ok=True)
        safe = "".join(c for c in title[:40] if c.isalnum() or c in " -_").strip()
        ref_file = ref_dir / f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe[:30]}.json"
        ref_file.write_text(json.dumps({
            "title": title,
            "video_id": video_id,
            "mode": mode,
            "uploaded_at": str(datetime.datetime.now()),
            "original_filename": Path(video_path).name,
        }, indent=2))
        if Path(video_path).exists():
            Path(video_path).unlink()
            console.print(f"[dim]🗑  Cleaned up {Path(video_path).name} → ref saved[/dim]")
    except Exception as e:
        console.print(f"[yellow]⚠  Cleanup warning: {e}[/yellow]")


def get_content_plan():
    if not CONTENT_PLAN_FILE.exists():
        console.print("[cyan]📄 content_plan.json not found. Generating new plan…[/cyan]")
        with console.status("[cyan]Generating curriculum via Ollama…[/cyan]"):
            new_plan = generate_curriculum()
        with open(CONTENT_PLAN_FILE, 'w') as f:
            json.dump(new_plan, f, indent=2)
        console.print(f"[green]✅ New curriculum saved to {CONTENT_PLAN_FILE}[/green]")
        return new_plan
    else:
        try:
            with open(CONTENT_PLAN_FILE, 'r') as f:
                plan = json.load(f)
            if not plan.get("lessons") or not isinstance(plan["lessons"], list):
                raise ValueError("Invalid or empty lesson plan detected.")
            return plan
        except Exception as e:
            console.print(f"[red]❌ ERROR loading existing plan: {e}. Regenerating…[/red]")
            with console.status("[cyan]Regenerating curriculum via Ollama…[/cyan]"):
                new_plan = generate_curriculum()
            with open(CONTENT_PLAN_FILE, 'w') as f:
                json.dump(new_plan, f, indent=2)
            return new_plan


def update_content_plan(plan):
    with open(CONTENT_PLAN_FILE, 'w') as f:
        json.dump(plan, f, indent=2)


def produce_lesson_videos(lesson):
    console.print(f"\n[bold cyan]▶  Starting production: [white]'{lesson['title']}'[/white][/bold cyan]")
    unique_id = f"{datetime.datetime.now().strftime('%Y%m%d')}_{lesson['chapter']}_{lesson['part']}"
    lesson_content = generate_lesson_content(lesson['title'])

    console.print("\n[bold]── Long-Form Video ──[/bold]")
    intro_slide = {"title": lesson['title'], "content": f"Chapter {lesson['chapter']} | Part {lesson['part']}"}
    outro_slide = {"title": "Thanks for Watching!", "content": "Like, Share & Subscribe for more daily AI content!\n#AIforDevelopers"}
    all_slides = [intro_slide] + lesson_content['long_form_slides'] + [outro_slide]
    slide_scripts = [
        f"Hello and welcome to AI for Developers. I'm {YOUR_NAME} talking bot. Today's lesson is titled {lesson['title']}.",
        *[s['content'] for s in lesson_content['long_form_slides']],
        "Thanks for watching! If you found this helpful, make sure to subscribe to our channel and hit the like button."
    ]
    slide_audio_paths = []
    for i, script in enumerate(tqdm(slide_scripts, desc="  TTS (long)", unit="slide",
                                    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")):
        audio_path = OUTPUT_DIR / f"audio_slide_{i+1}_{unique_id}.mp3"
        wav_path = text_to_speech(script, audio_path)
        slide_audio_paths.append(wav_path)

    slide_dir = OUTPUT_DIR / f"slides_long_{unique_id}"
    slide_paths = []
    for i, slide in enumerate(tqdm(all_slides, desc="  Slides (long)", unit="slide",
                                   bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")):
        path = generate_visuals(
            output_dir=slide_dir,
            video_type='long',
            slide_content=slide,
            slide_number=i + 1,
            total_slides=len(all_slides)
        )
        slide_paths.append(path)

    long_video_path = OUTPUT_DIR / f"long_video_{unique_id}.mp4"
    console.print(f"[cyan]🎥 Creating long-form video: [dim]{long_video_path}[/dim][/cyan]")
    long_full_script = '\n'.join(slide_scripts)
    compose_video(slide_paths, slide_audio_paths, long_video_path, 'long', lesson['title'],
                  script=long_full_script)

    for _ap in slide_audio_paths:
        try:
            Path(_ap).unlink(missing_ok=True)
        except Exception:
            pass

    long_thumb_path = generate_visuals(
        output_dir=OUTPUT_DIR,
        video_type='long',
        thumbnail_title=lesson['title']
    )

    console.print("\n[bold]── Short Video ──[/bold]")
    from src.generator import _clamp_words
    raw_short = (f"{lesson_content['short_form_highlight']}\n\n"
                 f"Link to the full lesson is in the description below.")
    short_script = _clamp_words(raw_short, min_w=99, max_w=127)
    short_audio_mp3_path = OUTPUT_DIR / f"short_audio_{unique_id}.mp3"
    short_audio_path = text_to_speech(short_script, short_audio_mp3_path)
    short_slide_dir = OUTPUT_DIR / f"slides_short_{unique_id}"
    short_slide_content = {
        "title": "Quick Tip!",
        "content": f"{lesson_content['short_form_highlight']}\n\n#AI for developers by {YOUR_NAME}"
    }
    short_slide_path = generate_visuals(
        output_dir=short_slide_dir,
        video_type='short',
        slide_content=short_slide_content,
        slide_number=1,
        total_slides=1
    )
    short_video_path = OUTPUT_DIR / f"short_video_{unique_id}.mp4"
    console.print(f"[cyan]🎥 Creating short video: [dim]{short_video_path}[/dim][/cyan]")
    compose_video([short_slide_path], [short_audio_path], short_video_path, 'short', lesson['title'],
                  script=short_script)

    for _ap in [short_audio_path, str(short_audio_mp3_path)]:
        try:
            Path(_ap).unlink(missing_ok=True)
        except Exception:
            pass

    short_thumb_path = generate_visuals(
        output_dir=OUTPUT_DIR,
        video_type='short',
        thumbnail_title=f"Quick Tip: {lesson['title']}"
    )

    console.print("\n[cyan]📤 Uploading to YouTube…[/cyan]")
    hashtags = lesson_content.get("hashtags", "#AI #Developer #LearnAI")
    long_desc = f"Part of the 'AI for Developers' series by {YOUR_NAME}.\n\nToday's Lesson: {lesson['title']}\n\n{hashtags}"
    long_tags = "AI, Artificial Intelligence, Developer, Programming, Tutorial, " + lesson['title'].replace(" ", ", ")
    long_video_id = upload_to_youtube(
        long_video_path, lesson['title'], long_desc, long_tags, long_thumb_path
    )
    if long_video_id:
        log_upload(lesson['title'], long_video_id, "educational")
        console.print("[yellow]⏳ Waiting 30 s before uploading the short…[/yellow]")
        time.sleep(30)
        highlight = (lesson_content.get('short_form_highlight') or '').strip()
        if not highlight:
            highlight = f"AI Quick Tip: {lesson['title']}"
        short_title = f"{highlight[:90].rstrip()} #Shorts"
        short_desc = (f"{lesson_content['short_form_highlight']}\n\n"
                      f"Watch the full lesson with {YOUR_NAME} here: https://www.youtube.com/watch?v={long_video_id}\n\n"
                      f"{hashtags}")
        short_video_id = upload_to_youtube(
            short_video_path, short_title.strip(), short_desc, "AI,Shorts,TechTip", short_thumb_path
        )
        if short_video_id:
            log_upload(short_title, short_video_id, "short")
            cleanup_after_upload(short_video_path, short_title, short_video_id, "short")
        cleanup_after_upload(long_video_path, lesson['title'], long_video_id, "educational")
        return long_video_id
    return None


def main_flow(lessons_per_run: int = 2):
    console.print("[bold cyan]🚀 Starting Money Printer V2 (100% Local Ollama)[/bold cyan]")
    console.print(f"[dim]📁 Working dir: {os.getcwd()}[/dim]")
    console.print(f"[dim]📁 Output dir:  {OUTPUT_DIR.resolve()}[/dim]")
    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
        plan = get_content_plan()
        pending = [(i, lesson) for i, lesson in enumerate(plan['lessons']) if lesson['status'] == 'pending']
        if not pending:
            console.print("[green]🎉 All lessons done! Generating fresh curriculum…[/green]")
            previous_titles = [l['title'] for l in plan['lessons']]
            with console.status("[cyan]Generating new curriculum via Ollama…[/cyan]"):
                new_plan = generate_curriculum(previous_titles=previous_titles)
            update_content_plan(new_plan)
            plan = new_plan
            pending = [(i, lesson) for i, lesson in enumerate(new_plan['lessons']) if lesson['status'] == 'pending']
        for _, lesson in pending[:lessons_per_run]:
            try:
                video_id = produce_lesson_videos(lesson)
                if video_id:
                    for original in plan['lessons']:
                        if original['title'].strip().lower() == lesson['title'].strip().lower():
                            original['status'] = 'complete'
                            original['youtube_id'] = video_id
                            console.print(f"[green]✅ Lesson marked complete: {lesson['title']}[/green]")
                            break
                    update_content_plan(plan)
            except Exception as e:
                console.print(f"[red]❌ Failed to produce lesson: {e}[/red]")
                traceback.print_exc()
            gc.collect()
    except Exception as e:
        console.print(f"[red]❌ Critical error: {e}[/red]")
        traceback.print_exc()


def main():
    while True:
        choice = menu.show_menu()
        try:
            if choice == "1":
                count = menu.ask_video_count("Educational", default=2)
                main_flow(lessons_per_run=count)
            elif choice == "2":
                count = menu.ask_video_count("Brain Rot", default=3)
                start_brainrot_generation(count)
            elif choice == "3":
                start_viral_gameplay_mode()
            elif choice == "4":
                start_tutorial_generation()
            elif choice == "5":
                start_learning_mode()
            elif choice == "6":
                start_idea_generator()
            elif choice == "7":
                menu.view_content_plan()
                continue  # view_content_plan has its own "Press Enter"
            elif choice == "8":
                count = menu.ask_video_count("RotGen", default=3)
                start_rotgen_mode(count)
            elif choice == "9":
                generate_youtube_content_package()
            elif choice == "10":
                run_video_clipper()
            elif choice == "11":
                run_tcm_mode()
            elif choice == "12":
                console.print("\n[bold cyan]  Goodbye![/bold cyan]")
                break
            else:
                console.print("[yellow]  Invalid option — enter 1–12.[/yellow]")
                continue
        except Exception as e:
            console.print(f"\n[red]  Error: {e}[/red]")
            traceback.print_exc()
        console.input("\n  [dim]Press Enter to return to menu…[/dim]")


if __name__ == "__main__":
    main()
