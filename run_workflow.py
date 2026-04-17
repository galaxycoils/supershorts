#!/usr/bin/env python3
# run_workflow.py - SuperShorts Workflow Engine
#
# Usage:
#   python run_workflow.py workflows/daily.workflow.json
#   python run_workflow.py workflows/tcm-weekly.workflow.json
#   python run_workflow.py workflows/full-pipeline.workflow.json
#   python run_workflow.py --list
#   python run_workflow.py --validate workflows/daily.workflow.json

import gc
import sys
import json
import time
import argparse
import datetime
import traceback
from pathlib import Path
from collections import defaultdict
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich import box

console = Console()

LOG_DIR     = Path("output/workflow_logs")
OUTPUT_DIR  = Path("output")

# ─── Task function registry ───────────────────────────────────────

def ensure_output_dir(**_):
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "uploaded").mkdir(exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    console.print("[dim]📁 Output dirs ready[/dim]")
    return {"status": "ok"}


def run_educational(count: int = 2, **_):
    from main import main_flow
    console.print(f"[cyan]📚 Educational Videos × {count}[/cyan]")
    main_flow(lessons_per_run=count)
    gc.collect()
    return {"mode": "educational", "count": count}


def run_brainrot(count: int = 3, **_):
    from src.brainrot import run_brainrot_pipeline
    console.print(f"[cyan]🧠 Brain Rot Shorts × {count}[/cyan]")
    run_brainrot_pipeline(count)
    gc.collect()
    return {"mode": "brainrot", "count": count}


def run_rotgen(count: int = 1, **_):
    from src.rotgen import run_rotgen_pipeline
    console.print(f"[cyan]🎭 RotGen Videos × {count}[/cyan]")
    run_rotgen_pipeline(count)
    gc.collect()
    return {"mode": "rotgen", "count": count}


def run_tcm_batch(count: int = 3, focus: str = "Traditional Chinese Medicine (TCM)",
                  extra: str = "", **_):
    """Run TCM mode non-interactively (no prompts)."""
    import ollama
    from src.tcm_mode import (
        TCM_PLAN_FILE, _generate_tcm_curriculum, _show_plan_status
    )
    from src.generator import generate_lesson_content, text_to_speech, generate_visuals, compose_video, _clamp_words
    from src.browser_uploader import upload_to_youtube_browser as upload_to_youtube
    from src.learning import log_upload
    from main import cleanup_after_upload

    console.print(f"[cyan]🌿 TCM Videos × {count} ({focus})[/cyan]")

    plan = None
    if TCM_PLAN_FILE.exists():
        try:
            existing = json.loads(TCM_PLAN_FILE.read_text())
            pending = sum(1 for l in existing.get("lessons", []) if l.get("status") == "pending")
            if pending > 0:
                plan = existing
        except Exception:
            pass

    if plan is None:
        with console.status(f"[cyan]Generating {focus} curriculum…[/cyan]"):
            plan = _generate_tcm_curriculum(focus, extra)
        TCM_PLAN_FILE.write_text(json.dumps(plan, indent=2))

    pending_lessons = [l for l in plan.get("lessons", []) if l.get("status") == "pending"]
    if not pending_lessons:
        for l in plan["lessons"]:
            l["status"] = "pending"
            l["youtube_id"] = None
        TCM_PLAN_FILE.write_text(json.dumps(plan, indent=2))
        pending_lessons = plan["lessons"]

    OUTPUT_DIR.mkdir(exist_ok=True)
    produced = 0

    for lesson in pending_lessons[:count]:
        try:
            uid = f"{datetime.datetime.now().strftime('%Y%m%d')}_tcm_ch{lesson['chapter']}"
            with console.status(f"[cyan]Generating: {lesson['title']}…[/cyan]"):
                content = generate_lesson_content(lesson["title"])

            raw_short = content.get("short_form_highlight") or lesson["title"]
            short_script = _clamp_words(raw_short, min_w=99, max_w=127)
            short_audio = text_to_speech(short_script, OUTPUT_DIR / f"tcm_audio_{uid}.mp3")
            slide_path = generate_visuals(
                output_dir=OUTPUT_DIR / f"tcm_slides_{uid}",
                video_type="short",
                slide_content={"title": lesson["title"], "content": content.get("short_form_highlight", "")},
                slide_number=1, total_slides=1,
            )
            short_path = OUTPUT_DIR / f"tcm_short_{uid}.mp4"
            compose_video([slide_path], [short_audio], short_path, "short",
                          lesson["title"], script=short_script)
            try:
                Path(short_audio).unlink(missing_ok=True)
            except Exception:
                pass

            hashtags = "#TCM #TraditionalChineseMedicine #Wellness #Health #Shorts"
            vid_id = upload_to_youtube(
                short_path,
                f"{lesson['title']} #Shorts",
                f"{content.get('short_form_highlight', '')}\n\n{hashtags}",
                "TCM,Traditional Chinese Medicine,Wellness",
                None,
            )
            if vid_id:
                log_upload(lesson["title"], vid_id, "tcm")
                lesson["status"] = "complete"
                lesson["youtube_id"] = vid_id
                TCM_PLAN_FILE.write_text(json.dumps(plan, indent=2))
                cleanup_after_upload(short_path, lesson["title"], vid_id, "tcm")
                produced += 1
                if produced < count:
                    console.print("[yellow]⏳ 30 s cooldown…[/yellow]")
                    time.sleep(30)
        except Exception as e:
            console.print(f"[red]❌ TCM task failed: {e}[/red]")
        gc.collect()

    return {"mode": "tcm", "count": count, "produced": produced}


def run_learning(**_):
    from src.learning import suggest_improvements
    console.print("[cyan]📈 Learning Mode Analysis[/cyan]")
    result = suggest_improvements()
    return {"mode": "learning", "result": result[:80] if isinstance(result, str) else str(result)}


def write_summary(workflow_name: str = "workflow", task_results: dict = None, **_):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    summary = {
        "workflow": workflow_name,
        "completed_at": str(datetime.datetime.now()),
        "tasks": task_results or {},
    }
    log_file = LOG_DIR / f"{ts}_{workflow_name}.json"
    log_file.write_text(json.dumps(summary, indent=2))
    console.print(f"[green]📝 Summary → {log_file}[/green]")
    return {"log_file": str(log_file)}


# ─── Function registry ────────────────────────────────────────────

TASK_FNS: dict[str, Any] = {
    "ensure_output_dir": ensure_output_dir,
    "run_educational":   run_educational,
    "run_brainrot":      run_brainrot,
    "run_rotgen":        run_rotgen,
    "run_tcm_batch":     run_tcm_batch,
    "run_learning":      run_learning,
    "write_summary":     write_summary,
}


# ─── Dependency graph ─────────────────────────────────────────────

def build_graph(tasks: list) -> dict:
    """Return {task_id: set(dep_ids)}."""
    return {t["id"]: set(t.get("depends_on", [])) for t in tasks}


def topo_sort(graph: dict) -> list[list[str]]:
    """Return tasks grouped into execution waves (each wave can run in parallel)."""
    remaining = {k: set(v) for k, v in graph.items()}
    waves = []
    while remaining:
        ready = [k for k, deps in remaining.items() if not deps]
        if not ready:
            raise ValueError(f"Circular dependency detected among: {list(remaining.keys())}")
        waves.append(ready)
        for done in ready:
            del remaining[done]
            for deps in remaining.values():
                deps.discard(done)
    return waves


# ─── Engine ───────────────────────────────────────────────────────

class WorkflowRunner:
    def __init__(self, workflow: dict):
        self.workflow   = workflow
        self.name       = workflow.get("name", "unnamed")
        self.task_map   = {t["id"]: t for t in workflow.get("tasks", [])}
        self.results: dict[str, dict] = {}

    def _run_task(self, task: dict) -> dict:
        fn_name = task.get("fn")
        if fn_name not in TASK_FNS:
            raise ValueError(f"Unknown task function: {fn_name!r}")

        args = dict(task.get("args", {}))
        args["workflow_name"] = self.name
        args["task_results"]  = self.results

        max_attempts = task.get("retry", {}).get("attempts", 1) + 1
        delay        = task.get("retry", {}).get("delay", 5)

        for attempt in range(1, max_attempts + 1):
            try:
                result = TASK_FNS[fn_name](**args)
                return result or {}
            except Exception as e:
                if attempt < max_attempts:
                    console.print(
                        f"[yellow]  Retry {attempt}/{max_attempts - 1} for '{task['name']}' "
                        f"in {delay}s… ({e})[/yellow]"
                    )
                    time.sleep(delay)
                else:
                    raise

    def run(self) -> dict:
        tasks   = self.workflow.get("tasks", [])
        graph   = build_graph(tasks)
        waves   = topo_sort(graph)

        start   = time.time()
        console.print()
        console.print(Panel(
            f"[bold cyan]{self.workflow.get('description', self.name)}[/bold cyan]",
            title=f"[bold]▶  {self.name}[/bold]",
            border_style="cyan",
            padding=(0, 2),
        ))
        console.print()

        total   = len(tasks)
        done    = 0
        failed  = []

        for wave_idx, wave in enumerate(waves):
            console.print(Rule(f"[dim]Wave {wave_idx + 1}/{len(waves)}[/dim]", style="dim"))
            for task_id in wave:
                task = self.task_map[task_id]
                console.print(f"\n[bold yellow]  → {task['name']}[/bold yellow]")
                t0 = time.time()
                try:
                    result = self._run_task(task)
                    elapsed = time.time() - t0
                    self.results[task_id] = {"status": "ok", "elapsed": round(elapsed, 1), **result}
                    console.print(f"    [green]✔[/green] done in {elapsed:.1f}s")
                    done += 1
                except Exception as e:
                    elapsed = time.time() - t0
                    self.results[task_id] = {"status": "failed", "elapsed": round(elapsed, 1), "error": str(e)}
                    console.print(f"    [red]✘ {e}[/red]")
                    failed.append(task_id)
                    traceback.print_exc()
                    # Don't abort — continue remaining tasks

        total_elapsed = time.time() - start

        # ── Summary table ─────────────────────────────────────────
        console.print()
        console.print(Rule(style="dim"))
        tbl = Table(box=box.SIMPLE_HEAD, border_style="dim", padding=(0, 1))
        tbl.add_column("Task",    style="white",      no_wrap=True)
        tbl.add_column("Status",  no_wrap=True,       min_width=8)
        tbl.add_column("Time",    style="dim",        no_wrap=True, min_width=7)
        for tid, res in self.results.items():
            t = self.task_map[tid]
            sym = "[green]✔  ok[/green]" if res["status"] == "ok" else "[red]✘  fail[/red]"
            tbl.add_row(t["name"], sym, f"{res['elapsed']}s")
        console.print(tbl)

        status_str = "[green]PASSED[/green]" if not failed else f"[red]FAILED ({len(failed)} tasks)[/red]"
        console.print(
            f"\n  {status_str}  "
            f"[dim]{done}/{total} tasks · {total_elapsed:.1f}s total[/dim]"
        )

        return {
            "workflow":  self.name,
            "status":    "failed" if failed else "ok",
            "elapsed":   round(total_elapsed, 1),
            "tasks":     self.results,
            "failed":    failed,
        }


# ─── CLI ─────────────────────────────────────────────────────────

def list_workflows():
    wf_dir = Path("workflows")
    files  = sorted(wf_dir.glob("*.workflow.json"))
    if not files:
        console.print("[yellow]No workflow files found in workflows/[/yellow]")
        return
    tbl = Table(box=box.SIMPLE_HEAD, border_style="dim", padding=(0, 1))
    tbl.add_column("File",        style="cyan",  no_wrap=True)
    tbl.add_column("Name",        style="white", no_wrap=True)
    tbl.add_column("Description", style="dim",   no_wrap=True)
    tbl.add_column("Trigger",     style="yellow",no_wrap=True)
    for f in files:
        try:
            wf = json.loads(f.read_text())
            trigger = wf.get("trigger", {}).get("config", {}).get("schedule", wf.get("trigger", {}).get("type", "?"))
            tbl.add_row(f.name, wf.get("name", "?"), wf.get("description", "")[:50], trigger)
        except Exception:
            tbl.add_row(f.name, "?", "parse error", "?")
    console.print(tbl)


def validate_workflow(path: str):
    wf = json.loads(Path(path).read_text())
    tasks = wf.get("tasks", [])
    graph = build_graph(tasks)
    try:
        waves = topo_sort(graph)
    except ValueError as e:
        console.print(f"[red]❌ Validation failed: {e}[/red]")
        return False

    # Check all fn references exist
    errors = []
    for t in tasks:
        fn = t.get("fn")
        if fn and fn not in TASK_FNS:
            errors.append(f"Task '{t['id']}': unknown function '{fn}'")
        for dep in t.get("depends_on", []):
            if dep not in graph:
                errors.append(f"Task '{t['id']}': dependency '{dep}' not found")

    if errors:
        for e in errors:
            console.print(f"[red]  ✘ {e}[/red]")
        return False

    console.print(f"[green]✔ Valid — {len(tasks)} tasks in {len(waves)} waves[/green]")
    for i, w in enumerate(waves, 1):
        console.print(f"  Wave {i}: {', '.join(w)}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="SuperShorts Workflow Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_workflow.py workflows/daily.workflow.json
  python run_workflow.py workflows/tcm-weekly.workflow.json
  python run_workflow.py --list
  python run_workflow.py --validate workflows/daily.workflow.json
        """,
    )
    parser.add_argument("workflow", nargs="?", help="Path to .workflow.json file")
    parser.add_argument("--list",     action="store_true", help="List available workflows")
    parser.add_argument("--validate", metavar="FILE",      help="Validate a workflow file")
    args = parser.parse_args()

    if args.list:
        list_workflows()
        return

    if args.validate:
        ok = validate_workflow(args.validate)
        sys.exit(0 if ok else 1)

    if not args.workflow:
        parser.print_help()
        sys.exit(1)

    wf_path = Path(args.workflow)
    if not wf_path.exists():
        console.print(f"[red]❌ File not found: {wf_path}[/red]")
        sys.exit(1)

    wf = json.loads(wf_path.read_text())
    runner = WorkflowRunner(wf)
    result = runner.run()
    sys.exit(0 if result["status"] == "ok" else 1)


if __name__ == "__main__":
    main()
