# `cns` — Conspiracy

> Per-family memory doc. Read this before answering set-specific questions about
> `cns` or working on `cns`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here. See `CLAUDE.md` § "Per-set knowledge".

**Anchor code:** `cns`
**Family root type:** `draft_innovation`
**Family released:** 2014-06-06
**Last audit:** 2026-11-05 via `/characterize-set cns` (one-at-a-time run — tier decisions pending owner review).

---

> **The first multiplayer Conspiracy draft set**: 13 Conspiracy cards, new
> draft-matters cards and Legacy/Commander reprints (Exploration, Stifle,
> Reflecting Pool). Base frame, every card in both finishes, no basics.
> Sibling of [`cn2`](cn2.md).

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `cns` | draft_innovation | 210 | 2014-06-06 | parent — CN 1–210 (Conspiracies 1–13) |
| `pcns` | promo | 1 | 2014-06-06 | Magister of Worth `48★` (release promo, own art) |
| `tcns` | token | 9 | 2014-06-06 | tokens |

`draft_innovation` isn't a default inventory set type, but the anchor is
always included by `mm set master-list cns`.

---

## 2. Treatments

Every print computes `regular`. Unlike `cn2`, the Conspiracies carry no `draft`
frame effect.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| base (foil + nonfoil) | 210 | `cns` 1–210 (89 C / 68 U / 43 R / 10 M) | `regular` | rarity/base sub-selectors — R+M ≈ $211 nonfoil / $828 foil (Exploration 164 ~$34, Treasonous Ogre 36 ~$20 / $121, Altar of Dementia 196, Reflecting Pool 210, Phage 120 ~$17 / $66, Misdirection 102 ~$14 / $88) |
| release promo | 1 | `pcns` `48★` Magister of Worth (foil, own art) | `regular` | owner's call |

Foils run high relative to nonfoil (draft-only product, low foil supply).
Configured `[dupe_foil] cns = []` (2026-11-08) to enable `mm query missing-set cns`.

---

## 3–6.

No chase variants or scenes. PRM: `pcns` `48★` (release). Unobtainable rules:
no rule is active; `[dupe_foil] cns = []` —
**applied 2026-11-08**; `pcns` 48★ — owner's call.

---

## 7. Edge cases & gotchas

- **Conspiracies 1–13 are not constructed-legal** but are collectible cards.
- No basics in the set.
- **Foil premium is extreme** (Treasonous Ogre ~6×, Misdirection ~6×).

---

## 8. Code refs

- `config/families.toml` `[dupe_foil] cns = []` — configured 2026-11-08 (enables `mm query missing-set cns`).
- `config/families.toml` `[[unobtainable.cns.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.cns]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters / Booster Box | booster product | conspiracy slot |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py cns --list-boosters` (2026-11-05): `draft` EV ~$10.14, 99.8% coverage.
