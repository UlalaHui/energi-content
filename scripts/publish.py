"""Publish an approved reel via Upload-Post (Instagram / Facebook). Each real upload uses 1 of the plan's monthly uploads.

Usage:
  python scripts/publish.py <job> --dry-run                      # shows exactly what would be posted, no API call
  python scripts/publish.py <job> --yes                          # posts to the platforms in .env (UPLOAD_POST_PLATFORMS)
  python scripts/publish.py <job> --yes --platforms instagram
Needs in .env: UPLOAD_POST_KEY, UPLOAD_POST_USER, optional FACEBOOK_PAGE_ID, UPLOAD_POST_PLATFORMS (default: instagram)
Refuses unless status.md contains 'step: approved' and final/ has reel + caption. Never re-posts a job that has published.json.
"""
import argparse
import json
import os
import re
import time

import requests

import tg

from common import ROOT, job_dir, load_env, log

API = "https://api.upload-post.com/api"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job", nargs="?", default="latest", help="job folder name, or latest (newest reel waiting for approval)")
    ap.add_argument("--platforms", help="comma list, e.g. instagram,facebook")
    ap.add_argument("--format", choices=["1x1", "9x16"], default="1x1", help="brand rule: 1:1 for FB/IG")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true", help="required to actually post")
    ap.add_argument("--wait", action="store_true", help="poll status up to 2 times (60s apart) for the post link (extra API calls)")
    ap.add_argument("--approve", action="store_true", help="record the operator's approval (job must be video_ready)")
    ap.add_argument("--notify", action="store_true", help="send the result to Telegram")
    ap.add_argument("--force", action="store_true", help="allow re-posting a job that was already published")
    args = ap.parse_args()
    load_env()
    if args.job == "latest":
        cands = sorted((p for p in (ROOT / "jobs").iterdir() if p.is_dir() and (p / "status.md").exists()
                        and "step: video_ready" in (p / "status.md").read_text(encoding="utf-8")
                        and not (p / "published.json").exists()), key=lambda p: p.stat().st_mtime, reverse=True)
        if not cands:
            raise SystemExit("No reel is waiting for approval.")
        args.job = cands[0].name
    job = job_dir(args.job)
    final = job / "final"

    status = (job / "status.md").read_text(encoding="utf-8") if (job / "status.md").exists() else ""
    if args.approve and "step: video_ready" in status and not re.search(r"step:\s*approved", status):
        with open(job / "status.md", "a", encoding="utf-8") as f:
            f.write("step: approved\n")
        status += "step: approved\n"
    if not re.search(r"step:\s*approved", status, re.I):
        raise SystemExit("REFUSED: status.md has no 'step: approved'. The operator must approve the reel first.")
    if (job / "published.json").exists() and not args.force:
        raise SystemExit("REFUSED: already published (published.json exists). Use --force only if the operator asks to post again.")

    video = final / f"reel_{args.format}.mp4"
    cap_file = final / "caption.txt"
    for f in (video, cap_file):
        if not f.exists():
            raise SystemExit(f"Missing {f}. Run package.py first.")
    caption = cap_file.read_text(encoding="utf-8").strip()
    if re.search(r"withstand(s)? lightning|lightning[- ]proof|tahan petir|kalis petir|tesla logo", caption, re.I):
        raise SystemExit("REFUSED: caption fails the brand rules (lightning/Tesla). Fix caption.md and re-package.")

    platforms = [p.strip() for p in (args.platforms or os.environ.get("UPLOAD_POST_PLATFORMS", "instagram")).split(",") if p.strip()]
    user = os.environ.get("UPLOAD_POST_USER", "")
    page = os.environ.get("FACEBOOK_PAGE_ID", "")
    if "facebook" in platforms and not page:
        raise SystemExit("facebook needs FACEBOOK_PAGE_ID in .env")

    data = [("user", user), ("title", caption), ("async_upload", "true")]
    data += [("platform[]", p) for p in platforms]
    if "instagram" in platforms:
        data += [("media_type", "REELS"), ("share_to_feed", "true")]
    if "facebook" in platforms:
        data += [("facebook_page_id", page), ("facebook_media_type", "REELS")]

    size_mb = video.stat().st_size / 1e6
    print(f"Job: {job.name}\nVideo: {video.name} ({size_mb:.1f} MB)\nPlatforms: {', '.join(platforms)}\nProfile: {user or '(UPLOAD_POST_USER missing)'}")
    print("Caption:\n" + caption + "\n")
    if args.dry_run or not args.yes:
        print("DRY RUN - nothing posted. Uses 1 upload of the monthly quota when run with --yes.")
        return
    key = os.environ.get("UPLOAD_POST_KEY")
    if not key or not user:
        raise SystemExit("Set UPLOAD_POST_KEY and UPLOAD_POST_USER in .env")
    headers = {"Authorization": f"Apikey {key}"}

    with open(video, "rb") as fh:
        r = requests.post(f"{API}/upload", headers=headers, data=data,
                          files={"video": (video.name, fh, "video/mp4")}, timeout=600)
    try:
        res = r.json()
    except ValueError:
        res = {"raw": r.text[:500]}
    print(f"HTTP {r.status_code}: {json.dumps(res)[:800]}")
    if r.status_code >= 400 or not res.get("success", r.ok):
        log(job, "publish", f"FAILED HTTP {r.status_code}")
        if args.notify:
            tg.send(f"❌ Publish failed (HTTP {r.status_code}): {json.dumps(res)[:300]}. Nothing was posted.")
        raise SystemExit("Upload failed (see above). Nothing was published.")

    rid = res.get("request_id")
    final_res = res
    if rid and args.wait:   # optional: a few status checks (may count toward the plan's API calls)
        for _ in range(2):
            time.sleep(60)
            s = requests.get(f"{API}/uploadposts/status", headers=headers, params={"request_id": rid}, timeout=60)
            try:
                final_res = s.json()
            except ValueError:
                continue
            print("status:", json.dumps(final_res)[:300])
            if re.search(r"https://", json.dumps(final_res)):
                break
    urls = re.findall(r"https://[^\"\s]+", json.dumps(final_res))
    out = {"request_id": rid, "platforms": platforms, "format": args.format, "result": final_res,
           "urls": urls, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    (job / "published.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    with open(job / "status.md", "a", encoding="utf-8") as f:
        f.write("\nstep: published\n")
    log(job, "publish", f"{', '.join(platforms)} request {rid} urls {urls[:3]}")
    print("\nPUBLISHED. Links:" if urls else "\nSubmitted (processing in background, ~1-3 min). Check Instagram / the Upload-Post dashboard History.")
    for u in urls:
        print(" ", u)
    prof = os.environ.get("PUBLISH_PROFILE_URLS", "")
    if prof:
        print("Profile:", prof)
    if args.notify:
        post_links = [u for u in urls if "instagram.com" in u or "facebook.com" in u]
        tg.send("✅ Published to " + ", ".join(platforms) + "\n" + ("\n".join(post_links) or "(post link pending - processing)")
                + (f"\nProfile: {prof}" if prof else ""))


if __name__ == "__main__":
    main()
