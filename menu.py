# menu.py - SuperShorts interactive terminal menu
import os
import sys
import json
from pathlib import Path

CONTENT_PLAN_FILE  = Path("content_plan.json")
BRAINROT_PLAN_FILE = Path("brainrot_plan.json")

# ─── ANSI colour helpers ─────────────────────────────────────────
_IS_TTY = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    """Wrap text in ANSI colour code (no-op if not a TTY)."""
    return f"\033[{code}m{text}\033[0m" if _IS_TTY else text

def DIM(t):   return _c("2",      t)
def BOLD(t):  return _c("1",      t)
def CYAN(t):  return _c("96",     t)
def GREEN(t): return _c("92",     t)
def RED(t):   return _c("91",     t)
def GOLD(t):  return _c("93",     t)
def BLUE(t):  return _c("94",     t)
def MAG(t):   return _c("95",     t)
def GREY(t):  return _c("90",     t)


# ─── Banner ──────────────────────────────────────────────────────
BANNER_LINES = [
    r"  ____                       ____  _                _       ",
    r" / ___| _   _ _ __   ___ _ _/ ___|| |__   ___  _ __| |_ ___ ",
    r" \___ \| | | | '_ \ / _ \ '__\___ \| '_ \ / _ \| '__| __/ __|",
    r"  ___) | |_| | |_) |  __/ |   ___) | | | | (_) | |  | |_\__ \\",
    r" |____/ \__,_| .__/ \___|_|  |____/|_| |_|\___/|_|   \__|___/",
    r"              |_|",
]
TAGLINE = "  v2.0  │  Powered by Ollama + MoviePy  │  Local-AI Content Engine"

MENU_OPTIONS = [
    ("1", "📚", "Educational Videos",        "Long-form + linked Short (curriculum-based)"),
    ("2", "🧠", "Brain Rot Viral Shorts",     "Sensationalized AI shorts, 30–45 s"),
    ("3", "🎮", "Viral Gameplay Mode",        "Subway Surfers-style background + AI narration"),
    ("4", "🎓", "Tutorial Videos",            "~10-min deep-dive + linked Short"),
    ("5", "📈", "Learning Mode",              "Self-improvement analysis from past uploads"),
    ("6", "💡", "YouTube Studio Ideas",       "Real YT suggestions, thumbnails & scripts"),
    ("7", "📋", "View Content Plan",          "Browse lessons + brain rot topic tracker"),
    ("8", "🎭", "RotGen Character Mode",       "ByteBot AI character + gameplay + auto-subtitles"),
    ("9", "🚪", "Exit",                       ""),
]


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def _stats_line() -> str:
    """Quick stats: lessons done / brainrot done."""
    lessons_done = lessons_total = 0
    br_done = br_total = 0
    try:
        if CONTENT_PLAN_FILE.exists():
            plan = json.loads(CONTENT_PLAN_FILE.read_text())
            ls = plan.get("lessons", [])
            lessons_total = len(ls)
            lessons_done  = sum(1 for l in ls if l.get("status") == "complete")
    except Exception:
        pass
    try:
        if BRAINROT_PLAN_FILE.exists():
            bp = json.loads(BRAINROT_PLAN_FILE.read_text())
            ts = bp.get("topics", [])
            br_total = len(ts)
            br_done  = sum(1 for t in ts if t.get("status") == "complete")
    except Exception:
        pass
    parts = []
    if lessons_total:
        parts.append(f"Lessons {GREEN(str(lessons_done))}/{lessons_total}")
    if br_total:
        parts.append(f"Brain Rot {GREEN(str(br_done))}/{br_total}")
    return "  " + GREY("  ·  ".join(parts)) if parts else ""


def show_menu():
    clear_screen()

    # Banner
    for line in BANNER_LINES:
        print(CYAN(BOLD(line)))
    print(GOLD(TAGLINE))
    print()

    # Stats bar
    stats = _stats_line()
    if stats:
        print(stats)
        print()

    # Divider
    print(GREY("  " + "─" * 61))
    print()

    # Options
    for key, icon, label, desc in MENU_OPTIONS:
        num   = GOLD(f"  [{key}]")
        icon_ = icon + " "
        lbl   = BOLD(label)
        dsc   = GREY(f"  —  {desc}") if desc else ""
        print(f"{num}  {icon_}{lbl}{dsc}")

    print()
    print(GREY("  " + "─" * 61))
    print()
    return input(BOLD("  Select option: ")).strip()


# ─── Content Plan view ───────────────────────────────────────────

def view_content_plan():
    clear_screen()

    for line in BANNER_LINES:
        print(CYAN(BOLD(line)))
    print(GOLD(TAGLINE))
    print()
    print(BOLD(CYAN("  CONTENT PLAN")))
    print(GREY("  " + "─" * 61))
    print()

    # ── Educational lessons ──
    if CONTENT_PLAN_FILE.exists():
        try:
            plan     = json.loads(CONTENT_PLAN_FILE.read_text())
            lessons  = plan.get("lessons", [])
            complete = sum(1 for l in lessons if l.get("status") == "complete")
            pending  = len(lessons) - complete

            print(BOLD("  Educational Lessons"))
            print(f"  Total {BOLD(str(len(lessons)))}  │  "
                  f"{GREEN('✔')} Complete {GREEN(str(complete))}  │  "
                  f"⏳ Pending {GOLD(str(pending))}")
            print()
            print(GREY(f"  {'Ch':>3}  {'Pt':>3}  {'Status':>10}  Title"))
            print(GREY("  " + "─" * 58))

            for l in lessons:
                status  = l.get("status", "pending")
                symbol  = GREEN("✔") if status == "complete" else GOLD("·")
                ch      = str(l.get("chapter", "?"))
                pt      = str(l.get("part",    "?"))
                title   = l.get("title", "")[:46]
                yt_id   = l.get("youtube_id")
                yt_str  = GREY(f" ↗ yt/{yt_id[:8]}") if yt_id else ""
                print(f"  {ch:>3}  {pt:>3}  {symbol:>10}  {title}{yt_str}")
        except Exception as e:
            print(RED(f"  Error: {e}"))
    else:
        print(GREY("  No content_plan.json found."))

    print()

    # ── Brain Rot topics ──
    if BRAINROT_PLAN_FILE.exists():
        try:
            bp     = json.loads(BRAINROT_PLAN_FILE.read_text())
            topics = bp.get("topics", [])
            done   = sum(1 for t in topics if t.get("status") == "complete")
            pend   = len(topics) - done

            print(BOLD("  Brain Rot Topics"))
            print(f"  Total {BOLD(str(len(topics)))}  │  "
                  f"{GREEN('✔')} Complete {GREEN(str(done))}  │  "
                  f"⏳ Pending {GOLD(str(pend))}")
            print()
            print(GREY(f"  {'Status':>10}  Title"))
            print(GREY("  " + "─" * 50))
            for t in topics:
                st  = t.get("status", "pending")
                sym = GREEN("✔") if st == "complete" else GOLD("·")
                tit = t.get("title", "")[:54]
                print(f"  {sym:>10}  {tit}")
        except Exception:
            pass

    print()
    input(GREY("  Press Enter to return..."))
