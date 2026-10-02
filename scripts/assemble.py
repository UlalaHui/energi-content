"""Assemble the final 1:1 video: scenes + voiceover + word captions + logo + end card (free, local FFmpeg).

Per scene it uses, in order: clips/scene_XX.mp4 > keyframes/scene_XX.png (slow zoom) > text card.
So you can preview the whole video from keyframes alone, before paying for clips.

Usage:
  python scripts/assemble.py <job>
  python scripts/assemble.py <job> --hook "NEVER RESET THIS BREAKER" --preset B --vertical
Output: <job>/renders/final_1x1.mp4 (+ final_9x16.mp4), <job>/qa/contact.jpg
"""
import argparse
import json
import math
import re

from common import (ROOT, contact_sheet, job_dir, load_config, load_scenes, log, need,
                    probe_duration, probe_size, run, scene_name)


# ---------- captions ----------

def ts(sec):
    sec = max(sec, 0)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def chunk_words(words, max_words=3, gap=0.35):
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        end_punct = bool(re.search(r"[.,!?;:]$", w["text"]))
        big_gap = nxt is not None and nxt["start"] - w["end"] > gap
        if len(cur) >= max_words or end_punct or big_gap or nxt is None:
            chunks.append(cur)
            cur = []
    return chunks


def clean(t):
    return t.replace("{", "(").replace("}", ")").replace("\\", "/")


def build_ass(words, cfg, preset, hook, cut_at, size, labels=()):
    font = cfg["caption_font"]
    orange = f"&H00{cfg['brand_orange_bgr']}"
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {size}
PlayResY: {size}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},64,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,5,2,2,60,60,230,1
Style: Hook,{font},66,&H00FFFFFF,&H00FFFFFF,{orange},&H00000000,-1,0,0,0,100,100,0,0,3,14,0,8,80,80,150,1
Style: Label,{font},50,&H00FFFFFF,&H00FFFFFF,&H00382A1E,&H00000000,-1,0,0,0,100,100,0,0,3,12,0,8,80,80,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    chunks = [c for c in chunk_words(words) if c[0]["start"] < cut_at]
    for k, c in enumerate(chunks):
        start = c[0]["start"]
        nxt = chunks[k + 1][0]["start"] if k + 1 < len(chunks) else None
        end = nxt if nxt is not None and nxt - c[-1]["end"] < 0.5 else c[-1]["end"] + 0.2
        end = min(end, cut_at)
        texts = [clean(w["text"]) for w in c]
        if preset == "B":
            texts = [t.upper() for t in texts]
            key = max(range(len(texts)), key=lambda i: len(re.sub(r"\W", "", texts[i])))
            texts[key] = "{\\c" + orange + "&}" + texts[key] + "{\\c&H00FFFFFF&}"
        lines.append(f"Dialogue: 0,{ts(start)},{ts(end)},Cap,,0,0,0,,{' '.join(texts)}")
    hook_end = 2.6 if hook else 0.0
    if hook:
        lines.append(f"Dialogue: 1,{ts(0)},{ts(hook_end)},Hook,,0,0,0,,{clean(hook.upper())}")
    for start, end, text in labels:   # component tags, e.g. "MCB", shown while that scene is on screen
        start = max(start + 0.15, hook_end)
        if end - start > 0.6:
            lines.append(f"Dialogue: 1,{ts(start)},{ts(end - 0.1)},Label,,0,0,0,,{clean(text)}")
    return head + "\n".join(lines) + "\n"


# ---------- scene segments ----------

def render_segment(scene, dur, job, cfg, out):
    size, fps = cfg["output_size"], cfg["fps"]
    name = scene_name(scene)
    clip = job / "clips" / f"{name}.mp4"
    key = job / "keyframes" / f"{name}.png"
    photo = scene.get("photo")
    photo = (ROOT / "assets" / "e1-photos" / photo) if photo else None
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(fps), "-an"]
    fit = f"scale={size}:{size}:force_original_aspect_ratio=increase,crop={size}:{size}"

    if scene.get("type") == "text_card":
        logo = ROOT / "assets" / "logo.png"
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=black:s={size}x{size}:r={fps}:d={dur}",
             "-i", str(logo), "-filter_complex",
             f"[1]scale={int(size * 0.6)}:-1[l];[0][l]overlay=(W-w)/2:(H-h)/2,format=yuv420p",
             "-t", f"{dur:.3f}", *enc, str(out)])
        return "text_card"
    if clip.exists():
        slow = max(1.0, dur / probe_duration(clip))
        run(["ffmpeg", "-y", "-v", "error", "-i", str(clip), "-vf", f"setpts=PTS*{slow:.4f},{fit},fps={fps}",
             "-t", f"{dur:.3f}", *enc, str(out)])
        return "clip" + (f" (slowed x{slow:.2f})" if slow > 1.01 else "")
    src = key if key.exists() else (photo if photo and photo.exists() else None)
    if src is None:
        # Never crash the preview: render a plain branded placeholder and report it.
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
             "-i", f"color=c=0x8A9BB0:s={size}x{size}:r={fps}:d={dur}", "-t", f"{dur:.3f}", *enc, str(out)])
        return "MISSING IMAGE - placeholder"
    frames = math.ceil(dur * fps)
    zoom = (f"scale={size * 2}:{size * 2}:force_original_aspect_ratio=increase,crop={size * 2}:{size * 2},"
            f"zoompan=z='min(zoom+0.0007,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={size}x{size}:fps={fps}")
    run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(src), "-vf", zoom, "-t", f"{dur:.3f}", *enc, str(out)])
    return "keyframe zoom" if src == key else "real photo zoom"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--hook", help="optional on-screen text hook for the first 2.6s")
    ap.add_argument("--preset", choices=["A", "B"], help="caption style (default from config)")
    ap.add_argument("--vertical", action="store_true", help="also export a 9:16 version")
    args = ap.parse_args()
    need("ffmpeg")
    job, cfg = job_dir(args.job), load_config()
    preset = args.preset or cfg["caption_preset"]
    size = cfg["output_size"]

    for f in ("timeline.json", "words.json", "vo.mp3"):
        if not (job / f).exists():
            raise SystemExit(f"Missing {f}. Run scripts/voiceover.py first.")
    timeline = {t["id"]: t for t in json.loads((job / "timeline.json").read_text(encoding="utf-8"))}
    words = json.loads((job / "words.json").read_text(encoding="utf-8"))
    scenes = load_scenes(job)

    seg_dir = job / "segments"
    seg_dir.mkdir(exist_ok=True)
    sources, listing = [], []
    for s in scenes:
        dur = timeline[s["id"]]["duration"]
        out = seg_dir / f"{scene_name(s)}.mp4"
        sources.append(f"#{s['id']}: {render_segment(s, dur, job, cfg, out)} {dur:.1f}s")
        listing.append(f"file '{out.name}'")
    (seg_dir / "list.txt").write_text("\n".join(listing) + "\n", encoding="utf-8")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "body.mp4"],
        cwd=seg_dir)

    total = sum(t["duration"] for t in timeline.values())
    end_card = next((timeline[s["id"]]["start"] for s in scenes if s.get("type") == "text_card"), total)
    labels = [(timeline[s["id"]]["start"], timeline[s["id"]]["end"], s["label"])
              for s in scenes if s.get("label") and s.get("type") != "text_card"]
    (job / "captions.ass").write_text(build_ass(words, cfg, preset, args.hook, end_card, size, labels),
                                      encoding="utf-8")

    renders = job / "renders"
    renders.mkdir(exist_ok=True)
    logo = ROOT / "assets" / "logo.png"
    fc = (f"[2:v]scale={cfg['logo_width']}:-1,format=rgba,colorchannelmixer=aa={cfg['logo_opacity']}[lg];"
          f"[0:v][lg]overlay=(W-w)/2:40:enable='lt(t,{end_card:.3f})'[v0];[v0]subtitles=captions.ass[v]")
    run(["ffmpeg", "-y", "-v", "error", "-i", "segments/body.mp4", "-i", "vo.mp3", "-i", str(logo),
         "-filter_complex", fc, "-map", "[v]", "-map", "1:a", "-af", "apad", "-t", f"{total:.3f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "renders/final_1x1.mp4"], cwd=job)
    final = renders / "final_1x1.mp4"
    w, h = probe_size(final)
    if (w, h) != (size, size):
        raise SystemExit(f"Output is {w}x{h}, expected {size}x{size} (1:1 brand rule).")

    # Telegram's Bot API rejects files over 20 MB, so always keep a small preview copy.
    tg = renders / "final_tg.mp4"
    if final.stat().st_size <= 19 * 1024 * 1024:
        import shutil
        shutil.copy2(final, tg)
    else:
        kbps = max(600, int(18 * 8 * 1024 / total) - 128)
        run(["ffmpeg", "-y", "-v", "error", "-i", str(final), "-c:v", "libx264", "-preset", "medium",
             "-b:v", f"{kbps}k", "-maxrate", f"{kbps}k", "-bufsize", f"{kbps * 2}k", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(tg)])

    if args.vertical:
        run(["ffmpeg", "-y", "-v", "error", "-i", str(final), "-filter_complex",
             "[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=24[bg];"
             "[bg][b]overlay=0:(H-h)/2[v]", "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-crf", "20",
             "-pix_fmt", "yuv420p", "-c:a", "copy", str(renders / "final_9x16.mp4")])

    qa = job / "qa"
    qa.mkdir(exist_ok=True)
    for old in qa.glob("frame_*.jpg"):
        old.unlink()
    run(["ffmpeg", "-y", "-v", "error", "-i", str(final), "-vf", "fps=1/2,scale=480:-1", str(qa / "frame_%03d.jpg")])
    contact_sheet(sorted(qa.glob("frame_*.jpg")), qa / "contact.jpg", cols=6, cell=240)

    (job / "assembly.md").write_text("# Assembly sources\n" + "\n".join(f"- {x}" for x in sources) + "\n",
                                     encoding="utf-8")
    missing = [s for s in sources if "MISSING" in s]
    if missing:
        print("WARNING: placeholder used for: " + "; ".join(missing))
    log(job, "assemble", (f"WARNING {len(missing)} placeholder scene(s); " if missing else "")
        + f"renders/final_1x1.mp4 {w}x{h} {total:.1f}s; captions preset {preset}"
        + ("; hook overlay" if args.hook else "") + ("; 9:16 exported" if args.vertical else "")
        + "; QA sheet qa/contact.jpg")


if __name__ == "__main__":
    main()
