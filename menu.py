# menu.py - SuperShorts interactive terminal menu (rich edition)
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich import box
from rich.rule import Rule

CONTENT_PLAN_FILE  = Path("content_plan.json")
BRAINROT_PLAN_FILE = Path("brainrot_plan.json")

console = Console()

# ─── Menu options ─────────────────────────────────────────────────
MENU_OPTIONS = [
    ("1",  "📚", "Educational Videos",       "Long-form + linked Short (curriculum-based)"),
    ("2",  "🧠", "Brain Rot Viral Shorts",    "Sensationalized AI shorts, 30–45 s"),
    ("3",  "🎮", "Viral Gameplay Mode",       "Subway Surfers-style background + AI narration"),
    ("4",  "🎓", "Tutorial Videos",           "~10-min deep-dive + linked Short"),
    ("5",  "📈", "Learning Mode",             "Self-improvement analysis from past uploads"),
    ("6",  "💡", "YouTube Studio Ideas",      "Real YT suggestions, thumbnails & scripts"),
    ("7",  "📋", "View Content Plan",         "Browse lessons + brain rot topic tracker"),
    ("8",  "🎭", "RotGen Character Mode",      "ByteBot AI character + gameplay + auto-subtitles"),
    ("9",  "📦", "YouTube Content Package",   "Expert AI: topic → script → 5-min video → upload"),
    ("10", "✂️",  "Automatic Video Clipper",   "Long YouTube/podcast → viral vertical Shorts"),
    ("11", "🌿", "TCM Educational Mode",      "Traditional Chinese Medicine content series"),
    ("12", "🚪", "Exit",                      ""),
]


def _stats() -> tuple[int, int, int, int]:
    """Return (lessons_done, lessons_total, br_done, br_total)."""
    ld = lt = bd = bt = 0
    try:
        if CONTENT_PLAN_FILE.exists():
            plan = json.loads(CONTENT_PLAN_FILE.read_text())
            ls = plan.get("lessons", [])
            lt = len(ls)
            ld = sum(1 for l in ls if l.get("status") == "complete")
    except Exception:
        pass
    try:
        if BRAINROT_PLAN_FILE.exists():
            bp = json.loads(BRAINROT_PLAN_FILE.read_text())
            ts = bp.get("topics", [])
            bt = len(ts)
            bd = sum(1 for t in ts if t.get("status") == "complete")
    except Exception:
        pass
    return ld, lt, bd, bt


def show_menu() -> str:
    console.clear()

    # ── Header panel ──────────────────────────────────────────────
    header = Text(justify="center")
    header.append("SuperShorts", style="bold cyan")
    header.append("  v2.6  ", style="dim")
    header.append("│", style="dim")
    header.append("  Ollama + MoviePy  ", style="cyan")
    header.append("│", style="dim")
    header.append("  Local-AI Content Engine", style="dim")
    console.print(Panel(header, border_style="cyan", padding=(0, 2)))

    # ── Stats bar ────────────────────────────────────────────────
    ld, lt, bd, bt = _stats()
    parts = []
    if lt:
        parts.append(f"[green]{ld}[/green][dim]/{lt}[/dim] Lessons")
    if bt:
        parts.append(f"[green]{bd}[/green][dim]/{bt}[/dim] Brain Rot")
    if parts:
        console.print("  " + "  [dim]·[/dim]  ".join(parts))
        console.print()

    # ── Menu table ───────────────────────────────────────────────
    table = Table(
        box=box.SIMPLE,
        show_header=False,
        padding=(0, 1),
        border_style="dim",
    )
    table.add_column("num",   style="bold yellow",  no_wrap=True, min_width=4)
    table.add_column("icon",  no_wrap=True,          min_width=2)
    table.add_column("label", style="bold white",   no_wrap=True, min_width=26)
    table.add_column("desc",  style="dim",           no_wrap=True, overflow="ellipsis")

    for key, icon, label, desc in MENU_OPTIONS:
        table.add_row(f"[{key}]", icon, label, desc)

    console.print(table)
    console.print(Rule(style="dim"))
    console.print()

    return Prompt.ask("  [bold]Select option[/bold]").strip()


# ─── Content Plan view ────────────────────────────────────────────

def view_content_plan():
    console.clear()

    header = Text("  CONTENT PLAN  ", style="bold cyan", justify="center")
    console.print(Panel(header, border_style="cyan", padding=(0, 2)))
    console.print()

    # ── Educational lessons ──────────────────────────────────────
    if CONTENT_PLAN_FILE.exists():
        try:
            plan     = json.loads(CONTENT_PLAN_FILE.read_text())
            lessons  = plan.get("lessons", [])
            complete = sum(1 for l in lessons if l.get("status") == "complete")
            pending  = len(lessons) - complete

            summary = (
                f"[bold]Educational Lessons[/bold]  "
                f"Total [bold]{len(lessons)}[/bold]  │  "
                f"[green]✔[/green] Complete [green]{complete}[/green]  │  "
                f"⏳ Pending [yellow]{pending}[/yellow]"
            )
            console.print(summary)
            console.print()

            tbl = Table(box=box.SIMPLE_HEAD, border_style="dim", padding=(0, 1))
            tbl.add_column("Ch",     style="dim",         no_wrap=True, min_width=3)
            tbl.add_column("Pt",     style="dim",         no_wrap=True, min_width=3)
            tbl.add_column("",       no_wrap=True,        min_width=1)   # status symbol
            tbl.add_column("Title",  style="white",       no_wrap=False)
            tbl.add_column("YT ID",  style="dim cyan",    no_wrap=True)

            for l in lessons:
                status = l.get("status", "pending")
                sym    = "[green]✔[/green]" if status == "complete" else "[yellow]·[/yellow]"
                ch     = str(l.get("chapter", "?"))
                pt     = str(l.get("part",    "?"))
                title  = l.get("title", "")[:50]
                yt_id  = l.get("youtube_id", "")
                yt_str = yt_id[:11] if yt_id else ""
                tbl.add_row(ch, pt, sym, title, yt_str)

            console.print(tbl)
        except Exception as e:
            console.print(f"[red]Error loading lessons: {e}[/red]")
    else:
        console.print("[dim]No content_plan.json found.[/dim]")

    console.print()

    # ── Brain Rot topics ─────────────────────────────────────────
    if BRAINROT_PLAN_FILE.exists():
        try:
            bp     = json.loads(BRAINROT_PLAN_FILE.read_text())
            topics = bp.get("topics", [])
            done   = sum(1 for t in topics if t.get("status") == "complete")
            pend   = len(topics) - done

            summary = (
                f"[bold]Brain Rot Topics[/bold]  "
                f"Total [bold]{len(topics)}[/bold]  │  "
                f"[green]✔[/green] Complete [green]{done}[/green]  │  "
                f"⏳ Pending [yellow]{pend}[/yellow]"
            )
            console.print(summary)
            console.print()

            tbl2 = Table(box=box.SIMPLE_HEAD, border_style="dim", padding=(0, 1))
            tbl2.add_column("",      no_wrap=True,  min_width=1)
            tbl2.add_column("Title", style="white", no_wrap=False)

            for t in topics:
                st  = t.get("status", "pending")
                sym = "[green]✔[/green]" if st == "complete" else "[yellow]·[/yellow]"
                tit = t.get("title", "")[:60]
                tbl2.add_row(sym, tit)

            console.print(tbl2)
        except Exception:
            pass

    console.print()
    console.input("[dim]  Press Enter to return…[/dim]")


def ask_video_count(mode_label: str, default: int = 3) -> int:
    """Prompt user for batch video count (1–10). Warns if >5 on 8 GB RAM."""
    console.print()
    raw = Prompt.ask(
        f"  [bold]How many {mode_label} videos to generate?[/bold]",
        default=str(default),
    )
    try:
        n = int(raw)
    except ValueError:
        console.print(f"[red]  Invalid input. Using default ({default}).[/red]")
        n = default
    n = max(1, min(10, n))
    if n > 5:
        console.print(
            f"[yellow]  ⚠  {n} videos may stress 8 GB RAM — consider 3–5 for stability.[/yellow]"
        )
    console.print(f"[dim]  Generating {n} {mode_label} video(s)…[/dim]\n")
    return n
