# menu.py - SuperShorts interactive terminal menu
import os
import json
from pathlib import Path

CONTENT_PLAN_FILE = Path("content_plan.json")
BRAINROT_PLAN_FILE = Path("brainrot_plan.json")

BANNER = r"""
  ____                       ____  _                _
 / ___| _   _ _ __   ___ _ _/ ___|| |__   ___  _ __| |_ ___
 \___ \| | | | '_ \ / _ \ '__\___ \| '_ \ / _ \| '__| __/ __|
  ___) | |_| | |_) |  __/ |   ___) | | | | (_) | |  | |_\__ \
 |____/ \__,_| .__/ \___|_|  |____/|_| |_|\___/|_|   \__|___/
              |_|
                    v2.0  |  Powered by Ollama + MoviePy
"""


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def show_menu():
    clear_screen()
    print(BANNER)
    print("=" * 65)
    print()
    print("  [1]  Educational Videos (Long + Shorts)")
    print("  [2]  Brain Rot Viral Shorts")
    print("  [3]  Viral Gameplay Mode (Subway Surfers style)")
    print("  [4]  Tutorial Videos (~10 min + linked Short)")
    print("  [5]  Learning Mode (Self-improvement analysis)")
    print("  [6]  YouTube Studio Idea Generator")
    print("  [7]  View Content Plan")
    print("  [8]  Exit")
    print()
    print("=" * 65)
    return input("  Select option: ").strip()


def view_content_plan():
    clear_screen()
    print(BANNER)
    print("  CONTENT PLAN\n")

    # Educational lessons
    if CONTENT_PLAN_FILE.exists():
        try:
            plan = json.loads(CONTENT_PLAN_FILE.read_text())
            lessons = plan.get("lessons", [])
            complete = sum(1 for l in lessons if l.get("status") == "complete")
            pending = len(lessons) - complete
            print(f"  Lessons: {len(lessons)}  |  Complete: {complete}  |  Pending: {pending}\n")
            print(f"  {'Ch':>3}  {'Pt':>3}  {'Status':>10}  Title")
            print("  " + "-" * 60)
            for l in lessons:
                status = l.get("status", "pending")
                symbol = "+" if status == "complete" else "."
                ch = l.get("chapter", "?")
                pt = l.get("part", "?")
                title = l.get("title", "")[:45]
                print(f"  {ch:>3}  {pt:>3}  {symbol:>10}  {title}")
        except Exception as e:
            print(f"  Error loading lesson plan: {e}")
    else:
        print("  No content_plan.json found.\n")

    # Brain rot topics
    if BRAINROT_PLAN_FILE.exists():
        try:
            plan = json.loads(BRAINROT_PLAN_FILE.read_text())
            topics = plan.get("topics", [])
            br_complete = sum(1 for t in topics if t.get("status") == "complete")
            br_pending = len(topics) - br_complete
            print(f"\n  Brain Rot: {len(topics)}  |  Complete: {br_complete}  |  Pending: {br_pending}")
        except Exception:
            pass

    print()
    input("  Press Enter to return...")
