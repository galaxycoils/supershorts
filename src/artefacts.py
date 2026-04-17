"""Post-upload bookkeeping: delete big local artefacts and leave a breadcrumb."""
import json
import os
import shutil
import datetime
from pathlib import Path

HISTORY_FILE = Path("upload_history.json")


def _append_history(entry: dict) -> None:
    try:
        data = json.loads(HISTORY_FILE.read_text()) if HISTORY_FILE.exists() else []
        if not isinstance(data, list):
            data = []
    except Exception:
        data = []
    data.append(entry)
    HISTORY_FILE.write_text(json.dumps(data, indent=2))


def _size_mb(path: Path) -> float:
    try:
        return round(path.stat().st_size / (1024 * 1024), 2)
    except Exception:
        return 0.0


def record_and_cleanup(
    *,
    mode: str,
    title: str,
    video_id: str | None,
    video_path: Path | str | None,
    audio_paths: list | None = None,
    slide_dir: Path | str | None = None,
    thumbnail_path: Path | str | None = None,
    extra_paths: list | None = None,
) -> None:
    """
    Record a breadcrumb in upload_history.json and delete the big files.

    Only runs deletion when video_id is truthy — failed uploads keep their
    files around for debugging/retry.
    """
    if not video_id:
        return

    video_path = Path(video_path) if video_path else None
    deleted: list[str] = []
    original_size_mb = _size_mb(video_path) if video_path else 0.0

    targets: list[Path] = []
    if video_path:
        targets.append(video_path)
    for a in audio_paths or []:
        if a:
            targets.append(Path(a))
    if thumbnail_path:
        targets.append(Path(thumbnail_path))
    for p in extra_paths or []:
        if p:
            targets.append(Path(p))

    for p in targets:
        try:
            if p.exists():
                p.unlink()
                deleted.append(str(p))
        except Exception as e:
            print(f"  cleanup: could not delete {p}: {e}")

    if slide_dir:
        sd = Path(slide_dir)
        if sd.exists() and sd.is_dir():
            try:
                shutil.rmtree(sd)
                deleted.append(str(sd))
            except Exception as e:
                print(f"  cleanup: could not remove dir {sd}: {e}")

    _append_history({
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "title": title,
        "video_id": video_id,
        "original_size_mb": original_size_mb,
        "deleted": deleted,
    })
    print(f"  🧹 cleaned {len(deleted)} artefact(s), freed ~{original_size_mb} MB")


def write_srt(script_text: str, audio_duration: float, path: Path | str,
              words_per_chunk: int = 6) -> Path:
    """Write a simple SRT file by splitting script into evenly-timed chunks.

    Used so YouTube can ingest accurate captions at upload time instead of
    us burning them into the frame. Timings are proportional to word counts.
    """
    path = Path(path)
    words = script_text.split()
    if not words or audio_duration <= 0:
        path.write_text("")
        return path

    chunks = [" ".join(words[i:i + words_per_chunk])
              for i in range(0, len(words), words_per_chunk)]
    total_words = sum(len(c.split()) for c in chunks)

    def fmt(t: float) -> str:
        if t < 0:
            t = 0
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines: list[str] = []
    cursor = 0.0
    for i, chunk in enumerate(chunks, start=1):
        n = len(chunk.split())
        dur = (n / total_words) * audio_duration
        start, end = cursor, cursor + dur
        cursor = end
        lines.append(str(i))
        lines.append(f"{fmt(start)} --> {fmt(end)}")
        lines.append(chunk)
        lines.append("")

    path.write_text("\n".join(lines))
    return path
