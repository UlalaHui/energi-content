"""Collect the approved outputs of a job into <job>/final/ (free, local). Does NOT publish anything.

Usage:  python scripts/package.py <job> --cover cover_2
Output: <job>/final/reel_1x1.mp4, reel_9x16.mp4 (if made), reel_preview_tg.mp4,
        cover_1x1.jpg, cover_9x16.jpg, caption.txt, summary.md
"""
import argparse
import re
import shutil

from common import job_dir, log, probe_duration, probe_size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--cover", default="thumbnail", help="cover name stem chosen by the operator, e.g. cover_2")
    args = ap.parse_args()
    job = job_dir(args.job)
    out = job / "final"
    out.mkdir(exist_ok=True)

    copies = {
        job / "renders" / "final_1x1.mp4": out / "reel_1x1.mp4",
        job / "renders" / "final_9x16.mp4": out / "reel_9x16.mp4",
        job / "renders" / "final_tg.mp4": out / "reel_preview_tg.mp4",
        job / f"{args.cover}_1x1.jpg": out / "cover_1x1.jpg",
        job / f"{args.cover}_9x16.jpg": out / "cover_9x16.jpg",
    }
    missing = [str(src.name) for src in copies if not src.exists() and "9x16" not in src.name]
    if missing:
        raise SystemExit(f"Missing outputs: {', '.join(missing)}. Run assemble.py / thumbnail.py first.")
    for src, dst in copies.items():
        if src.exists():
            shutil.copy2(src, dst)

    cap = (job / "caption.md").read_text(encoding="utf-8")
    # drop markdown headings ("# Caption") but keep hashtag lines ("#EnergiElite")
    cap = "\n".join(l for l in cap.splitlines() if not re.match(r"^\s*#{1,6}\s", l)).strip()
    (out / "caption.txt").write_text(cap + "\n", encoding="utf-8")

    reel = out / "reel_1x1.mp4"
    w, h = probe_size(reel)
    status = (job / "status.md").read_text(encoding="utf-8")
    billed = re.findall(r"\[animate\].*?(\d+)s billed", status)
    summary = [
        f"# Final package: {job.name}",
        f"- Reel: reel_1x1.mp4, {w}x{h}, {probe_duration(reel):.1f}s",
        "- Vertical: reel_9x16.mp4" if (out / "reel_9x16.mp4").exists() else "- Vertical: not exported",
        f"- Cover: {args.cover}",
        "- Caption: caption.txt",
        f"- Clip seconds billed: {sum(int(b) for b in billed)}",
        "- Status: ready for approval. NOT published.",
    ]
    (out / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    log(job, "package", f"final/ ready ({len(list(out.iterdir()))} files), cover {args.cover}; not published")


if __name__ == "__main__":
    main()
