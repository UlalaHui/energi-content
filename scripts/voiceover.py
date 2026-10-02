"""Generate the voiceover with word timings, and map each scene to its time range.

Usage:  python scripts/voiceover.py <job>
Output: <job>/vo.mp3, <job>/words.json, <job>/timeline.json
Free:   uses Microsoft Edge TTS (edge-tts), no API key.
"""
import argparse
import asyncio
import json
import re

from common import ROOT, job_dir, load_config, load_scenes, log, tokens, probe_duration


def script_text(job):
    raw = (job / "script.md").read_text(encoding="utf-8")
    if "[VERIFY" in raw:
        raise SystemExit("script.md still contains [VERIFY] markers. Resolve them before recording.")
    lines = [l.strip() for l in raw.splitlines() if l.strip() and not l.strip().startswith("#")]
    return " ".join(lines)


async def synth(text, voice, rate, mp3_path):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words = []
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append({"text": chunk["text"], "start": round(start, 3),
                              "end": round(start + chunk["duration"] / 1e7, 3)})
    return words


def build_timeline(scenes, words, audio_len, tail):
    """Assign each scene a start/end by walking the word timings in order."""
    # Expand each spoken word into normalised tokens so 'thirty-two' etc. line up.
    flat = []
    for w in words:
        for t in tokens(w["text"]) or [""]:
            flat.append((t, w["start"], w["end"]))
    flat = [f for f in flat if f[0]]

    counts = [len(tokens(s.get("vo_text", ""))) for s in scenes]
    timeline, i, ok = [], 0, sum(counts) == len(flat)
    if not ok:
        print(f"WARNING: scene words ({sum(counts)}) != spoken words ({len(flat)}). "
              "Falling back to proportional timing; check scenes.json vo_text matches script.md.")
    total_words = max(sum(counts), 1)
    for idx, (s, n) in enumerate(zip(scenes, counts)):
        if ok:
            if n:
                start = flat[i][1]
            else:  # silent scene (e.g. end card with no VO): starts right after the last spoken word
                start = flat[i - 1][2] if i > 0 else 0.0
            i += n
        else:
            start = audio_len * sum(counts[:idx]) / total_words
        timeline.append({"id": s["id"], "type": s.get("type", "generated"), "start": round(start, 3)})
    for k, t in enumerate(timeline):
        t["end"] = timeline[k + 1]["start"] if k + 1 < len(timeline) else round(audio_len + tail, 3)
        t["start"] = 0.0 if k == 0 else t["start"]
        t["duration"] = round(t["end"] - t["start"], 3)
    return timeline


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    args = ap.parse_args()
    job = job_dir(args.job)
    cfg = load_config()
    scenes = load_scenes(job)

    text = script_text(job)
    mp3 = job / "vo.mp3"
    words = asyncio.run(synth(text, cfg["voice"], cfg["voice_rate"], mp3))
    if not words:
        raise SystemExit("No word timings returned. Update edge-tts: pip install -U edge-tts")
    audio_len = probe_duration(mp3)
    timeline = build_timeline(scenes, words, audio_len, cfg["end_card_tail_s"])

    (job / "words.json").write_text(json.dumps(words, indent=1), encoding="utf-8")
    (job / "timeline.json").write_text(json.dumps(timeline, indent=1), encoding="utf-8")
    log(job, "voiceover", f"vo.mp3 {audio_len:.1f}s, {len(words)} words, timeline for {len(timeline)} scenes")


if __name__ == "__main__":
    main()
