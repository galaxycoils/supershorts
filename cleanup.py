"""
cleanup.py — SuperShorts output folder pruner
Removes intermediate .wav audio segments from output/ while keeping
slides, thumbnails, mp4 references, and uploaded/ JSON metadata.

Usage:
    python3 cleanup.py            # dry-run (shows what would be deleted)
    python3 cleanup.py --delete   # actually delete
    python3 cleanup.py --days 7   # only touch dirs older than 7 days
"""
import argparse
import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
OUTPUT_DIR   = PROJECT_ROOT / "output"

# Extensions considered safe to prune (large intermediary files)
PRUNE_EXTENSIONS = {".wav", ".mp3"}
# Patterns to never delete
KEEP_PATTERNS = {"uploaded", "workflow_logs"}


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def main():
    p = argparse.ArgumentParser(description="SuperShorts output cleanup")
    p.add_argument("--delete", action="store_true", help="Actually delete files (default: dry-run)")
    p.add_argument("--days",   type=int, default=0,  help="Only prune dirs older than N days (0 = all)")
    args = p.parse_args()

    if not OUTPUT_DIR.exists():
        print(f"Output dir not found: {OUTPUT_DIR}")
        return

    cutoff = None
    if args.days > 0:
        cutoff = datetime.datetime.now() - datetime.timedelta(days=args.days)

    total_freed = 0
    file_count  = 0
    pruned_dirs = 0

    for subdir in sorted(OUTPUT_DIR.iterdir()):
        if not subdir.is_dir():
            continue
        if subdir.name in KEEP_PATTERNS:
            continue

        if cutoff:
            mtime = datetime.datetime.fromtimestamp(subdir.stat().st_mtime)
            if mtime > cutoff:
                continue

        for f in subdir.rglob("*"):
            if f.is_file() and f.suffix.lower() in PRUNE_EXTENSIONS:
                size = f.stat().st_size
                total_freed += size
                file_count  += 1
                action = "DELETE" if args.delete else "would delete"
                print(f"  {action}: {f.relative_to(PROJECT_ROOT)}  ({human(size)})")
                if args.delete:
                    f.unlink()

        pruned_dirs += 1

    print()
    print(f"{'Deleted' if args.delete else 'Would free'}:  {human(total_freed)}")
    print(f"Files:  {file_count}  across  {pruned_dirs}  output dirs")
    if not args.delete and file_count > 0:
        print("\nRun with --delete to actually free this space.")


if __name__ == "__main__":
    main()
