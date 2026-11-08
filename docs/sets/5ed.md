# `5ed` — Fifth Edition

> Per-family memory doc. Read this before answering set-specific questions about
> `5ed` or working on `5ed`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `5ed`
**Family root type:** `core`
**Family released:** 1997-03-24
**Last audit:** 2026-11-06 via `/characterize-set 5ed` (one-at-a-time run — tier decisions pending owner review).

---

> **Core set, white border, nonfoil only, no mythics.** 449 prints, 20 basics. No promo or token set. Six Simplified-Chinese alt-art prints (`Ns`) are on Scryfall but not local.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `5ed` | core | 449 (455 on Scryfall) | 1997-03-24 | parent — 1–429 + basics 430–449 |

No children. The 6 Scryfall-only rows are `schinesealtart` prints (`lang = zhs`): Boomerang 75s, Ashes to Ashes 141s, Bog Wraith 147s, Initiates of the Ebon Hand 169s, Mindstab Thrull 178s, Necrite 181s.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 449 | `5ed` 1–449 (165 C / 132 U / 132 R + 20 basics) | `regular` | rarity/base sub-selectors — R ≈ $486 (Mana Vault 388 ~$99, Necropotence 182 ~$37, Sylvan Library 329 ~$29, City of Brass 413 ~$20, Game of Chaos 232 ~$16, Birds of Paradise 280 ~$14) |

**`promo_types`:** none. No fancy-foil sheet →
proposed `[dupe_foil] 5ed = []` to enable `mm query missing-set 5ed`.

---

## 3–4.

No chase variants; no scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] 5ed = []` | 0 | **apply** — empty, enables missing-set |
| `zhs` alt-art `Ns` | 6 (0 local) | **owner's call** — Chinese-only, not syncable |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `Ns` | `5ed` | Simplified-Chinese alt art (`schinesealtart`) | Boomerang 75s |

---

## 7. Edge cases & gotchas

- **5 English `N†` variation prints are not local** (same art): Game of Chaos 232†, Inferno 243†, Ironclaw Curse 244†, Manabarbs 250†, Shivan Dragon 267†. Scryfall's search leaves out `variation` prints, so `mm set sync` never fetches them.
- **Largest core set of the era** (429 non-basic cards).
- **No foils.**
- MTGJSON: Two Player Starter Set (decks `Deck A` / `Deck B`), Starter Deck (a `starter` booster type in `sealed-value`).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.5ed.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.5ed]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Starter Deck | starter deck | — |
| Two Player Starter Set | starter set | Deck A / Deck B |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py 5ed --list-boosters` (2026-11-06): `draft` EV ~$9.56, `starter` ~$37.79.
