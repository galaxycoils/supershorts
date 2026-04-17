# main.py - SuperShorts v2.0
import os
import json
import datetime
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tqdm import tqdm
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
)
from src.brainrot import run_brainrot_pipeline as start_brainrot_generation
from src.rotgen import run_rotgen_pipeline as start_rotgen_mode
from src.learning import start_learning_mode, log_upload
from src.ideagenerator import start_idea_generator
from src.browser_uploader import upload_to_youtube_browser as upload_to_youtube
from src.artefacts import record_and_cleanup
from src.hardware import max_parallel_slides
import menu

CONTENT_PLAN_FILE = Path("content_plan.json")
OUTPUT_DIR = Path("output")


def _parallel_map(fn, items, desc):
    """Run fn over items in a thread pool, preserving input order."""
    results = [None] * len(items)
    with ThreadPoolExecutor(max_workers=max_parallel_slides()) as pool:
        futures = {pool.submit(fn, i, item): i for i, item in enumerate(items)}
        for fut in tqdm(futures, desc=desc, unit="slide",
                        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"):
            idx = futures[fut]
            results[idx] = fut.result()
    return results

def get_content_plan():
    if not CONTENT_PLAN_FILE.exists():
        print("📄 content_plan.json not found. Generating new plan...")
        new_plan = generate_curriculum()
        with open(CONTENT_PLAN_FILE, 'w') as f:
            json.dump(new_plan, f, indent=2)
        print(f"✅ New curriculum saved to {CONTENT_PLAN_FILE}")
        return new_plan
    else:
        try:
            with open(CONTENT_PLAN_FILE, 'r') as f:
                plan = json.load(f)
            if not plan.get("lessons") or not isinstance(plan["lessons"], list):
                raise ValueError("⚠️ Invalid or empty lesson plan detected.")
            return plan
        except Exception as e:
            print(f"❌ ERROR loading existing plan: {e}. Regenerating...")
            new_plan = generate_curriculum()
            with open(CONTENT_PLAN_FILE, 'w') as f:
                json.dump(new_plan, f, indent=2)
            return new_plan

def update_content_plan(plan):
    with open(CONTENT_PLAN_FILE, 'w') as f:
        json.dump(plan, f, indent=2)

def produce_lesson_videos(lesson):
    print(f"\n▶️ Starting production for Lesson: '{lesson['title']}'")
    unique_id = f"{datetime.datetime.now().strftime('%Y%m%d')}_{lesson['chapter']}_{lesson['part']}"
    lesson_content = generate_lesson_content(lesson['title'])
    print("\n--- Producing Long-Form Video ---")
    intro_slide = {"title": lesson['title'], "content": f"Chapter {lesson['chapter']} | Part {lesson['part']}"}
    outro_slide = {"title": "Thanks for Watching!", "content": "Like, Share & Subscribe for more daily AI content!\n#AIforDevelopers"}
    all_slides = [intro_slide] + lesson_content['long_form_slides'] + [outro_slide]
    slide_scripts = [
        f"Hello and welcome to AI for Developers. I'm {YOUR_NAME} talking bot. Today’s lesson is titled {lesson['title']}.",
        *[s['content'] for s in lesson_content['long_form_slides']],
        "Thanks for watching! If you found this helpful, make sure to subscribe to our channel and hit the like button."
    ]
    def _tts_one(i, script):
        return text_to_speech(script, OUTPUT_DIR / f"audio_slide_{i+1}_{unique_id}.mp3")

    slide_audio_paths = _parallel_map(_tts_one, slide_scripts, "  TTS (long)")

    slide_dir = OUTPUT_DIR / f"slides_long_{unique_id}"
    total = len(all_slides)

    def _visual_one(i, slide):
        return generate_visuals(
            output_dir=slide_dir,
            video_type='long',
            slide_content=slide,
            slide_number=i + 1,
            total_slides=total,
        )

    slide_paths = _parallel_map(_visual_one, all_slides, "  Slides (long)")
    long_video_path = OUTPUT_DIR / f"long_video_{unique_id}.mp4"
    print(f"🎥 Creating long-form video at: {long_video_path}")
    compose_video(slide_paths, slide_audio_paths, long_video_path, 'long', lesson['title'])
    long_thumb_path = generate_visuals(
        output_dir=OUTPUT_DIR,
        video_type='long',
        thumbnail_title=lesson['title']
    )
    print("\n--- Producing Short Video ---")
    short_script = (f"{lesson_content['short_form_highlight']}\n\n"
                    f"Link to the full lesson is in the description below.")
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
    print(f"🎥 Creating short video at: {short_video_path}")
    compose_video([short_slide_path], [short_audio_path], short_video_path, 'short', lesson['title'])
    short_thumb_path = generate_visuals(
        output_dir=OUTPUT_DIR,
        video_type='short',
        thumbnail_title=f"Quick Tip: {lesson['title']}"
    )
    print("\n📤 Uploading to YouTube...")
    hashtags = lesson_content.get("hashtags", "#AI #Developer #LearnAI")
    long_desc = f"Part of the 'AI for Developers' series by {YOUR_NAME}.\n\nToday's Lesson: {lesson['title']}\n\n{hashtags}"
    long_tags = "AI, Artificial Intelligence, Developer, Programming, Tutorial, " + lesson['title'].replace(" ", ", ")
    long_video_id = upload_to_youtube(
        long_video_path,
        lesson['title'],
        long_desc,
        long_tags,
        long_thumb_path
    )
    if long_video_id:
        log_upload(lesson['title'], long_video_id, "educational")
        record_and_cleanup(
            mode="educational",
            title=lesson['title'],
            video_id=long_video_id,
            video_path=long_video_path,
            audio_paths=slide_audio_paths,
            slide_dir=slide_dir,
            thumbnail_path=long_thumb_path,
        )
        print("⏳ Waiting 30 seconds before uploading the short...")
        time.sleep(30)
        highlight = (lesson_content.get('short_form_highlight') or '').strip()
        if not highlight:
            highlight = f"AI Quick Tip: {lesson['title']}"
        short_title = f"{highlight[:90].rstrip()} #Shorts"
        short_desc = (f"{lesson_content['short_form_highlight']}\n\n"
                      f"Watch the full lesson with {YOUR_NAME} here: https://www.youtube.com/watch?v={long_video_id}\n\n"
                      f"{hashtags}")
        short_video_id = upload_to_youtube(
            short_video_path,
            short_title.strip(),
            short_desc,
            "AI,Shorts,TechTip",
            short_thumb_path
        )
        if short_video_id:
            log_upload(short_title, short_video_id, "short")
            record_and_cleanup(
                mode="short",
                title=short_title,
                video_id=short_video_id,
                video_path=short_video_path,
                audio_paths=[short_audio_path],
                slide_dir=short_slide_dir,
                thumbnail_path=short_thumb_path,
            )
        return long_video_id
    return None

def main_flow():
    print("🚀 Starting Money Printer V2 (100% Local Ollama)")
    print(f"📁 Current working dir: {os.getcwd()}")
    print(f"📁 OUTPUT_DIR: {OUTPUT_DIR.resolve()}")
    try:
        OUTPUT_DIR.mkdir(exist_ok=True)
        plan = get_content_plan()
        pending = [(i, lesson) for i, lesson in enumerate(plan['lessons']) if lesson['status'] == 'pending']
        if not pending:
            print("🎉 All lessons done! Generating fresh curriculum...")
            previous_titles = [l['title'] for l in plan['lessons']]
            new_plan = generate_curriculum(previous_titles=previous_titles)
            update_content_plan(new_plan)
            plan = new_plan
            pending = [(i, lesson) for i, lesson in enumerate(new_plan['lessons']) if lesson['status'] == 'pending']
        lessons_this_run = menu.ask_count("lessons", "Lessons this run", 2)
        import gc
        for _, lesson in pending[:lessons_this_run]:
            try:
                video_id = produce_lesson_videos(lesson)
                if video_id:
                    for original in plan['lessons']:
                        if original['title'].strip().lower() == lesson['title'].strip().lower():
                            original['status'] = 'complete'
                            original['youtube_id'] = video_id
                            print(f"✅ Lesson marked complete: {lesson['title']}")
                            break
                    update_content_plan(plan)
            except Exception as e:
                print(f"❌ Failed to produce lesson: {e}")
                traceback.print_exc()
            finally:
                gc.collect()
        try:
            from src.learning import suggest_improvements
            suggest_improvements()
        except Exception as e:
            print(f"⚠️ Learning refresh skipped: {e}")
    except Exception as e:
        print(f"❌ Critical error: {e}")
        traceback.print_exc()

def main():
    while True:
        choice = menu.show_menu()
        try:
            if choice == "1":
                main_flow()
            elif choice == "2":
                start_brainrot_generation()
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
                continue  # skip the "Press Enter" since view_content_plan has its own
            elif choice == "8":
                start_rotgen_mode()
            elif choice == "9":
                generate_youtube_content_package()
            elif choice == "10":
                print("\n  Goodbye!")
                break
            else:
                print("  Invalid option.")
        except Exception as e:
            print(f"\n  Error: {e}")
            traceback.print_exc()
        input("\nPress Enter to return to menu...")

if __name__ == "__main__":
    main()
