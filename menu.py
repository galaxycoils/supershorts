"""menu.py - SuperShorts interactive terminal menu"""
import os
import json
from pathlib import Path

CONTENT_PLAN_FILE = Path("content_plan.json")

BANNER = r"""
  ____                       ____  _                _
 / ___| _   _ _ __   ___ _ _/ ___|| |__   ___  _ __| |_ ___
 \___ \| | | | '_ \ / _ \ '__\___ \| '_ \ / _ \| '__| __/ __|
  ___) | |_| | |_) |  __/ |   ___) | | | | (_) | |  | |_\__ \
 |____/ \__,_| .__/ \___|_|  |____/|_| |_|\___/|_|   \__|___/
              |_|
                          v1.0  |  Powered by Ollama + MoviePy
"""


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def show_banner():
    print(BANNER)
    print("=" * 65)
    print()


def show_menu():
    print("  [1]  Start YouTube Video Generation")
    print("  [2]  Generate Brain Rot Shorts")
    print("  [3]  View Content Plan")
    print("  [4]  Exit")
    print()
    return input("  Select option: ").strip()


def view_content_plan():
    clear_screen()
    show_banner()
    print("  CONTENT PLAN\n")
    if not CONTENT_PLAN_FILE.exists():
        print("  No content_plan.json found.\n")
        input("  Press Enter to return...")
        return
    try:
        with open(CONTENT_PLAN_FILE) as f:
            plan = json.load(f)
        lessons = plan.get("lessons", [])
        complete = sum(1 for l in lessons if l.get("status") == "complete")
        pending = len(lessons) - complete
        print(f"  Total: {len(lessons)}  |  Complete: {complete}  |  Pending: {pending}\n")
        print(f"  {'Ch':>3}  {'Pt':>3}  {'Status':>10}  Title")
        print("  " + "-" * 60)
        for l in lessons:
            status = l.get("status", "pending")
            symbol = "✓" if status == "complete" else "·"
            ch = l.get("chapter", "?")
            pt = l.get("part", "?")
            title = l.get("title", "")[:45]
            print(f"  {ch:>3}  {pt:>3}  {symbol:>10}  {title}")
    except Exception as e:
        print(f"  Error loading plan: {e}")
    print()
    input("  Press Enter to return...")


def menu_loop():
    while True:
        clear_screen()
        show_banner()
        choice = show_menu()

        if choice == '1':
            print("\n  Starting lesson video generation pipeline...\n")
            try:
                from main import main as run_pipeline
                run_pipeline()
            except Exception as e:
                print(f"\n  Pipeline error: {e}")
            input("\n  Press Enter to return to menu...")

        elif choice == '2':
            print("\n  Starting Brain Rot Shorts generator...\n")
            try:
                from src.brainrot import run_brainrot_pipeline
                run_brainrot_pipeline()
            except Exception as e:
                print(f"\n  Brain rot pipeline error: {e}")
            input("\n  Press Enter to return to menu...")

        elif choice == '3':
            view_content_plan()

        elif choice == '4':
            print("\n  Bye.\n")
            break

        else:
            print("  Invalid choice.")
            input("  Press Enter to continue...")


if __name__ == "__main__":
    menu_loop()
