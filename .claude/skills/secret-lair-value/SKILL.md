---
name: secret-lair-value
description: "Deterministic markdown table of the most recent N Secret Lair drops by release date (newest first), each valued sealed vs the cards inside — the drop's sealed market price (TCGplayer), its cards PLUS its bonus card at their exact printings, and each of those cards at its cheapest printing anywhere, with the gap (sealed − exact cards). Regular edition by default, `--foil` for the Foil Editions. Same engine as the web Market → Secret Lair view. Triggers: \"/secret-lair-value\", \"value of recent Secret Lairs\", \"how much are the latest Secret Lair drops worth\", \"recent SLD drop values\", \"newest Secret Lairs value\", \"which Secret Lairs are a good deal\", \"Secret Lair drop price table\"."
---

# Secret Lair Value

Deterministic, script-driven value table. Claude invokes `scripts/secret_lair_value.py [N] [--foil]` and relays the script's stdout markdown block verbatim into chat, surfacing the stderr summary line briefly beneath. No inline computation — the script (a thin driver over `magic_manager.sld_market`) is the single source of truth. For browsing, filtering and watching drops, point the user at the web app: **Market → Secret Lair**.

## When to use

- "What are the recent Secret Lair drops worth?" / "which recent Secret Lairs sell under their cards?"

**Don't** use for:
- One named drop — that's [[sealed-value]] (`scripts/sealed_value.py sld "<drop>"`), or the web inspector.
- What the user OWNS — that's [[inventory-query]] or [[set-status]].
- Adding SLD cards to inventory — that's [[bulk-add]].

## The canonical recipe

```bash
uv run python scripts/secret_lair_value.py [N] [--foil]
```

`N` defaults to 10. `--limit N` also works and wins if both are given. Relay the whole stdout block verbatim.

## Output shape

```
## Secret Lair Drop value — 10 newest, regular edition

| Drop | Release | Cards | Sealed mkt | Exact cards | Cheapest cards | Gap |
|---|---|---:|---:|---:|---:|---:|
| [Artist Series: Ian Miller](https://scryfall.com/search?…) | 2026-09-01 | 5 | $43.06 | $89.88 | $29.91 | −$46.82 (−52%) |
```

- **Sealed mkt** — the drop's sealed product (that edition) on the market (`—` until TCGplayer lists it).
- **Exact cards** — the drop's cards plus its bonus card at their exact printings (a random bonus pack counts at its expected value).
- **Cheapest cards** — each of those cards at its cheapest printing anywhere (local prices).
- **Gap** — sealed − exact cards; negative ⇒ the sealed drop costs less than its cards.

## Determinism

- Drops sort by release date descending, name ascending; base + `… Foil Edition` merge into one drop (`sld.recent_drops`).
- Each row is `market.product_cost(kind='sld')` — the same figures the web app and Deals show. Prices are local-first (a missing `sld` sync is filled; stale prices are used as-is).
- A drop without the requested edition is skipped; a drop that can't be valued renders an `error:` cell, never crashes.

## Cross-references

- `scripts/secret_lair_value.py` — the driver. `src/magic_manager/sld_market.py` — the engine (`recent`, `value`, `gap`, `survey`).
- `src/magic_manager/market.py` — `product_cost` / `_sld_cost` (bonus card via the drop's MTGJSON sealed product).
