# `leg` — Legends

> Per-family memory doc. Read this before answering set-specific questions about
> `leg` or working on `leg`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `leg`
**Family root type:** `expansion`
**Family released:** 1994-06-01
**Last audit:** 2026-11-06 via `/characterize-set leg` (one-at-a-time run — tier decisions pending owner review).

---

> **Old-border expansion, nonfoil only, no basics, one art per card.** 310 cards. The most valuable rare slot of the early sets (rares ≈ $14,144).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `leg` | expansion | 310 | 1994-06-01 | parent — CN 1–310 |

No children.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base | 310 | `leg` 1–310 (75 C / 114 U / 121 R) | `regular` | rarity/base sub-selectors — R ≈ $14,144 (The Tabernacle at Pendrell Vale 307 ~$3620, Chains of Mephistopheles 91 ~$1260, Moat 28 ~$936, The Abyss 120 ~$775, Nether Void 113 ~$674, All Hallow's Eve 88 ~$551); U ≈ $1283 (Mana Drain 65 ~$239, Sylvan Library 207 ~$187) |

**`promo_types`:** none. No fancy-foil sheet →
proposed `[dupe_foil] leg = []` to enable `mm query missing-set leg`.

---

## 3–4.

The Tabernacle at Pendrell Vale 307 (~$3620). Valuable uncommons (Mana Drain, Sylvan Library) are invisible to rare/mythic sub-selectors. No scenes.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] leg = []` | 0 | **apply** — empty, enables missing-set |

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **No foils, no basics.** MTGJSON lists no decks or sealed products besides boosters.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.leg.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.leg]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py leg --list-boosters` (2026-11-06): `default` EV ~$167.34.
