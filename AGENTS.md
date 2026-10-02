# Energi Content Machine: Project Instructions

Run Hermes from this folder so this file loads.

## Read first
| File | Purpose |
|---|---|
| `brand/brand_profile.md` | Company facts, products, audience, voice, content pillars, topic bank |
| `brand/brand_rules.md` | Hard rules and banned claims (EN / BM / CN) |
| `brand/recipe.md` | Video structure: hook, beats, length, CTA, captions |
| `brand/style_bible.md` | Visual look and prompt suffix for every generated scene |
| `brand/ref-frames/` | 6 frames from their reels; attach as style references |
| `reels/transcripts.md` | Transcripts of the 3 source reels |

## Principle: agent decides what, scripts decide how
You choose topics, write scripts, plan scenes and judge quality. Rendering, captions, checks and publishing run through scripts in `scripts/`; never improvise those steps by hand. If a script is missing, say so instead of working around it.

## Pipeline
1. **Topic**: from the operator, or 3 unused topics from the topic bank (check `jobs/` for used ones)
2. **Script pack** (skill `energi-script-pack`): `script.md`, `hooks.md` (10), `caption.md`, `scenes.json`
3. **Claim lint** (skill `energi-claim-lint`): every text output, before any spend
4. **Gate 1, script approval**: stop and ask the operator to approve, edit or reject
5. **Scenes**: Higgsfield keyframe, then image-to-video for `generated` scenes; real photos from `assets/e1-photos/` for `real_photo` scenes
6. **Assembly**: voiceover, word captions, logo, end card, FFmpeg 1080x1080 (+ optional 9:16)
7. **Logo check**: vision check on sampled frames and the thumbnail; any car badge means regenerate that scene
8. **Thumbnail**: best hook frame + hook text overlay (gpt-image-2 only as fallback)
9. **Gate 2, video approval**: stop and ask the operator
10. **Publish**: upload-post to the **test** IG account only, after approval
11. **Analytics**: log post metrics to `jobs/<job>/metrics.md`

## Job folder
`jobs/<YYYYMMDD>-<slug>/`
- `status.md`: current step, decisions, approvals (update at every step)
- `script.md`, `hooks.md`, `caption.md`, `scenes.json`
- `lint.md`: claim-lint result
- `renders/`, `thumbnail.png`

## scenes.json schema
```json
[{"id": 1, "vo_text": "...", "visual": "...", "type": "generated | real_photo | text_card", "duration_s": 3.5}]
```

## Morning routine
When triggered by the daily schedule: propose 3 unused topics, each with a full script pack and lint result, then ask which to approve.

## Folders
`assets/e1-photos/` real install photos · `scripts/` pipeline scripts · `renders/` · `thumbnails/` · `jobs/`
