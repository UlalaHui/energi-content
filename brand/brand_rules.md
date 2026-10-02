# Energi Elite: Brand Rules (hard rules, never break)

Source: the Energi Elite challenge brief. Any output that breaks a rule is rejected and regenerated.

## 1. Square 1:1 for Facebook and Instagram
- Final export: 1080x1080. A 9:16 cut may also be exported from the same scenes.
- Keep text and key subjects inside the centre-safe square so both crops work.

## 2. No Tesla logos, ever
- Never mention Tesla visually. Every image/video prompt includes: `no logos, no brand badges, no emblems on the car`.
- The recurring car is an unbadged orange SUV (see `style_bible.md`).
- Tesla may be named in text only as one of many compatible brands, never as a featured car. When in doubt, leave it out.

## 3. Real Energi Elite installation photos for the E1 charger
- Any scene that shows the E1 charger or a wall-mounted charger must use a **real photo** from `assets/e1-photos/`, never an AI render.
- Mark such scenes `type: "real_photo"` in `scenes.json`.
- Generated scenes must not include a wall charger. If one appears, reject the scene.

## 4. Never claim the products "withstand lightning"
Banned in script, captions, on-screen text, thumbnail text and hashtags. Includes paraphrases:

**English:** withstand lightning, lightning-proof, lightning proof, lightning-resistant, survives lightning, immune to lightning, safe from lightning, storm-proof, protects against lightning strikes
**Malay:** tahan petir, kalis petir, selamat dari petir
**Chinese:** 防雷, 抗雷击, 不怕雷

If a topic touches storms, surges or weather, describe only what the installation does (e.g. proper breakers, RCCB Type A, earthing). Never promise protection from lightning.

## General claim rules
- No invented numbers about Energi Elite (prices, install counts, ratings, warranty). Use only `brand_profile.md` facts; anything else gets `[VERIFY]`.
- General EV facts must be broadly true and framed with "most" or "typical" where they vary by car.
- No claims about competitors by name.
