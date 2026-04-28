"""Daily strategy improvement loop.

Reads yesterday's plan (or the seed on day 1), asks Claude to critique it
and produce today's plan, writes the result to disk. Designed to run
unattended from a GitHub Actions cron.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

REPO_ROOT = Path(__file__).resolve().parent.parent
STRATEGY_DIR = REPO_ROOT / "strategy"
DAILY_DIR = STRATEGY_DIR / "daily"
CONTEXT_PATH = STRATEGY_DIR / "CONTEXT.md"
LATEST_PATH = STRATEGY_DIR / "latest.md"
SEED_PATH = STRATEGY_DIR / "seed.md"

MODEL = "claude-opus-4-7"

SYSTEM_PROMPT = """\
You are the SuperShorts daily strategist. Your job: help the operator ship
short-form video content (YouTube Shorts, TikTok, Reels) that maximizes
algorithmic distribution, watch time, and monetization, within platform
ToS and without manipulating users in deceptive ways.

You are a senior short-form-video PM + creator strategist. You have
deep working knowledge of:
- The YouTube Shorts ranking model (retention curves, swipe-away rate,
  loop counting, comment velocity, watch-through to next video)
- TikTok For You Page mechanics (completion rate, share rate, re-watch)
- Hook architecture (first-frame promise, pattern interrupts,
  open-loops)
- Caption pacing (words per second, on-screen text density, animated
  captions)
- Voice + character casting for AI-generated content
- Cross-platform repost economics

Style:
- Be specific. "Use a hook" is useless. "Open with a number-based
  contradiction in the first 0.8s" is useful.
- Reference yesterday's plan explicitly. Call out what was right, what
  was wrong, what the operator likely couldn't measure yet.
- One central hypothesis per day. Don't propose 5 experiments — propose
  one experiment that can actually be run.
- Stay inside the SuperShorts pipeline's actual capabilities (see the
  product context). Don't suggest features the system doesn't have.
- Respect ToS. No deceptive thumbnails, no fake engagement.

Output format: a markdown document with the following sections, in
order:

# Strategy — {DATE}

## Yesterday's plan, reviewed
- What was right
- What was wrong or untested
- What the operator likely couldn't measure yet

## Today's central hypothesis
(one sentence)

## Today's experiment
- Concrete shippable description: which mode, which voice, which
  hook structure, which background, which caption style, which
  posting times.
- 3 to 5 line description max — the operator should be able to
  produce this today without further design work.

## Measurement
- Exactly which numbers to look at tomorrow.
- Decision rule: "if X > Y, double down; if X < Z, kill and try W."

## Rolling: what's working
(carry forward + append from yesterday's list, with one-line evidence)

## Rolling: what's not working
(carry forward + append from yesterday's list, with one-line evidence)

## Open questions for tomorrow
(2 to 4 bullets — these become candidate hypotheses for future days)
"""


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def previous_plan() -> str:
    """Return the rolling head plan, or the seed on first run."""
    if LATEST_PATH.exists():
        return load_text(LATEST_PATH)
    return load_text(SEED_PATH)


def build_user_message(today: str, prev_plan: str) -> str:
    return (
        f"Today is {today}.\n\n"
        f"Below is the most recent strategy plan. Critique it and "
        f"produce today's plan in the format described in the system "
        f"prompt.\n\n"
        f"--- PREVIOUS PLAN ---\n\n"
        f"{prev_plan}\n"
    )


def generate_plan() -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY not set — add it to repo secrets.")

    client = anthropic.Anthropic(api_key=api_key)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    context = load_text(CONTEXT_PATH)
    prev = previous_plan()

    system = [
        {"type": "text", "text": SYSTEM_PROMPT},
        {
            "type": "text",
            "text": f"## Product context\n\n{context}",
            "cache_control": {"type": "ephemeral"},
        },
    ]

    with client.messages.stream(
        model=MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=system,
        messages=[{"role": "user", "content": build_user_message(today, prev)}],
    ) as stream:
        message = stream.get_final_message()

    text_blocks = [b.text for b in message.content if b.type == "text"]
    plan = "\n".join(text_blocks).strip()
    if not plan:
        sys.exit("Model returned no text content.")

    usage = message.usage
    print(
        f"[daily_strategy] tokens: input={usage.input_tokens} "
        f"output={usage.output_tokens} "
        f"cache_read={usage.cache_read_input_tokens} "
        f"cache_write={usage.cache_creation_input_tokens}",
        file=sys.stderr,
    )
    return plan


def write_plan(plan: str) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    dated = DAILY_DIR / f"{today}.md"
    dated.write_text(plan + "\n", encoding="utf-8")
    LATEST_PATH.write_text(plan + "\n", encoding="utf-8")
    return dated


def main() -> int:
    plan = generate_plan()
    dated = write_plan(plan)
    print(f"wrote {dated.relative_to(REPO_ROOT)}")
    print(f"wrote {LATEST_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
