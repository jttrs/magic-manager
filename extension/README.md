# magic-manager companion (Chrome extension)

Reads your Mana Pool cart, your open store tabs (Deals) and Moxfield decks in **your own browser**.
Each time, it shows you exactly what it would send and waits for you to press Send. Plain
JavaScript, no dependencies, no build step: what you see here is what runs.

- Install, pair and use: [`docs/browser-companion.md`](../docs/browser-companion.md)
- What it can and can't do, and why: [`docs/browser-companion-security.md`](../docs/browser-companion-security.md)
- A site changed and a read broke: `.claude/skills/scrape-doctor/SKILL.md`

`src/stores.js` and the manifest's permission lists are generated from `config/vendors.toml` by
`uv run python scripts/build_extension.py`. Don't edit them by hand.
