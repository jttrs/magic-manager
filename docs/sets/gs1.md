# `gs1` — Global Series Jiang Yanggu & Mu Yanling

> Per-family memory doc. Read this before answering set-specific questions about
> `gs1` or working on `gs1`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `gs1`
**Family root type:** `duel_deck`
**Family released:** 2018-06-22
**Last audit:** 2026-11-05 via `/characterize-set gs1` (one-at-a-time run — tier decisions pending owner review).

---

> **Two-deck product made for the Chinese market**, built around two new
> Chinese planeswalkers, Mu Yanling and Jiang Yanggu. Standalone root
> (`parent_set_code: null`). Every card uses the base frame. About half of the
> cards (22 of 41, the Mowu token included) were printed here first.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `gs1` | duel_deck | 41 | 2018-06-22 | parent — Mu Yanling deck 1–21 (blue-white), Jiang Yanggu deck 22–40 (red-green), token `T1` Mowu |

No children: the Mowu token lives in the parent set (`T1`, `is_token = 1`),
not in a `t`-prefixed token set. `duel_deck` isn't a default inventory set
type, but the anchor is always included by `mm set master-list gs1`.

---

## 2. Treatments

All `regular`. No `promo_types`, no `full_art` on the cards (the Mowu token is
full-art).

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| planeswalkers (**foil-only**) | 2 | `gs1` 1 Mu Yanling (~$6.70), 22 Jiang Yanggu (~$0.78) | `regular` | mythic-regular |
| deck cards (nonfoil-only) | 38 | `gs1` 2–21, 23–40 (rares: Ancestor Dragon 12 ~$1.47, Rhythmic Water Vortex 18, Screeching Phoenix 30, Journey for the Elixir 36; basics 20, 21, 39, 40) | `regular` | rarity sub-selectors — ≈ $12 nonfoil for all 38 |
| token | 1 | `gs1` `T1` Mowu (double-faced token, foil, `legendary`) | `regular` | token, ~$0.69 |

**First printings here (22):** both planeswalkers, Mowu, and 19 deck cards
(Colorful Feiyi Sparrow 2, Heavenly Qilin 6, Rhythmic Water Vortex 18,
Screeching Phoenix 30, Journey for the Elixir 36, …). Neither walker has been
reprinted; the later Mu Yanling cards (*Sky Dancer* in `war`, *Celestial Wind*
in `m20`) are different cards.

**`promo_types` dupe-foil / stamped signals:** none. Proposed
`[dupe_foil] gs1 = []` to enable `mm query missing-set gs1`.

---

## 3. Chase variants

None. Mu Yanling 1 is the only card above $2.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] gs1 = []` | 0 | **apply** — empty, enables missing-set |
| whole family | 41 | **owner's call** — sold mainly in China; cheap and still findable singly. Kept (default) — pending owner review |

---

## 6. PRM destinations

n/a. No promo child.

---

## 7. Edge cases & gotchas

- **Token inside the parent set:** `T1` Mowu has `set_code = 'gs1'`, so it
  appears in any `set:gs1` selector unless tokens are filtered (missing-set's
  `is_token` chokepoint drops it).
- **`T1` sorts as 0** under a numeric CN cast.
- **MTGJSON files the decks as `type: Planeswalker Deck`** (`JiangYanggu_GS1`,
  `MuYanling_GS1`), so they appear in `mm set precon-list`. The sealed product
  is one `multiple_decks` item, *Global Series Jiang Yanggu and Mu Yanling*.
- The planeswalker cards are foil-only; there is no nonfoil Mu Yanling 1.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.gs1.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.gs1]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Global Series Jiang Yanggu & Mu Yanling | Planeswalker deck ×2 in one box (MTGJSON `multiple_decks`) | Mu Yanling 1–21, Jiang Yanggu 22–40 + Mowu token |

**Booster types (for `sealed-value` EV):** none.
