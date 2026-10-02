"""Make the cover: a scene keyframe + hook text + logo (free, local).

Usage:
  python scripts/thumbnail.py <job> --hook "Stop blaming your charger"
  python scripts/thumbnail.py <job> --hook "..." --scene 3
Output: <job>/thumbnail_1x1.jpg and <job>/thumbnail_9x16.jpg
Text is typed by code (not generated), so the claim lint can check it and it can't contain typos.
"""
import argparse
import pathlib

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from common import ROOT, job_dir, load_config, load_scenes, log, run, scene_name

FONTS = [r"C:\Windows\Fonts\ariblk.ttf", r"C:\Windows\Fonts\arialbd.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def font(size):
    for f in FONTS:
        if pathlib.Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def wrap(text, fnt, max_w, draw):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def make_square(src, hook, cfg, size=1080):
    im = Image.open(src).convert("RGB")
    s = min(im.size)
    im = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width + s) // 2, (im.height + s) // 2))
    im = im.resize((size, size), Image.LANCZOS).convert("RGBA")

    # darken the lower part so the text stays readable
    grad = Image.new("L", (1, size))
    for y in range(size):
        grad.putpixel((0, y), int(max(0, (y - size * 0.45) / (size * 0.55)) * 170))
    shade = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    shade.putalpha(grad.resize((size, size)))
    im.alpha_composite(shade)

    draw = ImageDraw.Draw(im)
    text = hook.upper()
    fs = 92
    while fs > 48:
        fnt = font(fs)
        lines = wrap(text, fnt, size - 160, draw)
        if len(lines) <= 3:
            break
        fs -= 6
    orange = tuple(int(cfg["brand_orange_bgr"][i:i + 2], 16) for i in (4, 2, 0))
    line_h = int(fs * 1.25)
    y = size - 110 - line_h * len(lines)
    for ln in lines:
        w = draw.textlength(ln, font=fnt)
        x = (size - w) / 2
        draw.rounded_rectangle([x - 22, y - 10, x + w + 22, y + line_h - 6], radius=14, fill=orange + (255,))
        draw.text((x, y), ln, font=fnt, fill=(255, 255, 255))
        y += line_h + 8

    logo = Image.open(ROOT / "assets" / "logo.png").convert("RGBA")
    lw = 360
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    im.alpha_composite(logo, ((size - lw) // 2, 50))
    return im.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--hook", required=True, help="cover text (run it through energi-claim-lint)")
    ap.add_argument("--scene", type=int, help="scene id to use as the background (default: first generated)")
    ap.add_argument("--out", default="thumbnail", help="output name stem, e.g. cover_1 -> cover_1_1x1.jpg")
    args = ap.parse_args()
    job, cfg = job_dir(args.job), load_config()

    scenes = [s for s in load_scenes(job) if s.get("type", "generated") == "generated"]
    if args.scene:
        scenes = [s for s in scenes if int(s["id"]) == args.scene]
    src = next((job / "keyframes" / f"{scene_name(s)}.png" for s in scenes
                if (job / "keyframes" / f"{scene_name(s)}.png").exists()), None)
    if src is None:   # text-to-video scenes have no keyframe: grab a frame from the clip instead
        clip = next((job / "clips" / f"{scene_name(s)}.mp4" for s in scenes
                     if (job / "clips" / f"{scene_name(s)}.mp4").exists()), None)
        if clip is not None:
            src = job / "clips" / f"{clip.stem}_cover.png"
            run(["ffmpeg", "-y", "-v", "error", "-ss", "1.0", "-i", str(clip), "-frames:v", "1", str(src)])
    if src is None:
        raise SystemExit("No keyframe or clip found. Run keyframes.py or animate.py first.")

    sq = make_square(src, args.hook, cfg)
    sq.save(job / f"{args.out}_1x1.jpg", quality=92)

    tall = sq.resize((1920, 1920)).crop((420, 0, 1500, 1920)).filter(ImageFilter.GaussianBlur(30))
    tall.paste(sq, (0, (1920 - 1080) // 2))
    tall.save(job / f"{args.out}_9x16.jpg", quality=92)
    log(job, "thumbnail", f"{args.out}_1x1.jpg + {args.out}_9x16.jpg from {src.name}, hook: {args.hook}")


if __name__ == "__main__":
    main()
