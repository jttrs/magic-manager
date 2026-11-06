# `ima` — Iconic Masters

> Per-family memory doc. Read this before answering set-specific questions about
> `ima` or working on `ima`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `ima`
**Family root type:** `masters`
**Family released:** 2017-11-17
**Last audit:** 2026-11-05 via `/characterize-set ima` (one-at-a-time run — tier decisions pending owner review).

---

> **Masters reprint set built around big iconic creatures** (dragons, angels,
> demons, Eldrazi). All 249 cards are reprints in the base frame, every one in
> both finishes. No promo child, no alt treatments, no basics. Same shape as
> [`a25`](a25.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ima` | masters | 249 | 2017-11-17 | parent — the only card set, CN 1–249 |
| `tima` | token | 7 | 2017-11-17 | tokens |

`set:ima+related` covers both. `masters` isn't a default inventory set type,
but the anchor is always included by `mm set master-list ima`.

---

## 2. Treatments

All `regular`. No `frame_effects`, no `promo_types`, no `full_art`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base (foil + nonfoil) | 249 | `ima` 1–249 (101 C / 80 U / 53 R / 15 M) | `regular` | rarity/base sub-selectors — R+M ≈ $503 nonfoil / $857 foil |
| tokens | 7 | `tima` | `regular` | tokens |

Top cards: Mana Drain 65 (~$56), Archangel of Thune 8 (~$47), Avacyn, Angel of
Hope 11 (~$40), Necropotence 98 (~$39 / $96 foil), Consecrated Sphinx 47
(~$35), Serra Ascendant 31 (~$32), Kokusho 95 (~$28), Sheoldred, Whispering
One 108 (~$23).

**New art:** 11 prints don't share an illustration with any other local
printing (Kokusho 95, Horizon Canopy 240, Spiritmonger 209, Blizzard Specter
194, Malfegor 205, Night of Souls' Betrayal 99, …). The local catalog
undercounts older sets, so treat the count as an upper bound.

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] ima = []` to enable `mm query missing-set ima`.

---

## 3. Chase variants

None.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ima = []` | 0 | **apply** — empty, enables missing-set |

---

## 6. PRM destinations

n/a. No promo child.

---

## 7. Edge cases & gotchas

- **Rarities are re-assigned for the Masters set**; a card's rarity here can
  differ from its original printing.
- No basics; the draft booster has no land slot.
- The whole family is booster-obtainable (no prerelease, Promo Pack or
  buy-a-box prints).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ima.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ima]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters / Booster Box / Case | booster product | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py ima --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$11.38, 99.9% coverage |
