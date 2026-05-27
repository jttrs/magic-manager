---
name: scryfall-search
description: Search Magic the Gathering cards on Scryfall. Translate natural-language card requests ("cheap blue counterspells legal in modern", "red dragons with haste under $5") into Scryfall search syntax, run the query against the public Scryfall API, and return both the raw query (for copy/paste) and a concise summary of matching cards. Use this skill whenever the user asks to find, search, or look up MTG cards.
---

# Scryfall Search

Search Scryfall for Magic the Gathering cards by translating the user's request into Scryfall's search syntax, calling the public API, and returning a concise summary plus the raw query.

## Workflow

1. **Translate** the user's natural-language request into a Scryfall query string using the syntax reference below. Be precise — do not invent operators that aren't documented.
2. **Run** the query against the API: `GET https://api.scryfall.com/cards/search` with the query in the `q` parameter.
3. **Report** back to the user with:
   - The exact Scryfall query you used (so they can paste it into https://scryfall.com)
   - The total number of matching cards
   - A short list of top results (name · mana cost · type · set · oracle snippet)
   - The Scryfall web URL for the search

## Running queries — use `mm scryfall` first

For interactive / ad-hoc queries, **prefer `mm scryfall '<query>'` from the project root**:

```bash
uv run mm scryfall '!"Cloud, Ex-SOLDIER" g:fin' --first 10
```

It's a thin wrapper over the rate-limited `scryfall.sh` script, formats results as a tight table including the computed `treatment` keyword (so you can immediately see how each printing differs), and **never needs Python heredocs or quote-escaping tricks** — apostrophes in card names just work.

Useful flags:

- `--first N` — show at most N results (default 20).
- `--fields col1,col2,...` — pick columns. Available: `set`, `collector_number`, `name`, `rarity`, `treatment`, `full_art`, `border_color`, `frame_effects`, `promo_types`, `security_stamp`, `prices_usd`, `prices_usd_foil`, `scryfall_uri`. Default is `set,collector_number,name,treatment,rarity`.
- `--json` — emit the raw Scryfall JSON instead of the table.

When you need the wrapper directly (e.g. inside another script), call it via the shell:

```bash
.claude/skills/scryfall-search/scryfall.sh search 't:dragon c:r mv<=4 f:modern' order=edhrec
```

Subcommands:
- `search '<query>' [order=edhrec] [unique=cards|prints|art] [dir=asc|desc] [page=N]`
- `named '<exact card name>'`
- `collection [body.json]` — POST to `/cards/collection` for bulk identifier lookup (up to 75 cards per call). Reads JSON body from stdin or a file path. Body shape: `{"identifiers": [{"name":"Sol Ring"}, {"set":"leb","collector_number":"162"}, ...]}`. Used by `magic_manager.parsers.resolve()`.
- `raw '/some/path' 'already=encoded&query=string'` — for endpoints not covered above (sets, rulings, etc.)

**Always go through the wrapper.** A PreToolUse hook in this project will block any direct `curl` to `api.scryfall.com`. The wrapper enforces Scryfall's rate limits (500ms between `/cards/*` calls, 100ms otherwise), caches responses for 24h, and refuses to call again for 35s after an HTTP 429. Bypassing it risks a temp/permanent ban of the project's User-Agent.

If the API returns `{"object":"error", ...}` (e.g. zero matches, bad syntax), surface the `details` field to the user verbatim and suggest a fix.

## Custom Python — when the CLI isn't enough

If `mm scryfall` doesn't cover what you need (e.g. complex per-card analysis, comparing fields across many printings), use a **stdin heredoc** rather than `python -c "..."`:

```bash
python3 - <<'PY'
import sys; sys.path.insert(0, 'src')
from magic_manager import scryfall as sf

# Apostrophes, $, backslashes here are all literal because we used 'PY'
# (single-quoted heredoc, no shell expansion).
for c in sf.search('!"Cloud, Ex-SOLDIER" g:fin', unique='prints'):
    print(c['set'], c['collector_number'], c['name'], c.get('frame_effects'))
PY
```

**Never write `python -c "..."` with embedded quote-bearing data.** Card names contain `'` (Atraxa, Praetors' Voice; April O'Neil), Scryfall query syntax uses `"..."` for exact-name matching (`!"Card Name"`), and shell escaping of those inside a `-c` argument breaks regularly. The heredoc form sidesteps all of it.

If the script grows past a few lines, lift it into a real `.py` file under `src/magic_manager/` (or the equivalent project location) — but for one-shot research, the heredoc is correct.

## Rate limit and etiquette

Scryfall's published limits (https://scryfall.com/docs/api/rate-limits):
- `/cards/search`, `/cards/named`, `/cards/random`, `/cards/collection`: **2/sec → 500ms minimum gap**.
- All other endpoints: 10/sec → 100ms minimum gap.
- `*.scryfall.io` (image origin) has no rate limit.
- HTTP 429 = 30s lockout; **ignoring 429s leads to a temp or permanent ban**.
- They explicitly require caching downloaded data **for at least 24h**, and ask that bulk lookups use the daily bulk-data files instead of the search endpoint.
- Required headers: app-specific `User-Agent` (not the curl default), and an `Accept` header.

The wrapper handles all of this. Don't reach for raw `curl`.

## Output format

Always show the user:

1. **Query:** the exact Scryfall syntax string in a code block.
2. **Web link:** `https://scryfall.com/search?q=<url-encoded-query>`
3. **Summary:** total count + top 10–15 results as a compact list.

Keep the summary tight. The user can click the web link for the full visual results.

## Scryfall search syntax reference

This is the authoritative cheat sheet — do not invent operators not listed here.

### Colors and color identity
- `c:` / `color:` — card color. Letters `w u b r g`, names (`blue`), or nicknames (`azorius`, `bant`, `esper`, `quandrix`, `chaos` etc.). `c` or `colorless` for colorless, `m` or `multicolor` for multicolor.
- `id:` / `identity:` — color identity (for Commander).
- Comparisons: `c>=uw`, `c=2` (cards exactly 2 colors), `id<=esper`.
- `has:indicator` — has a color indicator.

### Card types
- `t:` / `type:` — supertype, type, or subtype. Partial words OK. `t:legendary t:goblin`, `-t:creature`.

### Card text
- `o:` / `oracle:` — oracle text. Use `~` as placeholder for card name. Quote phrases: `o:"~ enters tapped"`.
- `fo:` / `fulloracle:` — includes reminder text.
- `kw:` / `keyword:` — specific keyword ability (e.g. `kw:flying`).

### Mana cost & value
- `m:` / `mana:` — exact symbols. `m:2WW`, `m:{R/P}`, `m>3WU`.
- `mv:` / `manavalue:` / `cmc:` — numeric. `mv=5`, `mv<=3`, `manavalue:even`, `manavalue:odd`.
- `is:hybrid`, `is:phyrexian`.
- `devotion:{u/b}{u/b}{u/b}` — devotion contribution.
- `produces:wu` — mana the card can produce.

### Power / toughness / loyalty
- `pow:` / `power:`, `tou:` / `toughness:`, `pt:` / `powtou:` (sum), `loy:` / `loyalty:`.
- Compare to numbers or each other: `pow>=8`, `pow>tou`.

### Multi-faced
- `is:split`, `is:flip`, `is:transform` (alias `is:tdfc`), `is:meld`, `is:leveler`, `is:dfc`, `is:mdfc`, `is:meldpart`, `is:meldresult`.

### Spells / permanents / effects
- `is:spell`, `is:permanent`, `is:historic`, `is:party`, `is:outlaw`, `is:modal`, `is:vanilla`, `is:frenchvanilla`, `is:bear`, `is:manland`.

### Extras / funny
- `is:funny`, `t:scheme`, `t:plane`, `t:phenomenon`, `t:vanguard`. Include hidden cards with `include:extras`.

### Rarity
- `r:` / `rarity:` — `common`, `uncommon`, `rare`, `mythic`, `special`, `bonus`. Comparisons: `r>=r`.
- `new:rarity` — first time printed at this rarity.
- `in:rare` — has ever been printed at rare.
- `is:newinpauper`.

### Sets / blocks / collector numbers
- `s:` / `e:` / `set:` / `edition:` — set code (e.g. `e:war`).
- `cn:` / `number:` — collector number, supports `cn>50`.
- `b:` / `block:` — block (use any set code from the block).
- `g:` / `group:` — sets directly tied to a release (parent/sibling/child).
- `in:lea` — passed through that set.
- `st:` — set type: `core`, `expansion`, `draftinnovation`, `masters`, `funny`, `commander`, `duel_deck`, `from_the_vault`, `spellbook`, `premium_deck`, `alchemy`, `archenemy`, `masterpiece`, `memorabilia`, `planechase`, `promo`, `starter`, `token`, `treasure_chest`, `vanguard`.
- Booster/promo: `is:booster`, `is:planeswalker_deck`, `is:league`, `is:buyabox`, `is:giftbox`, `is:intro_pack`, `is:gameday`, `is:prerelease`, `is:release`, `is:fnm`, `is:judge_gift`, `is:arena_league`, `is:player_rewards`, `is:media_insert`, `is:instore`, `is:convention`, `is:set_promo`, `is:datestamped`.

### Cubes
- `cube:` — `arena`, `grixis`, `legacy`, `chuck`, `twisted`, `april`, `protour`, `uncommon`, `modern`, `amaz`, `tinkerer`, `livethedream`, `chromatic`, `vintage`, `apcube`.

### Format legality
- `f:` / `format:` — `standard`, `future`, `historic`, `timeless`, `gladiator`, `pioneer`, `modern`, `legacy`, `pauper`, `vintage`, `penny`, `commander`, `oathbreaker`, `standardbrawl`, `brawl`, `alchemy`, `paupercommander`, `duel`, `oldschool`, `premodern`, `predh`, `tlr`.
- `banned:legacy`, `restricted:vintage`.
- `is:commander`, `is:brawler`, `is:companion`, `is:duelcommander`, `is:oathbreaker`, `is:partner`, `is:gamechanger`, `is:reserved`.
- `edhrecrank` / `edhrec` — numeric (lower = more popular).

### Prices
- `usd`, `eur`, `tix` — numeric comparisons (`usd<5`, `tix>15`).
- `cheapest:usd|eur|tix` — find the cheapest print.

### Artist / flavor / watermark
- `a:` / `artist:` (e.g. `a:"proce"`), `artists>1`.
- `ft:` / `flavor:`.
- `wm:` / `watermark:`, `has:watermark`.
- `new:art`, `new:artist`, `new:flavor`, `illustrations>1`.

### Border / frame / foil / resolution
- `border:black|white|silver|borderless`.
- `frame:1993|1997|2003|2015|future`, `frame:legendary|colorshifted|tombstone|enchantment`.
- `is:full` (full art), `is:hires`, `new:frame`.
- `is:foil`, `is:nonfoil`, `is:etched`, `is:glossy`.
- `stamp:oval|acorn|triangle|arena`.
- `is:universesbeyond` / `not:universesbeyond`, `is:default`, `is:atypical`.

### Games / promos / spotlights
- `game:paper|mtgo|arena`, `in:paper|mtgo|arena`.
- `is:digital`, `is:alchemy`, `is:rebalanced`, `is:promo`, `is:spotlight`, `is:scryfallpreview`.

### Year / date
- `year=2026`, `year<=1994`.
- `date>=2015-08-18`, `date>ori` (use a set code as a date), `date>now`.

### Tagger tags
- `art:` / `atag:` / `arttag:` — illustration content (e.g. `art:squirrel`).
- `function:` / `otag:` / `oracletag:` — functional tags (e.g. `function:removal`).

### Reprints
- `is:reprint`, `not:reprint`, `is:unique`.
- `prints=N`, `sets=N`, `paperprints=N`, `papersets=N`.

### Languages
- `lang:` / `language:` — `english`, `japanese`, `ko`, `ru`, `zhs`, etc., or `lang:any`.
- `new:language`, `in:ru` (has ever been printed in Russian).

### Land shortcuts
`is:bikeland` (cycleland), `is:bondland` (battlebondland), `is:bounceland` (karoo), `is:canopyland`, `is:checkland`, `is:creatureland`, `is:dual`, `is:fastland`, `is:fetchland`, `is:filterland`, `is:gainland`, `is:painland`, `is:pathway`, `is:scryland`, `is:surveilland`, `is:shadowland` (snarl), `is:shockland`, `is:slowland`, `is:storageland`, `is:tangoland` (battleland), `is:tricycleland` (triome), `is:triland`. Also `is:masterpiece`.

### Negation
- Prefix any operator with `-` to negate. `-t:creature`, `-c:red`.
- `not:` is an alias for `-is:`.

### Regex
- Use `//` instead of quotes for `t:`, `o:`, `ft:`, `name:` to enable regex.
- Supports `.*?`, `(a|b)`, `[ab]`, `\d`, `\w`, `\b`, `^`, `$`, lookahead `(?!...)`. Escape forward slashes inside as `\/`.
- Example: `o:/^{T}:/` (creatures that tap with no other payment).

### Exact name
- Prefix with `!` for exact card-name match: `!fire`, `!"sift through sands"`.

### Boolean / grouping
- All terms are AND by default.
- `or` / `OR` between terms for disjunction: `t:fish or t:bird`.
- Parentheses for grouping: `t:legendary (t:goblin or t:elf)`.

### Display / sort (work in API too)
- `unique:cards|prints|art`.
- `display:grid|checklist|full|text` (web only — ignore for API).
- `order:name|cmc|power|toughness|set|usd|tix|eur|rarity|color|released|spoiled|edhrec|penny|review|artist`.
- `direction:asc|desc` (or `dir=` as URL param).
- `prefer:oldest|newest|usd-low|usd-high|promo|default|atypical|universesbeyond|notuniversesbeyond` (also `prefer:ub`, `prefer:notub`).

## Examples of natural language → query

| Request | Query |
|---|---|
| "cheap blue counterspells legal in modern" | `t:instant o:counter c:u f:modern usd<2 order:edhrec` |
| "red dragons with haste under $5" | `t:dragon c:r kw:haste usd<5 order:edhrec` |
| "white removal spells in pauper" | `c:w f:pauper function:removal order:edhrec` |
| "every printing of Lightning Bolt" | `!"Lightning Bolt" unique:prints order:released` |
| "commanders that care about artifacts" | `is:commander o:artifact order:edhrec` |
| "fetch lands legal in modern" | `is:fetchland f:modern` |
| "5+ power creatures for under a dollar" | `t:creature pow>=5 usd<1 order:edhrec` |
| "izzet (UR) instants and sorceries with cmc 2" | `id:ur (t:instant or t:sorcery) mv=2 order:edhrec` |
