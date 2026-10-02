"""Generate one keyframe image per generated scene with Higgsfield (paid).

Usage:
  python scripts/keyframes.py <job> --dry-run          # show plan, no spend
  python scripts/keyframes.py <job> --yes              # generate missing keyframes
  python scripts/keyframes.py <job> --yes --scenes 3,7 --force   # regenerate specific scenes
Output: <job>/keyframes/scene_XX.png and keyframes/contact.jpg (review sheet)
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from common import (contact_sheet, download, hf_submit, hf_wait, job_dir, load_config,
                    load_env, load_scenes, log, media_url, scene_name)


CAR_WORDS = ("car", "suv", "vehicle", "ev ")


def prompt_for(scene, cfg):
    """Style prefix + scene + guards. The car guard is added only when the scene has a car,
    because mentioning cars/plates in every prompt makes the model draw cars everywhere."""
    visual = scene["visual"].strip()
    parts = [cfg.get("image_style_prefix", ""), visual, cfg["image_prompt_guard"]]
    if any(w in f" {visual.lower()} " for w in CAR_WORDS):
        parts.append(cfg.get("image_car_guard", ""))
    return " ".join(p.strip() for p in parts if p and p.strip())


_REF_URLS = None


def ref_urls(cfg):
    """Upload the style reference frames once per run (only for models that accept reference images)."""
    global _REF_URLS
    if _REF_URLS is None:
        from common import ROOT, hf_upload
        files = [ROOT / p for p in cfg.get("image_refs", [])]
        _REF_URLS = [hf_upload(f) for f in files if f.exists()]
    return _REF_URLS


def one(scene, cfg, out):
    body = {"prompt": prompt_for(scene, cfg), **cfg["image_params"]}
    param = cfg.get("image_ref_param")
    if param:
        urls = ref_urls(cfg)
        body[param] = urls[0] if param.endswith("_url") else urls
    sub = hf_submit(cfg["image_endpoint"], body)
    res = hf_wait(sub)
    download(media_url(res, "image"), out)
    return scene["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--scenes", help="comma-separated scene ids")
    ap.add_argument("--force", action="store_true", help="regenerate even if the file exists")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true", help="confirm paid generation")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    load_env()
    job, cfg = job_dir(args.job), load_config()
    wanted = {int(x) for x in args.scenes.split(",")} if args.scenes else None
    kdir = job / "keyframes"
    kdir.mkdir(exist_ok=True)

    todo = []
    for s in load_scenes(job):
        if s.get("type", "generated") != "generated":
            continue
        if wanted and int(s["id"]) not in wanted:
            continue
        out = kdir / f"{scene_name(s)}.png"
        if out.exists() and not args.force:
            continue
        todo.append((s, out))

    print(f"Keyframes to generate: {len(todo)} via {cfg['image_endpoint']} {cfg['image_params']}")
    for s, _ in todo:
        print(f"  #{s['id']}: {s['visual'][:90]}...")
    if args.dry_run or not todo:
        return
    if not args.yes:
        raise SystemExit("Paid step. Re-run with --yes after the script is approved.")

    done, failed = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(one, s, cfg, out): s for s, out in todo}
        for f in as_completed(futs):
            s = futs[f]
            try:
                done.append(f.result())
                print(f"  ok #{s['id']}")
            except Exception as e:  # keep going; report failures at the end
                failed.append((s["id"], str(e)))
                print(f"  FAILED #{s['id']}: {e}")

    sheet = contact_sheet(sorted(kdir.glob("scene_*.png")), kdir / "contact.jpg")
    log(job, "keyframes", f"generated {len(done)}, failed {len(failed)}"
        + (f" ({', '.join(str(i) for i, _ in failed)})" if failed else "")
        + (f"; review sheet {sheet.name}" if sheet else ""))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
