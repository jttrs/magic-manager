# `cmd` — Commander 2011

> Per-family memory doc. Read this before answering set-specific questions about
> `cmd` or working on `cmd`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `cmd`
**Family root type:** `commander`
**Family released:** 2011-06-17
**Last audit:** 2026-11-05 via `/characterize-set cmd` (one-at-a-time run — tier decisions pending owner review).

---

> **The first Commander product: five three-colour decks**, three legends
> each. Standalone root, base frame, **all nonfoil** (as in
> [`c13`](c13.md)). Two memorabilia children: the 15 oversized legends
> (`ocmd`) and five foil launch-party legends (`pcmd`) that exist nowhere
> else as foils.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `cmd` | commander | 318 | 2011-06-17 | parent — CN 1–318, alphabetical within colour (basics 299–318) |
| `ocmd` | memorabilia | 15 | 2011-06-17 | oversized foil legends (Animar 181 ~$30, Kaalia 206, Riku 220, …) |
| `pcmd` | memorabilia | 5 | 2011-06-17 | Commander launch-party foils — Basandra 184 (~$35), Edric 196 (~$24), Skullbriar 227 (~$20), Nin 213, Vish Kal 234 (same art, `instore`) |

No token set. `set:cmd+related` covers all three; master-list skips both
memorabilia children by default.

---

## 2. Treatments

All `regular`. No `frame_effects`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| cards (nonfoil) | 318 | `cmd` 1–318 (97 C / 115 U / 92 R / 14 M; Animar 181 ~$34, Grave Pact 85 ~$31, Aura Shards 182 ~$27, Attrition 72 ~$19, Homeward Path 277 ~$16) | `regular` | rarity sub-selectors — ≈ $495 |
| oversized legends | 15 | `ocmd` (foil) | `regular` | memorabilia, off by default |
| launch-party foils | 5 | `pcmd` (foil, regular size) | `regular` | **memorabilia, off by default — but these are real foil cards** (~$96) |

**New art (local check):** 21 prints. Configured `[dupe_foil] cmd = []` (2026-11-08).

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] cmd = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `pcmd` launch-party foils | 5 | **owner's call** — regular-size foils filed as `memorabilia`, so hidden by default; opt in with `mm set master-list cmd --include memorabilia` |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| same CN as `cmd` | `pcmd` | launch party (in-store foil) | Edric, Spymaster of Trest 196 |
| same CN as `cmd` | `ocmd` | oversized | Animar 181 |

---

## 7. Edge cases & gotchas

- **`pcmd` is misfiled for our purposes:** Scryfall types it `memorabilia`,
  but the five cards are tournament-legal, regular-size foils — the only foil
  printings of those legends from this product.
- **No `tcmd`** token set.
- Decks reprinted in [`cma`](cma.md) (Heavenly Inferno) and [`cm2`](cm2.md)
  (Devour for Power).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] cmd = []` — configured 2026-11-08 (enables `mm query missing-set cmd`).
- `config/families.toml` `[[unobtainable.cmd.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.cmd]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Commander Deck ×5 | Commander deck | Counterpunch (Ghave), Devour for Power (The Mimeoplasm), Heavenly Inferno (Kaalia), Mirror Mastery (Riku), Political Puppets (Zedruu) |

**Booster types (for `sealed-value` EV):** none.
