# Pipeline scripts

Run from `energi-content\` (Windows CMD). `<job>` is the folder name under `jobs\`.

| Order | Command | Cost | Output |
|---|---|---|---|
| 1 | `python scripts\voiceover.py <job>` | free | `vo.mp3`, `words.json`, `timeline.json` |
| 2 | `python scripts\keyframes.py <job> --dry-run` then `--yes` | paid (images) | `keyframes\scene_XX.png`, `keyframes\contact.jpg` |
| 3 | `python scripts\assemble.py <job>` | free | **preview** from keyframes, before paying for clips |
| 4 | `python scripts\animate.py <job> --dry-run` then `--yes` | **paid (main cost)** | `clips\scene_XX.mp4` |
| 5 | `python scripts\assemble.py <job> --hook "..." --preset B --vertical` | free | `renders\final_1x1.mp4`, `renders\final_9x16.mp4`, `qa\contact.jpg` |
| 6 | `python scripts\thumbnail.py <job> --hook "..."` | free | `thumbnail_1x1.jpg`, `thumbnail_9x16.jpg` |

- Paid scripts never spend without `--yes`. Use `--scenes 3,7 --force` to redo specific scenes.
- `assemble.py` uses clip > keyframe > text card per scene, so it works at every stage.
- Settings (voice, models, logo, caption font and colours) live in `scripts\config.json`.
- Every script appends a line to the job's `status.md`.

## Setup (once)
```cmd
pip install -r scripts\requirements.txt
copy .env.example .env
notepad .env
```
