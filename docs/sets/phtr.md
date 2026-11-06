# `phtr` — 2016 Heroes of the Realm

> Per-family memory doc. Read this before answering set-specific questions about
> `phtr` or working on `phtr`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `phtr`
**Family root type:** `funny`
**Family released:** 2017-09-20
**Last audit:** 2026-11-05 via `/characterize-set phtr` (one-at-a-time run — tier decisions pending owner review).

---

> **Special product, not a retail set.** The first year of WotC's annual
> *Heroes of the Realm* tribute cards. Standalone (`parent_set_code: null`).
> Same shape as [`ph17`](ph17.md), [`ph18`](ph18.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `phtr` | funny | 3 | 2017-09-20 | parent — the only set, CN 1–3 |

No children.

---

## 2. Treatments

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base (nonfoil-only, all mythic) | 3 | `phtr` 1–3 | `regular` | `mythic-regular` |

No `promo_types`, no foils, no `full_art`, no prices.

| CN | Name |
|---|---|
| 1 | Chandra, Gremlin Wrangler |
| 2 | Dungeon Master |
| 3 | Nira, Hellkite Duelist |

No MTGJSON deck or sealed product.

---

## 3. Chase variants

None.

---

## 4. Scenes / posters / panoramas

n/a.

---

## 5. Unobtainable rules

None configured. **Whole-family obtainability (pending owner review):** never
sold at retail, unpriced on Scryfall; a missing-set run lists 3 unpriced
mythics. Track only if collecting Heroes of the Realm deliberately.

---

## 6. PRM destinations

n/a.

---

## 7. Edge cases & gotchas

- **Name-year offset:** "2016" released 2017-09-20 (as with `ph17`/`ph18`).
- **Code breaks the pattern:** `phtr`, not `ph16`.
- No Scryfall prices, so value-based selectors (`value>=`) never match.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.phtr.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.phtr]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Heroes of the Realm 2016 cards | n/a — special non-retail distribution | 3 single cards |

**Booster types (for `sealed-value` EV):** none.
