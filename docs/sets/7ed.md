# `7ed` — Seventh Edition

> Per-family memory doc. Read this before answering set-specific questions about
> `7ed` or working on `7ed`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `7ed`
**Family root type:** `core`
**Family released:** 2001-04-11
**Last audit:** 2026-11-06 via `/characterize-set 7ed` (one-at-a-time run — tier decisions pending owner review).

---

> **First core set with foils, and the first fully finish-split set:** every card is a nonfoil print at `N` plus a foil print at `N★` (700 local rows = 350 cards × 2). 349 of the 350 pairs share art; **Relentless Assault 214★ has its own art**. No mythics, no promo or token sets. Eight Simplified-Chinese alt-art prints (`Ns` / `N★s`) are on Scryfall but not local.**

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `7ed` | core | 700 (708 on Scryfall) | 2001-04-11 | parent — nonfoil 1–350 + foil 1★–350★; 20 basics in 328–349 |

No children. The 8 Scryfall-only rows are `schinesealtart` prints (`lang = zhs`): Drudge Skeletons 130s, Raise Dead 157s, Scathe Zombies 161s, Charcoal Diamond 289s, each also as `N★s`. `mm set sync` asks for `lang:en`, so they're never local.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| nonfoil | 350 | `7ed` 1–350 (130 C / 110 U / 110 R; 20 basics) | `regular` | rarity/base sub-selectors — R ≈ $368 (City of Brass 327 ~$31, Birds of Paradise 231 ~$23, Final Fortune 182 ~$18) |
| foil `N★` | 350 | `7ed` 1★–350★ (same rarities) | `regular` | **same art** as `N` except 214★ — R ≈ $19,850 (Birds of Paradise 231★ ~$3981, Final Fortune 182★ ~$1889, City of Brass 327★ ~$1500, Karplusan Forest 336★ ~$1200, Underground River 350★ ~$896) |
| alt-art foil | 1 | `7ed` 214★ Relentless Assault (~$120) | `regular` | **different art** from nonfoil 214 (~$4.45) |

**`promo_types`:** none on any print. The foil `N★` rows carry no dupe signal, so missing-set lists both halves of every card unless a finish-split rule is added. No fancy-foil sheet →
proposed `[dupe_foil] 7ed = []` to enable `mm query missing-set 7ed`.

---

## 3–4.

Foil rares are the chase: foil Birds of Paradise 231★ (~$3981) alone is ~20% of the foil rare total. No scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] 7ed = []` | 0 | **apply** — empty, enables missing-set |
| foil `N★` same-art half | 349 | **owner's call** — part of the finish-split decision ([`8ed`](8ed.md), [`9ed`](9ed.md), [`10e`](10e.md)); one card per name+art regardless of finish |
| 214★ Relentless Assault | 1 | keep — unique art |
| `zhs` alt-art `Ns` | 8 (0 local) | **owner's call** — Chinese-only, not syncable |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `N★` | `7ed` | booster foil | Birds of Paradise 231★ |
| `Ns` / `N★s` | `7ed` | Simplified-Chinese alt art (`schinesealtart`) | Drudge Skeletons 130s |

---

## 7. Edge cases & gotchas

- **The finish split starts here.** Seventh Edition was the first core set with foils, and Scryfall models it the way it models [`8ed`](8ed.md) and [`9ed`](9ed.md): two CNs per card, one finish each.
- **214★ is the one alt-art foil** — a CN-only rule (`★` = same art) would be wrong for it.
- **Foil rares are ~54× nonfoil** by total value.
- **`7ed` has no prerelease or token set.**
- MTGJSON: 5 Theme Decks (Armada, Bomber, Decay, Infestation, Way Wild), Two-Player Starter (decks `Gold Deck` / `Silver Deck`, typed `Starter Deck`, plus `Advanced Pack`s), a `Welcome Booster` sampler, MTGO Redemption.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.7ed.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.7ed]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters | booster product | — |
| Theme Decks ×5 | theme deck | not in `PRECON_MODERN_TYPES` |
| Two-Player Starter | starter set (`multiple_decks` / `two_player_starter`) | Gold + Silver decks |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py 7ed --list-boosters` (2026-11-06): `draft` EV ~$13.76.
