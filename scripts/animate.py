"""Turn approved keyframes into short clips with Higgsfield image-to-video (paid, the main cost).

Run voiceover.py first so clip lengths match the narration.
Usage:
  python scripts/animate.py <job> --dry-run
  python scripts/animate.py <job> --yes
  python scripts/animate.py <job> --yes --scenes 1 --force
Output: <job>/clips/scene_XX.mp4
"""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import math

from common import (download, hf_submit, hf_upload, hf_wait, job_dir, load_config, load_env,
                    load_scenes, log, media_url, scene_name)
from keyframes import prompt_for


def pick_duration(needed, cfg):
    """Seconds to request. Flexible models (e.g. Seedance: 4-30s) get exactly what the scene needs;
    fixed-length models get the shortest option that covers it (with a gentle slow-down at assembly)."""
    lo, hi = cfg.get("video_duration_range", [None, None])
    if lo:
        return int(min(max(math.ceil(needed), lo), hi))
    for d in sorted(cfg["video_durations"]):
        if d * cfg["video_max_slowdown"] >= needed:
            return d
    return max(cfg["video_durations"])


def one(scene, keyframe, seconds, cfg, out, mode):
    body = {"duration": seconds, **cfg.get("video_params", {})}
    if mode == "t2v":     # text-to-video straight from the diagram-first prompt (no keyframe needed)
        endpoint = cfg["video_t2v_endpoint"]
        body["prompt"] = f"{prompt_for(scene, cfg)} {cfg['video_motion']}"
    else:                 # image-to-video from an approved keyframe
        endpoint = cfg["video_endpoint"]
        body["prompt"] = f"{cfg['video_motion']} {scene['visual'].strip()}"
        body["image_url"] = hf_upload(keyframe)
    if cfg.get("video_negative_prompt") and cfg.get("video_supports_negative", True):
        body["negative_prompt"] = cfg["video_negative_prompt"]
    res = hf_wait(hf_submit(endpoint, body), timeout=1800, every=10)
    download(media_url(res, "video"), out)
    return scene["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--scenes")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--mode", choices=["i2v", "t2v"], help="i2v = animate keyframes; t2v = text-to-video (default from config)")
    args = ap.parse_args()

    load_env()
    job, cfg = job_dir(args.job), load_config()
    mode = args.mode or cfg.get("video_mode", "i2v")
    tl_path = job / "timeline.json"
    if not tl_path.exists():
        raise SystemExit("Run scripts/voiceover.py first (needs timeline.json for clip lengths).")
    timeline = {t["id"]: t for t in json.loads(tl_path.read_text(encoding="utf-8"))}
    wanted = {int(x) for x in args.scenes.split(",")} if args.scenes else None
    cdir = job / "clips"
    cdir.mkdir(exist_ok=True)

    todo, missing = [], []
    for s in load_scenes(job):
        if s.get("type", "generated") != "generated" or (wanted and int(s["id"]) not in wanted):
            continue
        kf = job / "keyframes" / f"{scene_name(s)}.png"
        out = cdir / f"{scene_name(s)}.mp4"
        if mode == "i2v" and not kf.exists():
            missing.append(s["id"])
            continue
        if out.exists() and not args.force:
            continue
        need = timeline.get(s["id"], {}).get("duration", s.get("duration_s", 4))
        todo.append((s, kf, pick_duration(need, cfg), out, need))

    if missing:
        print(f"No keyframe yet for scenes {missing}; run keyframes.py first.")
    total = sum(t[2] for t in todo)
    ep = cfg["video_t2v_endpoint"] if mode == "t2v" else cfg["video_endpoint"]
    price = cfg.get("video_price_per_s")
    est = f" (about ${total * price:.2f})" if price else ""
    print(f"Clips to generate: {len(todo)} via {ep} [{mode}], {total}s of video in total{est}")
    for s, _, d, _, need in todo:
        print(f"  #{s['id']}: {d}s clip for a {need:.1f}s scene")
    if args.dry_run or not todo:
        return
    if not args.yes:
        raise SystemExit("Paid step. Re-run with --yes after the keyframes are approved.")

    done, failed = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(one, s, kf, d, cfg, out, mode): s for s, kf, d, out, _ in todo}
        for f in as_completed(futs):
            s = futs[f]
            try:
                done.append(f.result())
                print(f"  ok #{s['id']}")
            except Exception as e:
                failed.append((s["id"], str(e)))
                print(f"  FAILED #{s['id']}: {e}")

    log(job, "animate", f"[{mode}] clips {len(done)} ok, {len(failed)} failed, {total}s billed video"
        + (f" (failed: {', '.join(str(i) for i, _ in failed)})" if failed else ""))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
