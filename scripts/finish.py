"""After the operator replies `go`: render the reel, make the cover, package with the caption, send all to Telegram.
Usage: python scripts/finish.py [<job>]   (default: latest scheduled job awaiting review)"""
import os
import re
import subprocess
import sys

from common import ROOT, log
import tg


def latest_job():
    jobs = sorted((p for p in (ROOT / "jobs").iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True)
    for j in jobs:
        st = (j / "status.md").read_text(encoding="utf-8") if (j / "status.md").exists() else ""
        if "mode: scheduled" in st and "step: awaiting_review" in st and not re.search(r"step: (skipped|video_ready|approved|published)", st):
            return j
    raise SystemExit("No scheduled job is waiting for review.")


def field(status, key):
    m = re.findall(rf"^{key}:\s*(.+)$", status, re.M)
    return m[-1].strip() if m else ""


def main():
    job = (ROOT / "jobs" / sys.argv[1]) if len(sys.argv) > 1 else latest_job()
    st = (job / "status.md").read_text(encoding="utf-8")
    hook = field(st, "on_screen_hook") or "EV FACTS"
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    py, s = sys.executable, ROOT / "scripts"
    tg.send(f"🎬 Rendering the reel, cover and caption for {job.name}…")
    for cmd in ([py, s / "assemble.py", job.name, "--hook", hook, "--preset", "B", "--vertical"],
                [py, s / "thumbnail.py", job.name, "--hook", hook, "--out", "cover_1"],
                [py, s / "package.py", job.name, "--cover", "cover_1"]):
        r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, env=env)
        if r.returncode != 0:
            tg.send(f"❌ {cmd[1].name} failed: {r.stderr[-400:]}")
            return 1
        if "WARNING" in r.stdout:
            tg.send("⚠️ " + " ".join(l for l in r.stdout.splitlines() if "WARNING" in l)[:500])
    final = job / "final"
    caption = (final / "caption.txt").read_text(encoding="utf-8").strip()
    with open(job / "status.md", "a", encoding="utf-8") as f:
        f.write("step: video_ready\n")
    log(job, "finish", "reel, cover and caption sent for approval")
    tg.video(final / "reel_preview_tg.mp4", f"🎞 {job.name} (1:1 for FB/IG, 9:16 version also saved)")
    tg.photo(final / "cover_1x1.jpg", f"Cover / title: {hook}")
    tg.send(f"✍️ Caption:\n\n{caption}\n\nReply:\n• approve — publish to Instagram now\n• or tell me what to change")
    return 0


if __name__ == "__main__":
    sys.exit(main())
