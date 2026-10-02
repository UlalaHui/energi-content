"""Daily unattended run: topic -> script pack -> lint -> voiceover -> scene images -> contact sheet to Telegram.
Stops at the human review gate (operator replies `go` in Telegram). Never renders or publishes.

Usage:
  python scripts/daily_run.py                 # real run (spends ~$0.07 per scene image, capped by --budget)
  python scripts/daily_run.py --dry-run       # rehearsal: topic + script + voiceover, quotes images, spends $0
  python scripts/daily_run.py --budget 1.0 --scenes 12
"""
import argparse
import json
import math
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime

import requests

from common import ROOT, load_env, log, tokens
import tg

PRICE_PER_IMAGE = 0.07
CTA = "Follow for more EV facts nobody tells you."
OLLAMA = "http://127.0.0.1:11434/v1/chat/completions"

BANNED_TEXT = [
    (r"withstand\w*\s+lightning|lightning[- ]?(proof|resistant)|survives? lightning|safe from lightning|storm[- ]?proof|tahan petir|kalis petir|防雷|抗雷", "lightning claim (brand rule 4)"),
    (r"\btesla\b", "Tesla mention (brand rule 2)"),
    (r"\bRM\s?\d", "price in RM (unverified prices are not allowed)"),
    (r"\b\d+(\.\d+)?\s?x\s+faster|\bthree times faster|\btriple the (speed|charging)", "speed overclaim (car's onboard charger usually limits AC speed)"),
    (r"open (up )?(your|the) (db|distribution|breaker|fuse|electrical) ?(box|board|panel)?", "tells viewers to open electrical panels (no DIY)"),
    (r"reset (the|your) breaker|upsize|bigger breaker|higher[- ]rated breaker", "unsafe electrical advice"),
    (r"(doesn'?t|don'?t|does not|do not) have three[- ]phase", "three-phase claim (many homes do have it)"),
    (r"\bguarantee|fire[- ]?proof|100% safe|completely safe", "absolute safety claim"),
]
BANNED_VISUAL = r"\b(text|words?|letters?|logo|sign|signs|label|labels|screen|phone|paper|receipt|document|tesla|wall charger|charger|charging cable|charging gun|plug|plugged|person|people|man|woman|character|driver|family|child|kids?|numbers?|digits?|tick|cross)\b"


def llm(messages, model, tries=3):
    last = None
    for _ in range(tries):
        try:
            r = requests.post(OLLAMA, json={"model": model, "messages": messages, "temperature": 0.6,
                                            "response_format": {"type": "json_object"}}, timeout=900)
            r.raise_for_status()
            txt = r.json()["choices"][0]["message"]["content"]
            m = re.search(r"\{.*\}", txt, re.S)
            return json.loads(m.group(0) if m else txt)
        except Exception as e:   # noqa: BLE001 - retry any model/parse hiccup
            last = e
    raise RuntimeError(f"LLM failed after {tries} tries: {last}")


def read(p):
    p = pathlib.Path(p)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def skill(name):
    for base in (pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / "skills", ROOT / "prompts"):
        t = read(base / name / "SKILL.md")
        if t:
            return t
    return ""


NEG = re.compile(r"(,|;|\.)?\s*\b(no|without|free of|not|never|avoid)\b[^.;]*", re.I)


def clean_visual(v):
    """Drop negative clauses ('no text, no logos') - they prime the image model and the guard already covers them."""
    out = NEG.sub("", v).strip(" ,;")
    return (out + ".") if out and not out.endswith(".") else out


def check(pack, n_scenes):
    errs = []
    for s in (pack.get("scenes") or [])[:-1]:
        s["visual"] = clean_visual(s.get("visual", ""))
    scenes = pack.get("scenes") or []
    if not (n_scenes - 2 <= len(scenes) <= n_scenes + 2):
        errs.append(f"need {n_scenes} scenes (about), got {len(scenes)}")
    if scenes:
        if scenes[-1].get("type") != "text_card":
            errs.append("last scene must be type text_card with vo_text exactly the CTA")
        for i, s in enumerate(scenes, 1):
            if int(s.get("id", 0)) != i:
                errs.append(f"scene ids must be 1..N in order (scene {i} has id {s.get('id')})")
                break
        for s in scenes[:-1]:
            if s.get("type") != "generated":
                errs.append(f"scene {s.get('id')} must be type generated")
            if not s.get("vo_text", "").strip():
                errs.append(f"scene {s.get('id')} has empty vo_text")
            bad = re.findall(BANNED_VISUAL, s.get("visual", ""), re.I)
            if bad:
                errs.append(f"scene {s.get('id')} visual mentions banned things {sorted(set(b.lower() for b in bad))}; "
                            "describe objects only, no text/people/chargers/plugs/symbols")
    spoken = " ".join(s.get("vo_text", "") for s in scenes)
    words = len(tokens(spoken))
    if not 160 <= words <= 190:
        errs.append(f"spoken script is {words} words; it must be 160-190 (adjust vo_text)")
    hooks = pack.get("hooks") or []
    if len(hooks) < 5:
        errs.append("give 10 hooks")
    elif scenes and tokens(hooks[0]) != tokens(scenes[0].get("vo_text", "")):
        errs.append("scene 1 vo_text must be exactly hooks[0]")
    alltext = " ".join([spoken, pack.get("caption", ""), " ".join(hooks), pack.get("on_screen_hook", "")]
                       + [s.get("label", "") for s in scenes])
    for pat, why in BANNED_TEXT:
        if re.search(pat, alltext, re.I):
            errs.append(f"banned wording: {why}")
    if len((pack.get("on_screen_hook") or "").split()) > 5:
        errs.append("on_screen_hook must be max 5 words")
    return errs, words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--budget", type=float, default=1.0)
    ap.add_argument("--scenes", type=int, default=12, help="total scenes incl. the end card")
    ap.add_argument("--topic", help="force a topic (default: the agent picks one)")
    args = ap.parse_args()
    load_env()
    model = os.environ.get("LLM_MODEL", "gemma4:31b-cloud")
    tag = "[REHEARSAL] " if args.dry_run else ""

    try:
        tg.send(f"{tag}⏰ Daily Energi reel run started ({datetime.now():%d %b %H:%M}).")
        brand = "\n\n".join(read(ROOT / "brand" / f) for f in ("brand_profile.md", "brand_rules.md", "recipe.md", "style_bible.md"))
        done = sorted(p.name for p in (ROOT / "jobs").iterdir() if p.is_dir()) if (ROOT / "jobs").exists() else []

        # 1. topic
        if args.topic:
            t = {"topic": args.topic, "angle": "", "alternatives": []}
        else:
            t = llm([{"role": "system", "content": "You plan short EV explainer reels for Energi Elite (Malaysian home EV charger installer). Reply in JSON only."},
                     {"role": "user", "content": f"BRAND:\n{brand}\n\nJob folders already made (topics already covered): {done}\n\n"
                      "Pick ONE topic from the topic bank that is not covered yet. Prefer topics about charging habits, costs, trips or batteries "
                      "over wiring/breaker topics. Also name 2 alternatives you considered. JSON: "
                      '{"topic": "...", "angle": "one line", "alternatives": ["...", "..."]}'}], model)
        topic = t["topic"].strip()
        slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:40]
        job = ROOT / "jobs" / f"{datetime.now():%Y%m%d}-{slug}"
        if job.exists():
            job = job.with_name(job.name + datetime.now().strftime("-%H%M"))
        job.mkdir(parents=True)
        (job / "status.md").write_text(f"reel_type: explainer\nmode: scheduled\ntopic: {topic}\nstep: started\n", encoding="utf-8")
        alts = ", ".join(t.get("alternatives", [])[:2])
        tg.send(f"{tag}📌 Today's topic: {topic}\n{t.get('angle', '')}\n(also considered: {alts or '-'})\nJob: {job.name}")

        # 2. script pack + lint (deterministic checks + model claim review), max 4 attempts
        sys_msg = ("You write Energi Elite reel script packs. Follow these instructions exactly.\n\n"
                   f"{skill('energi-script-pack')}\n\nBRAND:\n{brand}\n\nReply in JSON only.")
        ask = (f"Topic: {topic}\nAngle: {t.get('angle', '')}\n"
               f"Make the pack as JSON with exactly {args.scenes} scenes (the last is the end card):\n"
               '{"title": "...", "hooks": ["10 hooks; hooks[0] is the chosen one"], "on_screen_hook": "max 5 words, uppercase",'
               ' "caption": "Instagram caption with CTA and 5-6 hashtags incl #EnergiElite #EVMalaysia",'
               ' "scenes": [{"id": 1, "vo_text": "exactly hooks[0]", "visual": "...", "type": "generated", "label": "2-5 words"}, ...,'
               f' {{"id": {args.scenes}, "vo_text": "{CTA}", "visual": "end card: black background, Energi Elite logo", "type": "text_card"}}]}}\n'
               "Rules: the spoken script is ALL vo_text joined, 160-190 words in total. Explainer reel: no chargers, plugs or cables in visuals; "
               "no people; never mention text, numbers, screens, signs or symbols in visuals at all (not even to say \"no text\") - describe only the objects you want to see. No prices, no brand/app/network names, hedge numbers with 'about'. "
               "Every technical claim must be correct and hedged ('can', 'often', 'most').")
        msgs = [{"role": "system", "content": sys_msg}, {"role": "user", "content": ask}]
        pack, words, errs = None, 0, ["not generated"]
        for attempt in range(1, 7):
            pack = llm(msgs, model)
            errs, words = check(pack, args.scenes)
            if not errs:
                words_only = {"spoken_script": " ".join(x.get("vo_text", "") for x in pack["scenes"]),
                              "on_screen_labels": [x.get("label", "") for x in pack["scenes"] if x.get("label")],
                              "hooks": pack.get("hooks", []), "on_screen_hook": pack.get("on_screen_hook", ""),
                              "caption": pack.get("caption", "")}
                review = llm([{"role": "system", "content": "You are a strict fact checker for an EV charging company in Malaysia. "
                               f"Brand rules:\n{read(ROOT / 'brand' / 'brand_rules.md')}\nReply in JSON only."},
                              {"role": "user", "content": "Check ONLY the wording below (visuals and format are checked elsewhere - ignore them). "
                               "FAIL only for: a technical statement that is false or stated as certain when it is not, unsafe or DIY electrical advice, "
                               "a lightning/Tesla/price claim, or an unverifiable company fact. Hedged general advice ('about', 'often', 'most EVs') is fine. JSON: "
                               '{"result": "PASS" or "FAIL", "issues": ["quote the exact phrase and say why"]}\n\n' + json.dumps(words_only, ensure_ascii=False)}], model)
                if str(review.get("result", "")).upper().startswith("PASS"):
                    break
                errs = [f"fact/brand check: {i}" for i in review.get("issues", [])] or ["fact/brand check failed"]
            log(job, "lint", f"attempt {attempt}: FAIL - {'; '.join(errs)[:400]}")
            msgs += [{"role": "assistant", "content": json.dumps(pack, ensure_ascii=False)},
                     {"role": "user", "content": "Fix ALL of these problems and return the full corrected JSON (keep everything else the same; to change the word count, edit vo_text):\n- " + "\n- ".join(errs)}]
        if errs:
            tg.send(f"{tag}❌ Script failed the lint after 6 attempts, so nothing was spent.\n- " + "\n- ".join(errs[:6]))
            log(job, "lint", "FAIL - stopped before any spend")
            return 1

        scenes = pack["scenes"]
        for s in scenes:
            s["id"] = int(s["id"])
        script_body = " ".join(s["vo_text"].strip() for s in scenes)
        (job / "scenes.json").write_text(json.dumps(scenes, indent=1, ensure_ascii=False), encoding="utf-8")
        (job / "script.md").write_text(f"# {pack.get('title', topic)}\n\n{script_body}\n", encoding="utf-8")
        (job / "hooks.md").write_text("\n".join(f"{i}. {h}" + (" [chosen]" if i == 1 else "") for i, h in enumerate(pack["hooks"], 1)) + "\n", encoding="utf-8")
        (job / "caption.md").write_text(pack.get("caption", "").strip() + "\n", encoding="utf-8")
        (job / "lint.md").write_text(f"result: PASS\n- {words} spoken words; brand, safety and visual checks passed; model fact check PASS\n", encoding="utf-8")
        hook = pack.get("on_screen_hook", "").strip().upper() or " ".join(pack["hooks"][0].split()[:5]).upper()
        with open(job / "status.md", "a", encoding="utf-8") as f:
            f.write(f"hook: {pack['hooks'][0]}\non_screen_hook: {hook}\nlint: PASS\nstep: script_ready\n")
        tg.send(f"{tag}📝 Script ready ({words} words, lint PASS)\nHook: {pack['hooks'][0]}\nOn-screen: {hook}\n\n{script_body}")

        # 3. voiceover (free)
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        py = sys.executable
        r = subprocess.run([py, str(ROOT / "scripts" / "voiceover.py"), job.name], capture_output=True, text=True, env=env)
        if r.returncode != 0:
            raise RuntimeError("voiceover failed: " + r.stderr[-500:])

        # 4. scene images (paid)
        n_img = sum(1 for s in scenes if s.get("type") == "generated")
        cost = n_img * PRICE_PER_IMAGE
        if cost > args.budget:
            tg.send(f"{tag}⚠️ {n_img} images would cost ~${cost:.2f}, over the ${args.budget:.2f} budget. Stopped; nothing spent.")
            return 1
        if args.dry_run:
            tg.send(f"{tag}🎨 Would now generate {n_img} scene images (~${cost:.2f}). Rehearsal ends here; nothing spent.\nJob: {job.name}")
            with open(job / "status.md", "a", encoding="utf-8") as f:
                f.write("step: skipped\n")
            return 0
        tg.send(f"🎨 Generating {n_img} scene images (~${cost:.2f})…")
        kf = [py, str(ROOT / "scripts" / "keyframes.py"), job.name, "--yes", "--workers", "3"]
        subprocess.run(kf, capture_output=True, text=True, env=env)
        missing = [s["id"] for s in scenes if s.get("type") == "generated"
                   and not (job / "keyframes" / f"scene_{s['id']:02d}.png").exists()]
        if missing:   # one retry for timeouts
            subprocess.run(kf + ["--scenes", ",".join(map(str, missing))], capture_output=True, text=True, env=env)
            missing = [i for i in missing if not (job / "keyframes" / f"scene_{i:02d}.png").exists()]
        sheet = job / "keyframes" / "contact.jpg"
        with open(job / "status.md", "a", encoding="utf-8") as f:
            f.write(f"spend: ${cost:.2f}\nstep: awaiting_review\n")
        note = f"\n⚠️ Scenes {missing} failed and will show a placeholder (reply redo {','.join(map(str, missing))})." if missing else ""
        cap = (f"🖼 {n_img} scenes ready (~${cost:.2f}).{note}\n\nReply:\n• go — make the video, cover and caption\n"
               "• redo 3,7 — regenerate those scenes\n• skip — drop this reel")
        if sheet.exists():
            tg.photo(sheet, cap)
        else:
            tg.send(cap)
        return 0
    except Exception as e:   # noqa: BLE001 - always tell the operator
        tg.send(f"{tag}❌ Daily run failed: {str(e)[:500]}")
        raise


if __name__ == "__main__":
    sys.exit(main())
