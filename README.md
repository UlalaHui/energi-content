# Energi Content Machine

Turns **nothing** (or an idea) into a finished, brand-safe Energi Elite explainer reel, with a human approving in Telegram before money is spent on video and before anything is published.

Built for the Energi Elite AI internship challenge, Door A ("The Content Machine").

## The flow

```
cron (daily, Hermes, no agent)
  └─ daily_run.py
       1. picks a topic from the brand topic bank        -> Telegram
       2. writes script + scenes + hooks + caption (LLM)
       3. lint: word count, banned claims, banned visuals (code)
                + fact/brand check (LLM), up to 6 retries -> Telegram (script)
          (fails here = $0 spent)
       4. voiceover (Edge TTS, free)
       5. scene images (Higgsfield Soul, ~$0.07 each)    -> Telegram (contact sheet)
  ── HUMAN GATE 1: reply "go" ─────────────────────────────
  └─ finish.py: assemble 1:1 + 9:16, captions, logo, end card, cover, package
                                                          -> Telegram (reel, cover, caption)
  ── HUMAN GATE 2: reply "approve" ────────────────────────
  └─ publish.py: Upload-Post -> Instagram (1:1)           -> Telegram (post link)
```

The chat side runs on [Hermes Agent](https://github.com/NousResearch/hermes-agent) (Telegram gateway + cron). The agent only maps replies (`go`, `approve`, `redo 3,7`, `skip`) to fixed commands; all generation steps are deterministic scripts.

## Brand rules enforced
| Rule | How |
|---|---|
| Square 1:1 for FB/IG | `config.json` + assembly checks 1080x1080 (9:16 also exported) |
| No Tesla logos | banned in text and visuals; car prompts force blank, unbadged fascia |
| Real E1 photos, never AI renders | explainers keep chargers out of frame (lint); product reels use `assets/e1-photos/` only |
| Never "withstand lightning" | regex lint in EN / BM / CN + LLM claim check |
| Also | no RM prices, no DIY electrical advice, no speed overclaims, no text/people in generated visuals |

## Folders
| Path | What |
|---|---|
| `scripts/` | pipeline: `daily_run.py`, `finish.py`, `publish.py`, `voiceover.py`, `keyframes.py`, `animate.py` (optional Seedance motion), `assemble.py`, `thumbnail.py`, `package.py`, `tg.py`, `config.json` |
| `brand/` | brand profile, rules, recipe (from 3 existing reels), style bible, reference frames |
| `assets/` | logo, real E1 install photos |
| `hermes/` | Hermes skills, SOUL.md (agent guardrails), cron launcher |
| `prompts/` | copies of the script-pack / claim-lint instructions used by `daily_run.py` |

## Setup (Windows)
1. Python 3.11 + `pip install -r scripts/requirements.txt`, FFmpeg on PATH.
2. Copy `.env.example` to `.env`: Higgsfield key, Upload-Post key/profile, Telegram chat id.
3. Ollama running with `gemma4:31b-cloud` (or set `LLM_MODEL`).
4. Copy `hermes/skills/*` and `hermes/SOUL.md` to `%LOCALAPPDATA%\hermes\`, `hermes/scripts/energi_daily.py` to `%LOCALAPPDATA%\hermes\scripts\`.
5. `hermes gateway run`, then schedule:
   `hermes cron create "0 9 * * *" --no-agent --script energi_daily.py --name energi-daily --deliver telegram`
6. Rehearsal without spending: `python scripts/daily_run.py --dry-run`

## Cost per reel
About $0.80 (11-12 scene images). Optional motion on 3-4 key scenes with Seedance 2.5: +$2-4. LLM: free tier. Voice: free. Publishing: Upload-Post free tier (10 posts/month) or $16/month.

## Known limits
See the one-pager. Short version: stills + slow zoom rather than full motion (cost), a free LLM that needs strict code checks, single operator, no performance feedback loop yet.
