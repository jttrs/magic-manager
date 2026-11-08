# `atq` — Antiquities

> Per-family memory doc. Read this before answering set-specific questions about
> `atq` or working on `atq`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `atq`
**Family root type:** `expansion`
**Family released:** 1994-03-04
**Last audit:** 2026-11-06 via `/characterize-set atq` (one-at-a-time run — tier decisions pending owner review).

---

> **Old-border artifact expansion, nonfoil only, no basics.** Five lands come in **four arts each** (`80a`–`85d`), so 85 cards are 100 prints. Two English `N†` variation prints (Atog 23†, Tawnos's Weaponry 70†) are on Scryfall but not local.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `atq` | expansion | 100 (102 on Scryfall) | 1994-03-04 | parent — CN 1–85; Mishra's Factory, Strip Mine, Urza's Mine / Power Plant / Tower at `80a`–`85d` |

No children. The two Scryfall-only rows are `variation` prints Atog `23†` (unpriced) and Tawnos's Weaponry `70†` (~$2.28): Scryfall's search hides variations, so `mm set sync` never fetches them.

---

## 2. Treatments

Every print computes `regular`.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| single-art cards | 80 | `atq` 1–79, 81 (25 C / 35 U / 20 R) | `regular` | rarity/base sub-selectors — R ≈ $8897 total (Mishra's Workshop 81 ~$3925, Candelabra of Tawnos 43 ~$2750, Triskelion 73 ~$173); U ≈ $1369 (Transmute Artifact 14 ~$424, Power Artifact 11 ~$175) |
| four-art lands | 20 | `atq` 80a–85d | `regular` | **different art** per letter; **rarity varies by art** (Mishra's Factory 80a uncommon, 80b–d rare) — 80d ~$633, 80c ~$220, 80b ~$201, 80a ~$113 |

**`promo_types`:** none. No fancy-foil sheet →
configured `[dupe_foil] atq = []` (2026-11-08) to enable `mm query missing-set atq`.

---

## 3–4.

Mishra's Workshop 81 (~$3925), Candelabra of Tawnos 43 (~$2750). No scenes.

---

## 5. Unobtainable rules

No rule is active.

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] atq = []` | 0 | **applied 2026-11-08** — empty, enables missing-set |
| `variation` `N†` | 2 (0 local) | **owner's call** — English prints Scryfall hides from search; needs a sync fix (`include:variations` or `is:variation`) |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `80a`–`85d` | `atq` | land art variants | Mishra's Factory 80d |
| `N†` | `atq` | variation print (not synced) | Atog 23† |

---

## 7. Edge cases & gotchas

- **`a`–`d` CNs are separate arts** for the five lands; their prices differ a lot by art (Mishra's Factory 80d ~$633 vs 80a ~$113).
- **Rarity differs between arts of one card** (Strip Mine 82a uncommon / 82b–d rare; Urza's Tower 85a common / 85b–d uncommon), so a rarity filter keeps some arts of a land and drops others.
- **Variation prints are never synced** (see family map).
- **No foils, no basics.** MTGJSON lists no decks or sealed products besides boosters.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] atq = []` — configured 2026-11-08 (enables `mm query missing-set atq`).
- `config/families.toml` `[[unobtainable.atq.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.atq]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Boosters | booster product | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py atq --list-boosters` (2026-11-06): `default` EV ~$224.66.
