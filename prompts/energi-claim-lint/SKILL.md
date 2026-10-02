---
name: energi-claim-lint
description: Check Energi Elite scripts, captions, on-screen text, hashtags and thumbnail text against the brand rules before any generation or publishing. Use after writing or editing any Energi Elite content text.
---

# Energi claim lint

## Inputs
All text files in the job folder: `script.md`, `hooks.md`, `caption.md`, `scenes.json` (vo_text and visual), plus any thumbnail or on-screen text.

## Checks (any FAIL blocks the job)
1. **Lightning claims.** Exact or paraphrased: withstand lightning, lightning-proof, lightning-resistant, survives lightning, immune to / safe from lightning, storm-proof, protects against lightning strikes; Malay: tahan petir, kalis petir, selamat dari petir; Chinese: 防雷, 抗雷击, 不怕雷. Also flag any sentence implying the product protects against lightning or storms.
2. **Tesla.** Any visual description featuring a Tesla, or a Tesla logo or badge. Text may list Tesla only as one of several compatible brands.
3. **E1 renders.** Any `generated` scene that shows, or implies, a wall charger, the E1, Energi Elite hardware, a charging gun or cable plugged into the car, or a car "charging" at a home or porch. All of these must be `real_photo`. Judge what the scene would show, not only exact keywords.
4. **Logos or text in generated visuals.** Any `generated` visual that asks for a logo, brand name (including ENERGI ELITE), readable text, numbers, labels or signs, or that does not exclude logos and badges. The logo and end card are added in assembly, never generated.
5. **Unverified company facts.** Prices, install counts, ratings, warranty or certifications not in `brand/brand_profile.md`.
6. **Format.** Delivery not set to 1:1.
7. **Recipe fit** (WARN, not FAIL, except length):
    - FAIL if `script.md` spoken words (excluding the title) fall outside 160-190
    - WARN if fewer than 2 Malaysian references in the spoken script (visuals don't count)
    - WARN if a body beat has no concrete number or everyday analogy
    - WARN if the end card is `generated` instead of `text_card`
8. **Safety advice** (FAIL). On electrical topics, any wording that encourages DIY electrical work, resetting a tripping breaker repeatedly, or upsizing a breaker. Technical statements must be correct; when unsure, mark `[VERIFY: electrician]`.

9. **Real photos** (FAIL). Read `reel_type` in `status.md`.
    - explainer: any `real_photo` scene fails.
    - product: every `real_photo` scene must have a `photo` that is listed in `assets\e1-photos\photos.md` (FAIL if missing or not listed); a file used twice is a WARN.

10. **Electrical accuracy** (FAIL). Check every technical claim against this list:
    - RCCB / RCCB Type A = protects against **earth leakage** (electric shock, fire risk). It does **not** protect against surges or lightning.
    - MCB = trips on **sustained overcurrent / overheating of the breaker** (e.g. overload, undersized circuit).
    - Surges are handled by a **surge protection device (SPD)**, a separate part. Never attribute surge protection to an RCCB or MCB.
    - A tripping breaker has several possible causes (overload, earth leakage, faulty appliance, wiring). Never say it is *always* or *definitely* one cause; use "can be", "often".
    - Many Malaysian landed homes **do** have three-phase supply. Never say a home "doesn't have" three-phase; say "may not have" / "check if your home has".
    - Charging-time maths must add up (kWh / kW = hours, rounded honestly: 8 kWh on 7 kW is "just over an hour").
    - Undersized cable leads to heat build-up; don't exaggerate it into certain fire or melting unless hedged ("can").
11. **Prices and competitors in ALL text, including scene `label` fields** (FAIL). Any RM amount for Energi Elite's products or services, or any implied competitor price, unless it's in brand_profile.md and not marked [VERIFY]. Generic examples ("a few hundred ringgit") are fine.

## Output: write `lint.md` in the job folder
```
result: PASS | FAIL
- [FAIL] file:line, quoted text, rule broken, suggested fix
- [WARN] ...
```
Then report the result to the operator in 1-3 lines. On FAIL, propose fixed wording; do not continue the pipeline.
