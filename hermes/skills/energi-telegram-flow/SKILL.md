---
name: energi-telegram-flow
description: Run the full Energi Elite reel workflow in a chat (Telegram) - from an idea or 3 suggested topics, through script, hook choice, scenes, preview, cover and caption choice, to a finished reel package. Use whenever the operator messages about Energi content, sends an idea, asks for topic suggestions, or says publish <job>. Publishes only on explicit request.
---

# Energi reel workflow (chat)

## Daily run replies (CHECK THIS FIRST)
The daily reel is produced by a script (`daily_run.py`) that already sent the topic, script and scene contact sheet to this chat. When the operator replies to it, do ONLY this, with the terminal tool, then answer in one short line. The scripts send all files and messages themselves; do not send them again, do not start a new topic, do not write scripts yourself.
| Operator says | Run exactly |
|---|---|
| `go`, "go ahead", "make the video", "ok proceed" | `"C:\Program Files\Python311\python.exe" C:\Users\User\energi-content\scripts\finish.py` |
| `approve`, "approved", "publish", "post it" (after the reel was sent) | `"C:\Program Files\Python311\python.exe" C:\Users\User\energi-content\scripts\publish.py latest --approve --yes --wait --notify` |
| `redo 3,7` | `"C:\Program Files\Python311\python.exe" C:\Users\User\energi-content\scripts\keyframes.py <job> --scenes 3,7 --force --yes` then send `MEDIA:<job>\keyframes\contact.jpg` and ask "go / redo / skip?" (<job> = newest folder in jobs\ whose status.md has `step: awaiting_review`) |
| `skip` | append `step: skipped` to that job's status.md |
| a change request after the reel was sent ("change the caption to...") | edit `caption.md` or the hook in `status.md` (`on_screen_hook:`) of that job, then run finish.py again |
If a command fails, reply with its last error line only.

## Fixed paths (the chat session may not start in the project folder)
- Project: `C:\Users\User\energi-content` (call it PROJECT)
- Always read and write files with full paths under PROJECT.
- Run every pipeline script with the **terminal/shell tool** (never `execute_code`, never your own Python), using this exact interpreter, which has the required packages installed:
  `"C:\Program Files\Python311\python.exe" C:\Users\User\energi-content\scripts\<script>.py <job> ...`
  (scripts work from any folder; `<job>` is the folder name under `PROJECT\jobs`)
- Never install, upgrade or uninstall packages. If a script reports a missing module, stop and tell the operator the exact error.
- Before starting, read `PROJECT\AGENTS.md` and everything in `PROJECT\brand\`.
- Send files to the chat with a line `MEDIA:<full path>` (images and mp4 only; files over 20 MB fail, so send `renders\final_tg.mp4`, never `final_1x1.mp4`).

## Chat rules
- One step per message. End every message with exactly what the operator can reply (numbers or yes/no).
- Keep messages short: no file dumps, no code, no tool logs.
- Never spend money without an explicit "yes" to a cost question in this chat.
- Never publish or post anywhere unless the operator sends `publish <job>` and confirms (step 9).
- If a script fails, say which step failed in one line and offer: retry / skip / stop. Scripts are safe to re-run (they skip finished work), so on a timeout just re-run the same command.
- Keep `status.md` in the job folder updated at every step.

## Hard rules for files (breaking these corrupts the job)
- Follow the **Protected** and **What you MAY edit** sections in SOUL.md: only `script.md`, `hooks.md`, `caption.md`, `scenes.json`, `status.md` and `lint.md` in the job folder may be edited by you.
- Never delete, add, renumber or reorder scenes after `voiceover.py` has run. Scene ids are fixed.
- Never rename, move or delete files in `keyframes\`, `clips\`, `segments\` or `renders\`. Only the scripts write there.
- Never edit `vo_text` or `script.md` after the voiceover without re-running `voiceover.py` (free) straight after.
- If a scene image keeps failing after the script's own retries, do NOT work around it. Tell the operator in one line and offer exactly:
  `1` retry that scene later, `2` rewrite that scene's visual (same id) and regenerate it, `3` continue: the preview uses a plain placeholder for that scene.
- `assemble.py` never fails on a missing image (it uses a placeholder and prints WARNING). Pass that warning on to the operator.
- Explainer reels never use `real_photo` scenes. Product reels (about the E1, our installs, why choose us) must use `real_photo` with a file from `assets\e1-photos\photos.md` for every charger/install beat. Fix this **before** the voiceover. Photo scenes cost nothing: the keyframe quote only counts `generated` scenes.

## Steps

### 1. Topic
- The operator sends an idea, or asks for suggestions ("suggest", "/topics", "give me ideas").
- For suggestions: propose **3 topics** from the topic bank in `brand\brand_profile.md` that have no job folder yet. For each: the title, a one-line angle, and an example hook.
- Reply options: `1`, `2`, `3`, or their own idea.

### 2. Script pack
- Run the **energi-script-pack** skill, then **energi-claim-lint**. The job folder is `PROJECT\jobs\<YYYYMMDD>-<slug>`.
- Send: the script (as text), the 10 hooks (numbered), and the lint result (PASS/FAIL, one line).
- Ask: "Reply a hook number (1-10), or tell me what to change."

### 3. Lock the hook and script
- Make the chosen hook the script's **first sentence** and scene 1's `vo_text` (keep 160-190 words). Re-run the lint.
- Derive a short **on-screen hook** (max 5 words, e.g. "STOP BLAMING YOUR CHARGER") and save it in `status.md`.
- Set `step: script_approved`.

### 4. Voice and scene images (paid)
- Run `voiceover.py <job>` (free) **before** any paid step. If it fails, stop and report; do not continue to images. Fix any warning about scene words before continuing.
- Run `keyframes.py <job> --dry-run`, then ask: "Generate N scene images (about $0.07 each, ~$X total)? yes/no".
- On yes: `keyframes.py <job> --yes --workers 3`.
- Review **only `keyframes\contact.jpg`** with your vision tool (one image, all scenes numbered). Never send all the full-size scene PNGs to the vision tool at once (they are ~1.5 MB each and crash the model). Open at most 3 single keyframes, only for scenes you suspect. **If the vision tool errors or is unavailable, skip the check (do not retry, do not regenerate) and say "visual check skipped - please review the contact sheet"**; the operator's review is the real gate. Reject: recognisable real car brands, readable text, wall chargers, charging guns or cables into a car, off-style frames, cartoon people, symbols that contradict the line (e.g. a red/green X where the line is positive), or anything that doesn't clearly show the part the scene is about. Regenerate rejects with `--scenes <ids> --force --yes` (max 2 tries per scene, then report it).
- Send `MEDIA:` the contact sheet and say in one line how many scenes passed or were redone.

### 5. Preview
- Run `assemble.py <job> --hook "<on-screen hook>" --preset B`.
- Check `qa\contact.jpg` the same way as the keyframes.
- Send `MEDIA:PROJECT\jobs\<job>\renders\final_tg.mp4`.
- Ask: "1 = keep as is (stills with slow zoom), 2 = add motion to key scenes (I'll quote the cost), 3 = change scenes (say which)."
- For 2: pick the 3-4 scenes that carry the main idea (hook, the key diagram, the twist). Run `animate.py <job> --dry-run --scenes <ids>` (Seedance 2.5 text-to-video, ~$0.21 per second; the dry run prints the total), quote the total, ask yes/no, then run with `--yes --workers 1`, check the clips' frames like keyframes, and re-run assemble. Never animate all scenes unless the operator asks and accepts the quoted cost.

### 6. Cover
- Make 3 cover options with different short texts (the chosen on-screen hook plus two alternative hooks, max 5 words each, all lint-checked):
  `thumbnail.py <job> --hook "<text>" --out cover_1` (and `cover_2`, `cover_3`; use `--scene` to vary the background if useful).
- Send all three as `MEDIA:` (the `_1x1.jpg` files). Ask: "Reply 1, 2 or 3."

### 7. Caption and title
- Show `caption.md` plus 2 alternative captions (different opening lines; same CTA and hashtags; all lint-checked).
- Ask: "Reply A, B or C, or send edits." Save the chosen one to `caption.md`.

### 8. Final package
- Run `assemble.py <job> --hook "<on-screen hook>" --preset B --vertical`, then `package.py <job> --cover cover_<n>`.
- Send: `MEDIA:` `final\reel_preview_tg.mp4`, `MEDIA:` `final\cover_1x1.jpg`, and the caption text.
- Say where the full-quality files are (`PROJECT\jobs\<job>\final\`) and the spend for this reel.
- Set `step: video_ready` and ask: "Approve this reel? (approve / change something)".
- On "approve": append `step: approved` to `status.md` and reply: "Approved. Send `publish <job>` when you want it posted." **Do not publish on approval alone.**

### 9. Publish (only on request)
- Trigger: the operator sends `publish <job>` (optionally `publish <job> instagram,facebook`). The job must have `step: approved`.
- Run `publish.py <job> --dry-run` (add `--platforms ...` if given). Send the platforms, video file and caption, and ask: "Post this now? Uses 1 of the monthly uploads. yes/no".
- On yes: run `publish.py <job> --yes --wait` (same flags) **once**. Never re-run after an error without asking; never use `--force` unless the operator asks to post again.
- Reply with the post link(s) and the `Profile:` link it prints, or the one-line error. Then set nothing else; the job is done.

## Scheduled (unattended) run
Used when the prompt starts with `SCHEDULED RUN`. Nobody is there to answer, so make the choices yourself and stop at the review gate.
0. **Resume first:** if a job folder from today has `mode: scheduled` (or was clearly started by a scheduled run) and its `status.md` is not yet `awaiting_review`, `skipped` or later, **continue that job** from its last finished step instead of starting a new topic. Scripts skip finished work, so re-running them costs nothing extra. Never pay for the same images twice.
1. **Topic:** list 3 candidate topics from the topic bank that have no job folder, then pick the first one in `brand\brand_profile.md`'s topic bank that has no job folder in `PROJECT\jobs` (prefer explainer topics). If the prompt names a topic, use it.
2. **Script pack + lint** as in steps 2-3. If lint FAILs, fix the wording and re-lint (max 2 rounds); still FAIL -> stop and report why.
3. **Hook:** use the first `[Top Pick]` hook, lock it, derive the on-screen hook (max 5 words).
4. **Voiceover** (`voiceover.py`), then `keyframes.py <job> --dry-run`. Only if the quoted total is **within the budget in the prompt** (default $1.00) run `keyframes.py <job> --yes --workers 3`. Over budget -> stop and report the quote; spend nothing.
5. Vision-check **only `keyframes\contact.jpg`** (if the vision tool errors, skip this step and note it in the reply) (never all full-size PNGs at once); regenerate rejects once (`--scenes <ids> --force --yes`) only while total spend stays within budget.
6. **Stop here.** Append the line `step: awaiting_review` to `status.md` (append, don't rewrite the file). Do NOT assemble, animate, make covers or captions. Write to `status.md`: `mode: scheduled` (write this at the very start of the run too), `step: awaiting_review`, the hook, the on-screen hook, the spend.
7. Your final reply is delivered to Telegram. Keep it short:
   - the 3 suggested topics with the picked one marked, chosen hook, on-screen hook, scene count, spend so far
   - `MEDIA:<full path to keyframes\contact.jpg>`
   - "Reply `go <job>` to make the video, `redo <job> <scene ids>` to regenerate scenes, `hook <job> <n>` to change the hook, or `skip <job>`."

## Resuming a scheduled job (in chat)
When the operator sends `go <job>`, `redo <job> ...`, `hook <job> <n>` or `skip <job>`:
- If they say just `go`, "go ahead", "make the video" or similar **without a job name**, use the most recent job in `PROJECT\jobs` whose `status.md` has `mode: scheduled`, has `keyframes\contact.jpg`, and does not contain `step: skipped`, `step: approved` or `step: published`. Never start a new topic in reply to a go.
- Read `PROJECT\jobs\<job>\status.md`, `script.md`, `hooks.md` and `scenes.json` first.
- `go` -> continue from **step 5 (Preview)**, then steps 6-8 as normal.
- `redo` -> quote the cost with `--dry-run --scenes <ids> --force`, ask yes/no, regenerate, send the new contact sheet, ask again.
- `hook <n>` -> lock that hook, re-run `voiceover.py` (free), then continue as `go`.
- `skip` -> set `step: skipped`, reply in one line.
