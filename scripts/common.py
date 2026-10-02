"""Shared helpers for the Energi Content Machine pipeline scripts."""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://api.higgsfield.ai"


def load_env():
    """Load KEY=VALUE pairs from energi-content/.env into os.environ (no overwrite)."""
    p = ROOT / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_config():
    return json.loads((ROOT / "scripts" / "config.json").read_text(encoding="utf-8"))


def job_dir(arg):
    p = pathlib.Path(arg)
    if not p.exists():
        p = ROOT / "jobs" / arg
    if not p.exists():
        sys.exit(f"Job folder not found: {arg}")
    return p.resolve()


def load_scenes(job):
    return json.loads((job / "scenes.json").read_text(encoding="utf-8"))


def scene_name(scene):
    return f"scene_{int(scene['id']):02d}"


def log(job, step, msg):
    """Append a timestamped line to the job's status.md so the agent and operator can follow progress."""
    line = f"- {datetime.now():%Y-%m-%d %H:%M} [{step}] {msg}\n"
    with open(job / "status.md", "a", encoding="utf-8") as f:
        f.write(line)
    print(line.strip())


def tokens(text):
    """Normalise text into lowercase word tokens (hyphens split, punctuation dropped)."""
    return re.findall(r"[a-z0-9]+", text.lower().replace("'", ""))


# ---------- ffmpeg helpers ----------

def need(binary):
    if not shutil.which(binary):
        sys.exit(f"'{binary}' not found on PATH.")


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(map(str, cmd))}\n{r.stderr[-2000:]}")
    return r.stdout


def probe_duration(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    return float(out.strip())


def probe_size(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=width,height", "-of", "csv=p=0:s=x", str(path)])
    w, h = out.strip().split("x")[:2]
    return int(w), int(h)


# ---------- Higgsfield API ----------

def _headers(json_body=True):
    import requests  # noqa: F401  (fail early with a clear message if missing)
    combined = os.environ.get("HF_KEY", "").strip()
    kid = os.environ.get("HIGGSFIELD_API_KEY_ID", "").strip()
    sec = os.environ.get("HIGGSFIELD_API_KEY_SECRET", "").strip()
    if combined:
        cred = combined                      # new console format: "<id>:<secret>" in one string
    elif kid and sec:
        cred = f"{kid}:{sec}"
    else:
        sys.exit("Set HF_KEY=<key copied from the Higgsfield console> in energi-content/.env")
    h = {"Authorization": f"Key {cred}"}
    if json_body:
        h["Content-Type"] = "application/json"
    return h


def _request(method, url, tries=4, **kw):
    """HTTP call with retries on timeouts, connection errors, 429 and 5xx (backoff 5s, 15s, 30s)."""
    import requests
    waits = [5, 15, 30]
    for attempt in range(tries):
        try:
            r = requests.request(method, url, timeout=kw.pop("timeout", 90), **kw)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code}: {r.text[:200]}")
            return r
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
            if attempt == tries - 1:
                raise RuntimeError(f"{method} {url} failed after {tries} tries: {e}")
            wait = waits[min(attempt, len(waits) - 1)]
            print(f"  network issue ({e.__class__.__name__}), retrying in {wait}s...")
            time.sleep(wait)


def hf_submit(endpoint, body):
    h = _headers()
    h["Idempotency-Key"] = str(uuid.uuid4())   # same key on every retry, so a retry can't double-charge
    r = _request("POST", f"{API}/{endpoint.strip('/')}", headers=h, json=body)
    if r.status_code >= 400:
        raise RuntimeError(f"Submit to {endpoint} failed ({r.status_code}): {r.text[:500]}")
    return r.json()


def hf_wait(sub, timeout=900, every=5):
    url = sub.get("status_url") or f"{API}/requests/{sub['request_id']}/status"
    t0 = time.time()
    while True:
        r = _request("GET", url, headers=_headers(False))
        if r.status_code >= 400:
            raise RuntimeError(f"Status check failed ({r.status_code}): {r.text[:300]}")
        d = r.json()
        st = d.get("status")
        if st == "completed":
            return d
        if st in ("failed", "nsfw", "canceled"):
            raise RuntimeError(f"Request {sub.get('request_id')} ended with status '{st}': {json.dumps(d)[:300]}")
        if time.time() - t0 > timeout:
            raise TimeoutError(f"Request {sub.get('request_id')} still '{st}' after {timeout}s")
        time.sleep(every)


def hf_upload(path):
    """Upload a local image and return a public URL usable as image_url."""
    path = pathlib.Path(path)
    ct = {".png": "image/png", ".webp": "image/webp"}.get(path.suffix.lower(), "image/jpeg")
    r = _request("POST", f"{API}/files/generate-upload-url", headers=_headers(), json={"content_type": ct})
    if r.status_code >= 400:
        raise RuntimeError(f"Upload URL request failed ({r.status_code}): {r.text[:300]}")
    d = r.json()
    u = _request("PUT", d["upload_url"], data=path.read_bytes(),
                 headers=d.get("upload_headers") or {"Content-Type": ct}, timeout=300)
    if u.status_code >= 400:
        raise RuntimeError(f"File upload failed ({u.status_code}): {u.text[:300]}")
    return d["public_url"]


def media_url(result, kind):
    """Find the output URL in a completed result ('image' or 'video')."""
    if kind == "image":
        imgs = result.get("images") or []
        if imgs and imgs[0].get("url"):
            return imgs[0]["url"]
    if kind == "video":
        v = result.get("video") or {}
        if v.get("url"):
            return v["url"]
        vids = result.get("videos") or []
        if vids and vids[0].get("url"):
            return vids[0]["url"]
    raise RuntimeError(f"No {kind} URL in result: {json.dumps(result)[:300]}")


def download(url, dest):
    dest = pathlib.Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = _request("GET", url, timeout=300)
    if r.status_code >= 400:
        raise RuntimeError(f"Download failed ({r.status_code}) for {url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(r.content)
    tmp.replace(dest)          # write-then-rename: never leaves a half-written image behind
    return dest


def contact_sheet(images, dest, cols=6, cell=320):
    """Grid of thumbnails with scene numbers, for quick human or vision review."""
    from PIL import Image, ImageDraw
    images = [pathlib.Path(p) for p in images if pathlib.Path(p).exists()]
    if not images:
        return None
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * cell), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    for i, p in enumerate(images):
        im = Image.open(p).convert("RGB")
        im.thumbnail((cell, cell))
        x, y = (i % cols) * cell, (i // cols) * cell
        sheet.paste(im, (x + (cell - im.width) // 2, y + (cell - im.height) // 2))
        d.rectangle([x, y, x + 70, y + 24], fill=(0, 0, 0))
        d.text((x + 6, y + 5), p.stem.replace("scene_", "#").replace("frame_", "t"), fill=(255, 255, 255))
    sheet.save(dest, quality=88)
    return dest
