# src/clipper_mode.py - Automatic Video Clipper (Vizard AI Replica)
# Wraps the kirat11X clipper pipeline.
# Setup: copy all .py files from kirat11X repo into src/clipper/
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

CLIPPER_DIR  = Path("src/clipper")
WORKSPACE    = Path("outputs/clipper")
PIPELINE_FILE = CLIPPER_DIR / "run_pipeline.py"


def _check_setup() -> bool:
    """Verify clipper pipeline files exist."""
    if not PIPELINE_FILE.exists():
        console.print(Panel(
            "[red]src/clipper/run_pipeline.py not found.[/red]\n\n"
            "Setup:\n"
            "  1. Clone/download kirat11X clipper repo\n"
            "  2. Copy all [bold].py[/bold] files into [cyan]src/clipper/[/cyan]\n"
            "  3. [cyan]touch src/clipper/__init__.py[/cyan]",
            title="[yellow]⚠  Clipper Not Configured[/yellow]",
            border_style="yellow",
        ))
        return False
    return True


def run_video_clipper():
    """Option 10 — Automatic Video Clipper."""
    console.print()
    console.print(Panel(
        "[bold cyan]Automatic Video Clipper[/bold cyan]\n"
        "Convert long YouTube videos / podcasts into viral vertical Shorts",
        border_style="cyan",
        padding=(0, 2),
    ))
    console.print()

    if not _check_setup():
        return

    url = Prompt.ask("  [bold]YouTube URL or local video path[/bold]").strip()
    if not url:
        console.print("[yellow]  Cancelled.[/yellow]")
        return

    WORKSPACE.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[cyan]🎬 Starting clipper pipeline…[/cyan]")
    console.print(f"[dim]  Input : {url}[/dim]")
    console.print(f"[dim]  Output: {WORKSPACE}[/dim]\n")

    try:
        cmd = [
            sys.executable, "run_pipeline.py",
            "--url", url,
            "--workspace", str(WORKSPACE.resolve()),
        ]
        with console.status("[cyan]Running clipper pipeline (this may take a while)…[/cyan]"):
            result = subprocess.run(
                cmd,
                cwd=CLIPPER_DIR.resolve(),
                check=True,
                capture_output=True,
                text=True,
            )

        if result.stdout:
            console.print(result.stdout)

        console.print(f"[green]✅ Clipper finished![/green]")
        console.print(f"[dim]📁 Vertical shorts → {WORKSPACE}/outputs/[/dim]")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Pipeline failed (exit {e.returncode})[/red]")
        if e.stdout:
            console.print(e.stdout)
        if e.stderr:
            console.print(f"[red]{e.stderr}[/red]")
    except FileNotFoundError:
        console.print("[red]❌ Python executable not found for subprocess.[/red]")
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
