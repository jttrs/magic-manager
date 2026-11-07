# `ust` — Unstable

> Per-family memory doc. Read this before answering set-specific questions about
> `ust` or working on `ust`-related commands. When new peculiarities emerge in
> chat, update the appropriate section here so the knowledge outlives the
> session. See `CLAUDE.md` § "Per-set knowledge" for the full convention.

**Anchor code:** `ust`
**Family root type:** `funny`
**Family released:** 2017-12-08
**Last audit:** 2026-11-05 via `/characterize-set ust` (one-at-a-time run — tier decisions pending owner review).

---

> **Silver-bordered Un-set** with 13 lettered variant groups (65 prints),
> 45 borderless Contraptions and 5 full-art borderless basics. Everything comes
> in both finishes. Standalone root. Only Steamflogger Boss 93 is
> black-bordered.

## 1. Family map

| Code | `set_type` | Cards | Released | Notes |
|---|---|---:|---|---|
| `ust` | funny | 268 | 2017-12-08 | parent — 203 numbered cards + 65 lettered variants (CN 1–216); Contraptions 167–211; full-art basics 212–216 |
| `pust` | promo | 1 | 2017-12-08 | Earl of Squirrel 108, Draft Weekend foil |
| `tust` | token | 20 | 2017-12-08 | tokens — 10 silver-bordered, 10 black-bordered double-sided; all foil-only |

`set:ust+related` covers all three. `funny` isn't a default inventory set type,
but the anchor is always included by `mm set master-list ust`.

---

## 2. Treatments

Survey (`survey_treatment_signature.py UST`): every print computes `regular`
except the 5 full-art basics (`fa`). No `frame_effects`; the only
`promo_types` is `draftweekend` on `pust` 108.

| Class | Count | CN band | Computed treatment | Preferred-filter disposition |
|---|---:|---|---|---|
| silver-bordered cards | 217 | `ust` 1–166 (incl. the 65 lettered variants) | `regular` | rarity sub-selectors |
| black-bordered | 1 | `ust` 93 Steamflogger Boss | `regular` | the one tournament-legal-border card |
| Contraptions (borderless) | 45 | `ust` 167–211 (Pet Project 198 ~$9 foil) | `regular` | rarity sub-selectors; borderless but no `inverted` frame, so `regular` |
| full-art basics (borderless) | 5 | `ust` 212–216 | `fa` | **kept by default** — the only basics; ~$15 nonfoil / **~$279 foil** (Island 213 foil ~$86) |
| tokens | 20 | `tust` | `regular` | tokens |

Rarity totals (`ust`): 102 C / 90 U / 61 R / 15 M. R+M ≈ $55 nonfoil / $197
foil (Everythingamajig 147a ~$5, Earl of Squirrel 108 ~$4 / $21, Urza,
Academy Headmaster 136 ~$2.50 / $32).

**Lettered variant groups (13 groups, 65 prints):**

| Kind | Groups (CN) | What differs |
|---|---|---|
| **art variants** — same rules, different art | Amateur Auteur 3 (a–d), Extremely Slow Zombie 54 (a–d), Target Minotaur 98 (a–d), Beast in Show 103 (a–d), Secret Base 165 (a–e) | one `oracle_id`, several `illustration_id`s |
| **same rules, same art** | Novellamental 41 (a–d) | one `oracle_id`, one `illustration_id` — the four differ only in printed flavor text |
| **rules variants** — same art, different text | Knight of the Kitchen Sink 12, Garbage Elemental 82, Ineffable Blessing 113, Everythingamajig 147 (each a–f), Killbots 145 (a–d, four different names) | one `illustration_id`, several `oracle_id`s |
| **both** | Very Cryptic Command 49 (a–f), Sly Spy 67 (a–f) | 6 `oracle_id`s, 2 arts |

Every lettered print is a distinct printing, so missing-set lists them all.

**`promo_types` dupe-foil / stamped signals:** none that dupe. Proposed
`[dupe_foil] ust = []` to enable `mm query missing-set ust`.

**Full-art convention:** only the 5 basics.

---

## 3. Chase variants

The foil full-art basics (212–216, ~$44–86 each) are the set's priciest prints.

---

## 4. Scenes / posters / panoramas

None.

---

## 5. Unobtainable rules

None configured yet (proposals pending owner review).

| Tier | Prints | Recommendation |
|---|---:|---|
| `[dupe_foil] ust = []` | 0 | **apply** — empty, enables missing-set |
| lettered variants | 65 | keep — each is its own printing; the owner may prefer to collect one per group |
| `pust` 108 Draft Weekend | 1 | **owner's call** — same as other families' event promos |

---

## 6. PRM destinations

| Physical CN pattern | Scryfall set | Channel | Example |
|---|---|---|---|
| `108` | `pust` | Draft Weekend (foil) | Earl of Squirrel |

---

## 7. Edge cases & gotchas

- **Lettered CNs sort as their number** under a numeric cast; group by
  `cast(collector_number as int)` to collapse a variant group.
- **Variants aren't one card:** rules variants have different `oracle_id`s, so
  oracle-grain tools (EDHREC, `lowest_price_by_oracle`) treat Very Cryptic
  Command 49a–f as six cards; art variants collapse to one.
- **The Killbots** are one variant group with four names (Curious, Delighted,
  Despondent, Enraged Killbot).
- **Contraptions** are borderless but compute `regular`; a `b` rule won't touch
  them.
- **Token set mixes borders:** half of `tust` is silver-bordered, half
  black-bordered double-sided. All 20 tokens are foil-only.

---

## 8. Code refs

- `config/families.toml` `[dupe_foil]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[unobtainable.ust.rules]]` — None configured yet (proposals pending owner review).
- `config/families.toml` `[[scenes.ust]]` — none.

---

## 9. Product types

| Product | Archetype (→ [`../product-types.md`](../product-types.md)) | Family-specific detail |
|---|---|---|
| Draft boosters / Booster Box / Case | booster product | — |
| 3 Booster Draft Pack | limited aid tool (MTGJSON `limited_aid_tool` / `draft_set`) | — |

**Booster types (for `sealed-value` EV)** — `scripts/sealed_value.py ust --list-boosters` (2026-11-05):

| Booster type | Notes |
|---|---|
| `draft` | EV ~$7.15, 99.9% coverage |
