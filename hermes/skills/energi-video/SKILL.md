---
name: energi-video
description: Produce the Energi Elite video from an approved script pack, running the locked pipeline scripts (voiceover, keyframes, preview, clips, final assembly, cover) with cost and approval gates. Use after the operator approves a script (status step script_approved).
---

# Energi video production

Run every command from the project folder (`energi-content`). Never call Higgsfield, FFmpeg or TTS directly; only use the scripts in `scripts/` (see `scripts/README.md`). If a script fails, show the error and stop. Don't improvise a workaround.

## Preconditions
- `jobs/<job>/status.md` shows `script_approved` and `lint.md` is PASS. Otherwise stop.
- The script spells out units for speech (e.g. "seven kilowatt", not "7 kW").

## Steps
1. **Voiceover (free):** `python scripts/voiceover.py <job>`. If it warns that scene words don't match spoken words, fix `vo_text` in `scenes.json` to match `script.md` exactly and rerun.
2. **Keyframes (paid):** run `python scripts/keyframes.py <job> --dry-run`, show the plan and scene count, and **ask the operator to confirm spend**. Then run with `--yes`.
3. **Keyframe review:** open `keyframes/contact.jpg` and each keyframe with your vision tool. Reject any frame with: a car badge or logo (especially Tesla), readable text or numbers, a wall charger, or an off-style look (see `brand/style_bible.md`). Regenerate rejects with `--scenes <ids> --force --yes` (max 2 retries per scene, then ask the operator).
4. **Preview (free):** `python scripts/assemble.py <job>`. Tell the operator `renders/final_1x1.mp4` is a keyframe-only preview and **ask for approval before clips**.
5. **Clips (paid, main cost):** `python scripts/animate.py <job> --dry-run`, report total clip seconds, **ask to confirm spend**, then `--yes`.
6. **Final (free):** `python scripts/assemble.py <job> --hook "<chosen hook, short, upper-case friendly>" --preset B --vertical`. Run the hook text through energi-claim-lint first.
7. **Logo/quality check:** inspect `qa/contact.jpg` (one frame every 2s). Any badge, text artefact or charger means regenerate that scene's keyframe and clip, then reassemble.
8. **Cover:** `python scripts/thumbnail.py <job> --hook "<hook>"`, then check `thumbnail_1x1.jpg` the same way.
9. **Gate 2:** update `status.md` to `step: video_ready`, list the output files and total paid seconds, and ask the operator to approve, request changes, or reject. Never publish without explicit approval.
