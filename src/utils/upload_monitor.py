"""Upload monitoring — logs UploadMetrics to JSONL on disk."""
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from src.infrastructure.browser_uploader import UploadMetrics


def _default_log_path() -> Path:
    return Path.home() / ".supershorts" / "upload_log.jsonl"


def log_upload_metric(metric: UploadMetrics, log_path: Optional[Path] = None) -> None:
    """Append a single UploadMetrics record as a JSON line."""
    path = log_path if log_path is not None else _default_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    record = asdict(metric)
    record["timestamp"] = datetime.now(tz=timezone.utc).isoformat()
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


class UploadMonitor:
    """Stateful monitor that records metrics in memory and persists to JSONL."""

    def __init__(self, log_path: Optional[Path] = None) -> None:
        self.log_path: Path = log_path if log_path is not None else _default_log_path()
        self.history: List[UploadMetrics] = []

    def record(self, metric: UploadMetrics) -> None:
        """Record a metric in memory and flush to disk."""
        self.history.append(metric)
        log_upload_metric(metric, log_path=self.log_path)

    def last_success(self) -> Optional[UploadMetrics]:
        """Return the most recent successful metric, or None."""
        for m in reversed(self.history):
            if m.success:
                return m
        return None

    def summary(self) -> dict:
        """Return a dict with total/successes/failures counts."""
        total = len(self.history)
        successes = sum(1 for m in self.history if m.success)
        return {
            "total": total,
            "successes": successes,
            "failures": total - successes,
        }
