---
name: energi-script-pack
description: Write an Energi Elite explainer video script pack (script, 10 hooks, caption, scene plan) in their existing reel style. Use when the operator gives a topic or asks for topic suggestions for Energi Elite content.
---

# Energi script pack

## Before writing
Read, from the project folder: `brand/recipe.md`, `brand/brand_profile.md`, `brand/brand_rules.md`, `brand/style_bible.md`, and `reels/transcripts.md` as style examples.

## Create `jobs/<YYYYMMDD>-<slug>/` with:

### script.md
- 160-190 spoken words (count them; the title doesn't count), short sentences, second person
- Follow the beats in `recipe.md`: hook, myth check/setup, explain (2-3 beats, one number or analogy each), twist ("the part nobody tells you"), practical takeaway, CTA
- At least 2 Malaysian references
- End with: "Follow for more EV facts nobody tells you."
- No product pitch in the body
- Any number you are not sure of gets `[VERIFY]`

### hooks.md
- 10 alternative first lines, 12 words or fewer, numbered
- Each uses a different pattern from `recipe.md` (question, shock number, hidden danger, myth bust, local scene, warning, comparison, "nobody tells you", cost angle, direct challenge)
- Mark your top 2 picks and say why in one line each

### caption.md
- 2-4 short lines for IG/FB, ends with a CTA
- 3-6 hashtags (include #EnergiElite #EVMalaysia)

### scenes.json
- Scene ids are integers starting at **1**, in order, no gaps. One scene per 1-2 sentences, 12-18 scenes.
- `duration_s`: estimate from the VO (about 2.6 words per second, minimum 2.5s). Final timing comes from the voiceover.
- In explainer reels every scene is `type: "generated"` (product reels: see "Reel type" below), except the last one: `type: "text_card"`, visual `"end card: black background, Energi Elite logo"`. Explainer reels **never** use `real_photo` and never show a wall charger, the E1, a charging gun or a cable plugged into a car.
- Each `visual` must stand alone: never write "the same ...", "as before" or refer to another scene. The image model sees one scene at a time.
- Never put brand names, readable text, digits or logos in a `visual`. Numbers go in `label`.

### Diagram-first: show the idea literally (most important rule)
The viewer must understand the point **with the sound off**. For every scene, ask: "What single picture would a teacher draw on a whiteboard for this sentence?" Then describe that picture as a clean 3D object.

Use these patterns (no text in the image; the label carries the words and numbers):
| Sentence type | Visual pattern | Example visual |
|---|---|---|
| A range or sweet spot ("happiest between 20 and 80%") | **Gauge**: a large vertical battery icon split into coloured bands | "A tall glossy battery icon divided into bands: bottom band red, large middle band glowing green, top band red." + label `20-80% sweet spot` |
| A setting or action ("set your limit to 80%") | **Control**: a big slider or dial being moved | "A large glossy horizontal slider control, the knob stopped about four-fifths along, the filled part glowing green." + label `Set limit: 80%` |
| A bad combination ("heat + high voltage") | **Cause + effect side by side** | "A battery pack glowing red-hot next to a tall thermometer with the red line near the top, heat shimmer above both." + label `Heat + 100% = faster ageing` |
| A comparison (A vs B) | **Split screen**: two objects side by side, one green one red | "Two battery packs side by side: the left one cool and glowing blue, the right one glowing hot red." + label `80% vs 100%` |
| Change over time ("ages faster") | **Before / after** | "Two identical battery cells side by side, the left one bright and new, the right one dull, scratched and slightly swollen." + label `After years at 100%` |
| A place or habit ("on the tarmac at noon") | **Scene**: the orange SUV in that place | "The orange SUV parked on a sunny open-air car park at midday, harsh sunlight, heat shimmer rising from the tarmac." |
| A component (DB box, MCB, RCCB, cable, 12V battery) | **Hero object**: the real part, large and centred | see examples below |

Avoid metaphor objects (rubber bands, suitcases, water bottles, rivers, faces, mascots) unless the object **is** the diagram.

**No people or cartoon characters** (the house style is objects, cars, batteries, homes). **Symbols must match the meaning**: never ask for a tick, cross, X, arrow or warning sign; show the idea with colour and state instead (green glow = good, orange-red = bad).

**Never show objects that normally carry writing**: paper, quotes, receipts, documents, bills, screens, phones, signs, labels, packaging. The image model fills them with fake garbled text. Show the idea with physical objects plus our `label` instead (e.g. a price comparison = two stacks of coins, small vs large). If you need a comparison, use the split-screen pattern with the real objects.

### Make every component recognisable
- Describe real parts by how they actually look. Examples:
  - DB box: "a home electrical distribution board on a white wall: grey metal cabinet with the door open, a neat row of white circuit breaker switches and one wider residual current breaker with a small round test button"
  - Circuit breaker (MCB): "a single white circuit breaker switch with a toggle lever, close-up"
  - RCCB: "a wider white residual current breaker with a small round test button, close-up"
  - Cable: "two cut electrical cables side by side showing cross-sections: thick with large copper cores, thin with small copper cores"
  - 12V battery: "an ordinary black 12-volt car battery with two terminals, under an open car bonnet"
  - EV battery: "a flat EV battery pack cutaway: grey casing, rows of cylindrical cells"
- Spell out acronyms in the visual ("circuit breaker", not "MCB"); the image model doesn't know acronyms.
- Add `"label"` (2-5 words, correct case, e.g. "MCB", "RCCB Type A", "20-80% sweet spot", "7 kW ≈ 32 A") to every scene that shows a component, a range, a setting or a key number.

### Accuracy on technical topics
- Explain the mechanism correctly in plain words (e.g. an MCB trips on sustained overcurrent or heat in the breaker itself; an RCCB trips on earth leakage).
- Never suggest DIY electrical work or upsizing a breaker. Point to a licensed electrician.
- Uncertain technical claims get `[VERIFY: electrician]`.

### status.md
- `step: script_pack_done`, topic, date, files created

## Then
Run the `energi-claim-lint` skill on all text files and report the result. Do not proceed to any paid generation; ask the operator for script approval.


## Reel type: explainer (default) or product
- **explainer**: knowledge/tips. No charger in frame, no `real_photo` scenes.
- **product**: about Energi Elite's install, the E1, or why choose us. Use 3-5 `real_photo` scenes for every beat that shows the E1, a wall charger, a plug/holster or installation work:
  `{"id": 7, "type": "real_photo", "photo": "e1-carport-closeup-01.jpg", "vo_text": "...", "label": "Dedicated isolator"}`
  - `photo` must be a file listed in `C:\Users\User\energi-content\assets\e1-photos\photos.md`; pick by its "good for" column; each file at most once.
  - All other scenes stay `generated` (and still never show a charger), last scene `text_card`.
- Write `reel_type: explainer` or `reel_type: product` as the first line of `status.md`.
