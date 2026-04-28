# SuperShorts Product Context

This file is the static "product brief" passed to the daily strategy run as a
cacheable prompt prefix. Edit when the product itself changes — not daily.

## Product

SuperShorts is an AI-powered short-form video pipeline that generates,
renders, and uploads YouTube Shorts, TikToks, and Reels on autopilot. It
runs locally via Ollama / LM Studio (LLM) and Piper TTS, and renders with
MoviePy. It uses Selenium to upload to YouTube Studio.

## Production modes

- **Brainrot** — fast viral facts over looping gameplay (Subway Surfers,
  Minecraft parkour, etc.). Highest engagement / addiction potential. Hook in
  first 1.5s, payoff every 4-6s.
- **TCM (Teaches)** — educational curriculum-style content. Lower velocity,
  longer watch time per viewer.
- **RotGen** — split-screen AI character dialogue (Patrick/Spongebob,
  Stewie/Peter, etc.). Story-driven; relies on character voice consistency.
- **Clipper** — long-form video → vertical short-form clips. Depends on
  source quality; good for trend-jacking.

## Assets available

- 9+ Piper voices (Adam, Antoni, Arnold, Amy, Joe, Kristin, Rachel + more)
- Character avatars: Patrick, Peter Griffin, Spongebob, Squidward, Stewie,
  Trump, Peter Finance
- Background gameplay loops in `assets/viral_gameplay/`
- Local LLMs (Ollama default models)

## Monetization surfaces

- YouTube Shorts ad revenue (RPM scales with watch time + retention)
- YouTube channel sponsorships (scales with subscriber count + niche fit)
- TikTok Creator Rewards (longer-form vertical)
- Affiliate links in pinned comments / channel descriptions
- Future: cross-platform repost (TikTok, Instagram Reels — v3.7 roadmap)

## Algorithmic engagement levers (the platforms reward these)

- **Hook strength** — retention in first 1.5s determines whether the algo
  surfaces it at all
- **Average view duration** as % of length — primary ranking signal
- **Loop watches** — counted as additional views; pattern-match for
  loopable endings
- **Comment velocity** — early comments boost ranking; engineer
  controversy / call-to-comment hooks
- **Share rate** — strongest signal for crossover into recommendations
- **Watch-through to next video** — channel stickiness; uses end screens
  + sequential topic chains
- **Posting cadence** — at least daily, ideally 2-4x/day at peak
  audience times

## Constraints

- **Don't violate platform TOS.** No deceptive thumbnails, no fake
  engagement, no engagement-bait that breaks YouTube Shorts policy. All
  optimization must be within ToS.
- **Audience respect.** Hooks should be honest — clickbait that doesn't
  pay off destroys retention and burns channel reputation.
- **Cost: zero variable cost** — local LLM, local TTS, local rendering.
  Strategy must respect that constraint.
- **Operator: solo / small team.** Strategies must be executable without
  hiring editors or buying tools.

## What "improvement" means in this context

Each daily plan should:
1. Reference yesterday's plan and call out what was right / wrong / missing.
2. Propose a concrete experiment for today (single hypothesis,
   measurable outcome).
3. Update the rolling "what's working" / "what's not" list.
4. Stay focused on the *production pipeline* — what topics, hooks,
   captions, voices, pacing, cuts, end-screens, music to actually ship.
   Not generic creator advice.
