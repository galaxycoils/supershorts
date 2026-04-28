# Daily Strategy

Automated daily strategy improvement loop. Runs every morning at **09:00 UTC
(05:00 ET / 02:00 PT)** via `.github/workflows/daily-strategy.yml`.

## How it works

1. Cron fires `scripts/daily_strategy.py`.
2. The script loads:
   - `strategy/CONTEXT.md` — static product brief (cached prompt prefix)
   - `strategy/latest.md` — yesterday's plan (or `seed.md` on day 1)
3. Calls Claude Opus 4.7 with adaptive thinking. Asks it to:
   - Critique yesterday's plan
   - Propose today's hypothesis + experiment
   - Update rolling "what's working / not working" lists
4. Writes the new plan to:
   - `strategy/daily/YYYY-MM-DD.md` — the dated archive
   - `strategy/latest.md` — the rolling head, used as input for tomorrow
5. Commits and pushes both files.

## Files

- `CONTEXT.md` — static product context. Edit when the **product** changes
  (new modes, new assets, new platforms). Not edited by the bot.
- `seed.md` — day-zero bootstrap plan. Read once, then never again.
- `latest.md` — rolling head plan. Overwritten daily. **Do not hand-edit
  during a run** or you'll lose the change.
- `daily/YYYY-MM-DD.md` — append-only daily archive. Safe to read, don't
  delete.

## Setup

Add `ANTHROPIC_API_KEY` to repo secrets:

```
Settings → Secrets and variables → Actions → New repository secret
Name:  ANTHROPIC_API_KEY
Value: sk-ant-api03-...
```

## Manual run

The workflow has `workflow_dispatch`, so you can also trigger it manually:

```
Actions → Daily Strategy → Run workflow
```

## Changing the time

Edit the cron expression in `.github/workflows/daily-strategy.yml`:

```yaml
on:
  schedule:
    - cron: '0 9 * * *'   # 09:00 UTC = 5am ET (EDT) / 4am ET (EST) / 2am PT (PDT)
```

GitHub Actions cron is **always UTC** — it does not respect your local
timezone or DST. If you want exactly 5am local year-round, run twice a
year (DST switch) or use a timezone-aware wrapper.

## Cost

Daily run on Opus 4.7 with prompt caching: ~$0.05–0.20 per day depending
on plan length. ~$2–6/month.
