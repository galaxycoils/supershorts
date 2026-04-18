# src/tcm_mode.py - Traditional Chinese Medicine Educational Mode
import gc
import json
import datetime
import time
import random
import concurrent.futures
from pathlib import Path

import ollama
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich import box

from src.core.config import PROJECT_ROOT, OLLAMA_MODEL, OLLAMA_TIMEOUT, YOUR_NAME
from src.infrastructure.llm import ollama_generate, safe_json_parse
from src.infrastructure.tts import text_to_speech
from src.engine.video_engine import generate_visuals, compose_video
from src.utils.text import _clamp_words


console = Console()

TCM_PLAN_FILE = PROJECT_ROOT / "tcm_plan.json"
OUTPUT_DIR    = PROJECT_ROOT / "output"

# ── Pexels keywords for TCM background videos ────────────────────
TCM_BG_KEYWORDS = [
    "traditional medicine herbs",
    "acupuncture therapy",
    "Chinese herbal medicine",
    "meditation wellness",
    "herb preparation",
    "holistic healing lotus",
    "tea ceremony zen",
]

TOPIC_CHOICES = {
    "1": "Traditional Chinese Medicine (TCM)",
    "2": "Eastern Medicine",
    "3": "Ayurvedic Medicine",
    "4": "Holistic Wellness",
}


def _generate_tcm_curriculum(focus: str, extra: str, previous_titles=None) -> dict:
    """Generate TCM-focused curriculum via Ollama."""
    prev = f"\nDo not repeat these titles: {previous_titles}" if previous_titles else ""
    prompt = (
        f"Create a 10-lesson educational video curriculum about: {focus}.\n"
        f"{'Additional focus: ' + extra if extra else ''}{prev}\n\n"
        "Cover: fundamentals, herbs/treatments, diagnosis methods, lifestyle, "
        "modern applications, historical context, case studies, integration with Western medicine.\n\n"
        "Return ONLY valid JSON:\n"
        "{\n"
        '  "curriculum_title": "string",\n'
        '  "lessons": [\n'
        '    {"chapter": 1, "part": 1, "title": "string", "status": "pending", "youtube_id": null}\n'
        "  ]\n"
        "}\n"
        "10 lessons. No markdown, no commentary."
    )
    try:
        return ollama_generate(prompt, json_mode=True)
    except Exception as e:
        console.print(f"[yellow]⚠  Curriculum fallback ({e})[/yellow]")
        topics = [
            "Introduction", "Yin & Yang Theory", "Five Elements",
            "Qi & Energy Flow", "Herbal Medicine Basics", "Acupuncture Fundamentals",
            "Dietary Therapy", "Cupping & Moxibustion", "Mind-Body Integration",
            "Modern Integration",
        ]
        return {
            "curriculum_title": f"{focus} Essentials",
            "lessons": [
                {"chapter": i + 1, "part": 1, "title": f"{t} in {focus}",
                 "status": "pending", "youtube_id": None}
                for i, t in enumerate(topics)
            ],
        }


def _show_plan_status(plan: dict):
    """Print current TCM plan progress table."""
    lessons = plan.get("lessons", [])
    done    = sum(1 for l in lessons if l.get("status") == "complete")
    pending = len(lessons) - done

    tbl = Table(box=box.SIMPLE_HEAD, border_style="dim", padding=(0, 1))
    tbl.add_column("Ch",     style="dim",    no_wrap=True, min_width=3)
    tbl.add_column("",       no_wrap=True,   min_width=1)
    tbl.add_column("Title",  style="white",  no_wrap=True)
    tbl.add_column("YT ID",  style="dim cyan", no_wrap=True)
    for l in lessons:
        sym = "[green]✔[/green]" if l.get("status") == "complete" else "[yellow]·[/yellow]"
        tbl.add_row(
            str(l.get("chapter", "?")),
            sym,
            l.get("title", "")[:50],
            (l.get("youtube_id") or "")[:11],
        )
    console.print(
        f"[bold]{plan.get('curriculum_title', 'TCM Curriculum')}[/bold]  "
        f"[green]{done}[/green][dim]/{len(lessons)}[/dim] complete  "
        f"[yellow]{pending}[/yellow] pending"
    )
    console.print(tbl)


def run_tcm_mode():
    """Option 11 — TCM Educational Mode."""
    console.print()
    console.print(Panel(
        "[bold cyan]TCM Educational Mode[/bold cyan]\n"
        "Generate Traditional Chinese Medicine & Eastern wellness content",
        border_style="cyan",
        padding=(0, 2),
    ))
    console.print()

    # ── Check for existing plan ───────────────────────────────────
    plan = None
    if TCM_PLAN_FILE.exists():
        try:
            existing = json.loads(TCM_PLAN_FILE.read_text())
            pending_count = sum(
                1 for l in existing.get("lessons", [])
                if l.get("status") == "pending"
            )
            if pending_count > 0:
                _show_plan_status(existing)
                console.print()
                use = Prompt.ask(
                    f"  Found existing plan with [yellow]{pending_count}[/yellow] pending lessons. Use it?",
                    choices=["y", "n"], default="y",
                )
                if use == "y":
                    plan = existing
        except Exception:
            pass

    if plan is None:
        # ── Topic selection ───────────────────────────────────────
        console.print("[bold]Topic focus:[/bold]")
        for k, v in TOPIC_CHOICES.items():
            console.print(f"  [yellow][{k}][/yellow] {v}")
        console.print("  [yellow][5][/yellow] Custom")
        console.print()
        t_choice = Prompt.ask("  Select", default="1")
        if t_choice in TOPIC_CHOICES:
            focus = TOPIC_CHOICES[t_choice]
        else:
            focus = Prompt.ask("  Custom topic")

        extra = Prompt.ask(
            "  [dim]Sub-topics / extra details (optional, e.g. 'focus on anxiety, sleep')[/dim]",
            default="",
        )

        prev_titles = None
        if TCM_PLAN_FILE.exists():
            try:
                old = json.loads(TCM_PLAN_FILE.read_text())
                prev_titles = [l["title"] for l in old.get("lessons", [])]
            except Exception:
                pass

        with console.status(f"[cyan]Generating {focus} curriculum via Ollama…[/cyan]"):
            plan = _generate_tcm_curriculum(focus, extra, prev_titles)

        TCM_PLAN_FILE.write_text(json.dumps(plan, indent=2))
        console.print(f"[green]✅ Curriculum saved → {TCM_PLAN_FILE}[/green]")
        console.print()
        _show_plan_status(plan)
        console.print()

    # ── Video count ───────────────────────────────────────────────
    pending_lessons = [l for l in plan.get("lessons", []) if l.get("status") == "pending"]
    if not pending_lessons:
        console.print("[green]🎉 All TCM lessons complete! Resetting plan…[/green]")
        for l in plan["lessons"]:
            l["status"] = "pending"
            l["youtube_id"] = None
        TCM_PLAN_FILE.write_text(json.dumps(plan, indent=2))
        pending_lessons = plan["lessons"]

    raw_count = Prompt.ask(
        f"  How many videos to generate? [1–{min(10, len(pending_lessons))}]",
        default="3",
    )
    try:
        count = max(1, min(10, int(raw_count)))
    except ValueError:
        count = 3
    if count > 5:
        console.print("[yellow]  ⚠  >5 videos may stress 8 GB RAM — consider 3–5.[/yellow]")
    console.print()

    # ── Generation loop ───────────────────────────────────────────
    from src.generator import generate_lesson_content
    from src.infrastructure.tts import text_to_speech
    from src.engine.video_engine import generate_visuals, compose_video
    from src.utils.text import _clamp_words
    from src.infrastructure.browser_uploader import upload_to_youtube_browser as upload_to_youtube
    from src.core.learning import log_upload

    OUTPUT_DIR.mkdir(exist_ok=True)
    produced = 0

    for lesson in pending_lessons[:count]:
        try:
            console.print(
                f"\n[bold cyan]▶  TCM Lesson:[/bold cyan] [white]{lesson['title']}[/white]"
            )
            uid = f"{datetime.datetime.now().strftime('%Y%m%d')}_tcm_ch{lesson['chapter']}"

            # ── Content generation ────────────────────────────────
            series_name = plan.get('curriculum_title', 'Traditional Chinese Medicine')
            style_desc = (
                "Assume the viewer is interested in Eastern wellness and holistic health. "
                "Explain Traditional Chinese Medicine concepts (like Qi, Yin/Yang, herbs) "
                "using simple analogies and practical wellness tips. Avoid overly complex terminology "
                "without explaining it first."
            )
            with console.status("[cyan]Generating lesson content via Ollama…[/cyan]"):
                content = generate_lesson_content(
                    lesson["title"], 
                    series_name=series_name, 
                    style_description=style_desc
                )

            # ── Short video ───────────────────────────────────────
            raw_short = content.get("short_form_highlight") or lesson["title"]
            short_script = _clamp_words(raw_short, min_w=99, max_w=127)

            short_audio = text_to_speech(
                short_script, OUTPUT_DIR / f"tcm_audio_{uid}.mp3"
            )
            slide_path = generate_visuals(
                output_dir=OUTPUT_DIR / f"tcm_slides_{uid}",
                video_type="short",
                slide_content={
                    "title": lesson["title"],
                    "content": content.get("short_form_highlight", ""),
                },
                slide_number=1,
                total_slides=1,
            )
            short_path = OUTPUT_DIR / f"tcm_short_{uid}.mp4"
            console.print(f"[cyan]🎥 Composing short…[/cyan]")
            
            # Use random TCM background query
            bg_query = random.choice(TCM_BG_KEYWORDS)
            compose_video(
                [slide_path], [short_audio], short_path, "short",
                lesson["title"], script=short_script, bg_query=bg_query
            )

            # Cleanup audio temp
            try:
                Path(short_audio).unlink(missing_ok=True)
            except Exception:
                pass

            # ── Upload ────────────────────────────────────────────
            console.print("[cyan]📤 Uploading to YouTube…[/cyan]")
            hashtags = "#TCM #TraditionalChineseMedicine #Wellness #Health #EasternMedicine #Shorts"
            video_id = upload_to_youtube(
                short_path,
                f"{lesson['title']} #Shorts",
                f"{content.get('short_form_highlight', '')}\n\n{hashtags}",
                "TCM,Traditional Chinese Medicine,Wellness,Health,Eastern Medicine",
                None,
            )

            if video_id:
                log_upload(lesson["title"], video_id, "tcm")
                lesson["status"] = "complete"
                lesson["youtube_id"] = video_id
                TCM_PLAN_FILE.write_text(json.dumps(plan, indent=2))
                console.print(
                    f"[green]✅ Complete:[/green] [white]{lesson['title']}[/white]"
                )
                produced += 1

                if produced < count:
                    console.print("[yellow]⏳ Waiting 30 s before next upload…[/yellow]")
                    time.sleep(30)
            else:
                console.print("[yellow]⚠  Upload returned no video ID (check browser profile).[/yellow]")

        except Exception as e:
            console.print(f"[red]❌ Failed: {e}[/red]")
            import traceback
            traceback.print_exc()

        gc.collect()

    console.print(
        f"\n[bold green]TCM mode done — {produced}/{count} video(s) produced.[/bold green]"
    )
    _show_plan_status(plan)
