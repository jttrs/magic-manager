# Branding exploration: a collector's workbench

**Status:** Exploratory design brief, not an approved name or implementation plan.
**Date:** 2026-10-14.
**Scope:** Product naming and subtle visual branding for magic-manager, with room
to expand from Magic: The Gathering into Pokemon TCG.

No product rename, visual redesign, domain purchase, or trademark clearance has
been approved. The existing [design system](../DESIGN.md) remains authoritative
for the implemented application. This document records the naming discussion,
research, and proposed directions. Sections 1-6 preserve the original Myr
proposal; sections 8-13 record the subsequent naming exploration and commercial
screening. Recommendations are exploratory, not owner selections.

## 1. Brief and recommendation

The desired name should suggest a catalog, collection, or set of tools for
managing cards, decks, purchases, and engagement with the hobby. It should draw
from Magic's history or lore without requiring knowledge of Magic to make sense.
An oblique reference is preferable to a direct character or card name, especially
if the product supports other trading-card games.

The owner's initial examples were:

- **Omnus:** an allusion to Omnath, Locus of All.
- **Goblin Tools:** a familiar creature type and the assembled, disparate nature
  of the toolkit.

The owner reported both names taken. The discussion first explored the Myr
direction, then deliberately broadened into standalone names, treasure and
storage metaphors, recognizable cards, and player terminology. No candidate has
been selected.

**Recommended concept:** a quiet workshop for your collection, not a
robot-themed app. Small, purposeful tools work together in a place where your
hobby belongs.

**Original Myr proposal:** Myrden, with an original folded-metal mark, lamplit
charcoal-and-bone colors, and the existing precise ledger UI.

**Alternative:** Myrworks, if the connected toolkit should lead the identity
rather than the collection's home.

## 2. Research foundation

### Design history and lore

Mark Rosewater's *Design Files: Mirrodin, Part 3* explains that the team wanted a
cute, small artifact creature. The initial design used Gnomes; Brady Dommermuth
proposed a more appropriate creative concept, which became Myr.

In *Myr Myr, Off the Wall*, Rosewater discusses their purpose-driven nature,
replaceable parts, and association with order. These are useful foundations for
a toolkit made from small, specialized functions.

The MTG Wiki describes Myr as metal automatons created by Memnarch, gives the
pronunciation as rhyming with "deer," and connects the name to the Greek root for
ant. Its lore summary also records their original servitor and observation roles
and later Phyrexian adaptations.

The positive brand interpretation is **a useful thing under the collector's
control**, not surveillance, unquestioning obedience, disposability, or
Phyrexian horror.

### Brand interpretations, not canonical claims

| Territory | Inspiration | Product meaning |
|---|---|---|
| Workshop | Specialized mechanisms, repair, assembly | Make your collection work together |
| Habitat | A place for small things to belong | Your hobby has a home |
| Collective | Useful parts supporting one another | One connected system rather than disconnected utilities |
| Keeper | Order, tending, continuity | Know what you have, where it is, and what comes next |
| Material world | Metals, joints, folded forms | A thoughtfully made instrument rather than generic software |

These are proposed branding metaphors. They do not establish canonical Myr
occupations or locations.

## 3. Naming territories

All candidates below are proposed compounds or allusions, not claims that these
names exist in Magic lore. The intended Myr pronunciation is "meer"; a coined
name can still require pronunciation discovery.

| Candidate | Construction and character | Strength | Reservation |
|---|---|---|---|
| **Myrden** | Myr + den; a personal home for the hobby | Compact, warm, broad enough for collecting and tools | Pronunciation is not obvious; existing surname |
| **Myrworks** | Myr + works; a workshop of useful mechanisms | Closest to the Goblin Tools idea; connected toolkit | More technical and industrial |
| **Myrkeep** | Keep track, keep safe, and a keep as a place | Strong cataloging and stewardship association | More fantasy-coded; must not imply guaranteed security or preservation |
| **Myrstead** | A lasting home where things are tended | Provenance, continuity, and a growing collection | Sounds more like a fantasy settlement than software |
| Myrloft | An upstairs hobby room with shelves and a worktable | Light, contemporary, domestic | Close-looking existing MyLOFT library platform |
| Myrwell | A resource to return to; things well tended | Soft, welcoming | Less specific and memorable |
| Myrkin | A family of helpers or collector community | Companion and character potential | Easy to drift into a virtual-pet identity |
| Myrfolio | Myr + folio, with a portfolio association | More explicit cataloging connection | Pronunciation friction and financial-app associations |

**Shortlist:** Myrden, Myrworks, Myrkeep, Myrstead.

Myrden names the place the collector returns to. Myrworks names the machinery
that helps them there. This is the central positioning choice.

### Preliminary collision screening

Public-web searches are an initial filter, not evidence of legal, domain, or
handle availability. Broad searches missed results that narrower searches later
found, so negative results must not be treated as clearance.

| Name | Evidence found during the discussion | Implication |
|---|---|---|
| Myrden | Existing surname, including public figure Barry Myrden | Not an unused word; assess search competition |
| Myrworks, Myrkeep, Myrstead | No obvious exact-name product surfaced in the searches performed | Candidates remain exploratory; availability unknown |
| Myrloft | Similar existing MyLOFT library-resource platform | Deprioritize because of name and subject proximity |
| Bare MYR | Existing MYR restaurant software at myr.io | Avoid depending on the three-letter name alone |
| Myrarium | Indexed result describing a tiny-robot workshop at myrarium.eu; direct retrieval failed | Adjacent-brand collision lead requiring confirmation |

The broader naming pass also found nearby gaming/software usage for Lorewright,
Scrollwright, and Loreloft. Rummageworks had historical business usage. Those
findings reinforce the need to screen narrow exact names and close variants.

## 4. Aesthetic direction

### Proposed design brief

| Dimension | Direction |
|---|---|
| Domain | Trading-card collection and hobby tools |
| Audience and tone | Collectors and players; capable, welcoming, not childish |
| Mood | Warm precision |
| Motion depth | Subtle, purposeful feedback |
| Layout family | Existing ruled guide sheets and dense collection views |
| Reference anchor | A collector's ledger beside a well-made mechanical instrument |

The current "After-Hours Price Guide" already supplies much of this atmosphere:
charcoal chrome, bone work surfaces, restrained amber, fine rules, and tabular
figures. Prefer an evolution of that system over a themed reskin.

### A. Lamplit workbench: recommended

Keep the warm paper, brown-charcoal frame, fine rules, and amber interaction
color. Add identity through the mark, wordmark, and occasional original
illustration rather than decorative machinery.

| Material association | Existing value | Existing role |
|---|---|---|
| Darkened iron | `#16130E` | Light-theme app chrome |
| Warm paper | `#EFE7D6` | Light-theme guide sheet |
| Pale stock | `#F7F2E7` | Light-theme raised paper |
| Brass or lamplight | `#F0A531` | Accent and primary action |
| Dark ink | `#1D1912` | Light-theme text and figures |

These are existing values from DESIGN.md and the token system, not a newly
verified accessibility palette. Preserve the existing light/dark semantic
mapping. Any changed combinations or interactive states require contrast and
state verification before shipping.

The story is a small, warm light in a workshop full of useful things. It does
not depend on Magic card frames, mana colors, or any one game's visual identity.

### B. Silver instrument: alternative

Graphite, pewter, porcelain, and one restrained cool interaction accent. Folded
aluminum and calibrated instruments rather than chrome gradients.

Best suited to Myrworks. This direction would require an intentional revision
of the current amber-only system, not a second accent layered onto it. It risks
losing warmth and approaching familiar developer-tool aesthetics.

### C. Copper cabinet: alternative

Warm off-white, dark umber, muted copper, archive labels, and a sense of orderly
drawers. Best suited to Myrden or Myrkeep.

Borrow its stewardship, not an antique-shop treatment. Avoid parchment,
distressing, ornamental brass, and fantasy-prop styling. Any palette change
would need to preserve the distinction between interaction and danger.

**Preferred combination:** A, with a little of C's sense of care and continuity.
The cards supply the color and spectacle; the interface frames them.

## 5. Logo and wordmark

Develop an original mark that suggests a small mechanism without depicting a
recognizable Myr.

| Concept | Construction | Meaning |
|---|---|---|
| **Folded keeper: preferred** | Two or three folded shapes forming an abstract M, also readable as an open card file | Collection, making, and the name |
| Cabinet companion | Compact enclosure, small aperture, offset card-shaped plane | A useful object with restrained personality |
| Joined pieces | Interlocking plates creating an M through negative space | Separate tools becoming one system |

Start with monochrome and favicon-scale legibility. Color, highlights, and
character are secondary. The product should remain identifiable with no mascot
present.

Avoid literal Myr heads, distinctive creature silhouettes, copied card art,
mana symbols, and five-color orbits. An oblique name paired with recognizable
creature anatomy becomes much less oblique.

Keep Archivo in the application. An original wordmark can add personality
without introducing a fantasy typeface to headings, controls, or numeric tables.
Original geometry and a coined name are not substitutes for legal clearance.

## 6. Subtle application branding

Keep the operational interface literal. Collection, Decks, Explore, Market,
Purchase history, and Background jobs should not become Reservoir, Assembly,
Retriever, or other lore terms.

| Surface | Proposed treatment | Boundary |
|---|---|---|
| Masthead | Small original mark beside the selected name | Do not compete with navigation or crowd mobile controls |
| Typography | Existing Archivo voices and tabular figures | No fantasy font or additional UI typeface |
| Geometry | Folded/joined shapes in the mark and occasional illustration | No rivets, gears, bolts, or clipped corners on every control |
| Empty states | Occasional original helper sorting a card or holding a tray | Clear explanatory copy and action remain primary |
| Motion | Brief save or assembly feedback | No perpetual mascot activity, gear rotation, or simulated work |
| Color | One interaction accent, neutrals carrying the shell | No different Myr metal assigned to every section |

A companion illustration is optional, not the application's interaction model.
It must not celebrate during failed imports, unresolved purchases, or other
errors. Reduced-motion preferences and truthful job status remain essential.

Preserve the current information density, exact card artwork, accessibility,
responsive behavior, and error semantics. Branding must not add friction to
collection work.

## 7. Open decisions and implementation boundary

Before implementation:

- Select the positioning: collection home or connected workshop.
- Select and clear the name, including close variants, domains, handles, and
  relevant trademarks.
- Compare original monochrome logo sketches at masthead and favicon sizes.
- Decide whether the existing palette stays intact or is intentionally revised.
- Evaluate the identity beside both Magic and Pokemon card imagery.

If approved, update DESIGN.md and the directly affected brand surfaces together.
Palette changes belong in the existing `web/tokens/` source of truth, not
per-component colors. Verify light/dark states, mobile masthead fit, and
legibility before treating a visual proposal as implemented.

This brief does not authorize code changes or a rename of the repository, CLI,
database, package, or application.

## 8. Positioning beyond Myr

**Working product description:** a collector's workbench. The product connects
what you own, how you acquired it, what you can build, what you are missing, and
what is worth exploring or buying next. It is broader than inventory software,
a deckbuilder, or a price tracker.

The later conversation explored three complementary promises:

| Promise | Meaning | Naming territory |
|---|---|---|
| Your hobby has a home | Personal, well-tended collection | Den, keep, cabinet, strongbox |
| Your hobby comes together | Connected information and tools across games | Accord, omnibus, convergence |
| Find possibilities in what you own | Search, discovery, building, informed acquisition | Tutor, toolbox, wishboard, hoard and seek |

### Omnus: appealing model, deprioritized exact name

Omnus offered the short, standalone sound the owner preferred over many overt
fantasy compounds. Proposed associations were Omnath, the familiar omni- prefix,
and an echo of omnibus: separate things gathered into a whole. These are
branding interpretations, not documented etymologies.

Wizards describes Omnath as a being of pure mana adapting to embody more of
Zendikar's forces in
[The Legends of Zendikar Rising](https://magic.wizards.com/en/news/feature/legends-zendikar-rising-2020-09-15).
The useful metaphor was growth and convergence, not a literal elemental identity.

Three related directions were proposed:

- **Collected volume:** an index, bound volume, or overlapping leaves.
- **Point of convergence:** an original junction or folded-intersection mark.
- **Accumulating whole:** a product that grows with the collector's hobby.

The proposed visual identity was composed and editorial: warm paper, dark ink,
one interaction accent, an enclosing mark with overlapping leaves, and no
five-color wheel or Omnath silhouette.

The owner subsequently moved away from Omnus. Searches found software and other
uses, including [omnus.dev](https://omnus.dev/), [omnus.io](https://www.omnus.io/),
and [Omnus Law](https://www.omnuslaw.com/). Omnus Labs was an indexed software
lead whose site could not be retrieved. The existing omnus.com page did not
establish its intended business. The name is not a clean commercial candidate.

## 9. Candidate inventory: non-Myr directions

This is a record of ideas, not a list of cleared or equally recommended names.
Unless section 12 says otherwise, commercial availability remains unverified.

### Early lore and workshop alternatives

| Candidate | Proposed association | Assessment from the discussion |
|---|---|---|
| Glintrove | Glint + trove; shiny discoveries gathered together | Strong cross-game collecting metaphor; owner later responded to Glint itself |
| Rummageworks | Rummaging + a workshop; goblin ingenuity | Closest to Goblin Tools' assembled-tool identity; historical business use |
| Lorewright | Knowledge and making | Nearby tabletop and roleplay software uses; deprioritize |
| Folioforge | Catalog/folio + making | More constructed; no reliable clearance established |
| Loreloft | A home for knowledge | Existing gaming-content usage |
| Scrollwright | Scrolls and craftsmanship | Existing adjacent creative-software studio |
| Cobblekin | Cobbling together + a family of helpers | Warm and multi-game; weaker actual Magic connection |
| Lorecoil | Knowledge, scrolls, and mechanisms | Compact, but suggests writing/worldbuilding software |
| Cogfolio, Cogkeeper, Cog & Quill | Cogwork Librarian and mechanical knowledge tools | Creative leads only |
| Moonfolio, Scrollhaven, Scrollnest | Tamiyo's traveling story collection and scrolls | Creative leads only; not canonical names |

The owner said they did not like much of the original non-Myr alternatives.
Preserve them as explored options, not current favorites.

### Altered lore names

| Candidate | Proposed root | Assessment |
|---|---|---|
| Tolaryn | Tolaria and Tolarian Academy | Knowledge, research, artifice; fantasy-name and spelling friction |
| Tolarin | Alternate Tolaria-derived spelling | Pharmaceutical-name references surfaced; prefer not to pursue this spelling |
| Vedryn | Vedalken | Compact knowledge/artifice association, but faint reference and spelling friction |
| Thranum | Thran civilization and artifacts | Strong deep-history root; harder opening consonants and existing surname |
| Orriva | Orrery, especially Vedalken Orrery | Connected instrument metaphor; existing event-venue brand |
| Lithora | Lithoform | Existing commercial uses, including software |
| Vesari | Proposed echo of Vesuva | Not shortlisted; no reliable clearance established |
| Hedral | Hedrons | Existing engineering-technology business |
| Scryve | Scry + writing/archive associations | Existing tabletop/TCG and other software uses |

These were coined allusions, not claims that the names are canonical Magic
terms. The owner then asked to move beyond Magic-specific references.

### Plain-language names

| Candidate | Meaning and fit | Reservation |
|---|---|---|
| Accord | Collection, decks, purchases, and plans brought into agreement | Broad and not immediately card-related |
| Collate | Gathering and arranging information; card collation connection | Procedural and potentially hard to distinguish |
| Good Order | Organization and a satisfying purchase | Two words; organizing-service association |
| Holdings | What you own, with provenance and value | Investment rather than play |
| Commonplace | A personal book of useful discoveries | Can mean unremarkable |
| Assemblage | Individual pieces becoming a meaningful whole | Long and spelling friction |
| Repertoire | What you can do with what you own | Pronunciation and spelling friction |
| Cardwell | Cards well kept and put to use | Existing surname; shop-like |

Accord was an assistant recommendation, not an owner selection. The owner
redirected toward Trove and Hoard.

### Treasure and storage names

| Candidate | Meaning and fit | Reservation |
|---|---|---|
| Trove | Curated, valuable discoveries | Direct competing collection-app uses found |
| Hoard | An accumulated, loved pile of treasures | Clutter and compulsive-collecting associations |
| Trovekeep | Tending a treasure collection | Constructed name; trove-root competition |
| Hoardwell | Enthusiastic collecting done well | Availability unverified |
| Cache | Stored valuables and local software data | Spoken confusion with cash; generic |
| Stash | Informal personal collection | Other common associations |
| Lode | A rich source of things worth finding | Spoken confusion with load |
| Strongbox | A tangible container for prized possessions | Established password-manager name; keep researching the territory |
| Stockpile | Useful things ready when needed | Utilitarian rather than curated |
| Treasurehouse | Both the collection and its home | Long |

Trove feels curated and discovered; Hoard feels accumulated and loved. The
owner responded positively to this territory and explicitly asked to add
Strongbox to further research.

## 10. Card references and puns

### Treasure, collection, and artifact references

| Actual reference | Naming proposals or connection |
|---|---|
| [Trove Warden](https://scryfall.com/card/znc/3/trove-warden) | Troveward; keeper rather than just a container |
| [Glint Hawk](https://scryfall.com/card/som/10/glint-hawk) | Glint, Glintkeep; the flavor text describes hunting by metallic gleam |
| [Glint-Nest Crane](https://scryfall.com/card/kld/50/glint-nest-crane) | Glintnest, Glint & Gather; searches for an artifact |
| [Collector's Vault](https://scryfall.com/card/woe/244/collectors-vault) | Beluna; flavor explicitly describes her collecting valuables, including buildings |
| [Fomori Vault](https://scryfall.com/card/big/29/fomori-vault) | Fomori; ancient repository and Thunder Junction vault connection |
| [Shelldock Isle](https://scryfall.com/card/lrw/272/shelldock-isle) | Shelldock; a sheltered place plus the hideaway mechanic |
| [Spinerock Knoll](https://scryfall.com/card/dsc/300/spinerock-knoll) | Another hideaway reference, not a shortlisted name |
| [Kyren Archive](https://scryfall.com/card/mmq/302/kyren-archive) | Kyren, Kyren Archive; accumulates cards for later retrieval |
| [Trove Tracker](https://scryfall.com/card/cmr/104/trove-tracker) | Trovetracker; literal fit to collection tracking |
| [Custodian of the Trove](https://scryfall.com/card/dtk/236/custodian-of-the-trove) | Trovetender, Trovekeep, Troveward |
| [Scholar of the Lost Trove](https://scryfall.com/card/jmp/14/scholar-of-the-lost-trove) | Lost Trove; rediscovering and reusing resources |
| [Treasure Map // Treasure Cove](https://scryfall.com/card/lci/267/treasure-map-treasure-cove) | Trovechart, Cardcove, Covekeep; tool becomes a destination |
| [Dream Cache](https://scryfall.com/card/c18/88/dream-cache) | Dreamcache, Deckcache; stored possibilities |
| [Glittering Stockpile](https://scryfall.com/card/otc/167/glittering-stockpile) | Glintpile, Stockpile, Giltkeep; accumulating resources |
| [Treasure Nabber](https://scryfall.com/card/cmm/265/treasure-nabber) | Nabber, Glintnab; playful acquisition |
| [Junk Diver](https://scryfall.com/card/mh3/293/junk-diver) | Pilediver, Trove Diver; finding treasure among overlooked cards |
| [Scrap Trawler](https://scryfall.com/card/moc/373/scrap-trawler) | Trove Trawler, Pilecraft; reuse and resourcefulness |
| [Salvaging Station](https://scryfall.com/card/5dn/148/salvaging-station) | Workshop and recovery direction, not a shortlisted name |
| [Trading Post](https://scryfall.com/card/msc/224/trading-post) | A multifunctional resource engine; exact phrase suggests a store |
| [Academy Manufactor](https://scryfall.com/card/otc/251/academy-manufactor) | Especially apt story: its flavor describes automated sorting of acquisitions for use |
| [Treasure Keeper](https://scryfall.com/card/clb/341/treasure-keeper) | Guardian/keeper identity |
| [Hidden Stockpile](https://scryfall.com/card/2xm/201/hidden-stockpile) | Reserve resources and small useful mechanisms |
| [Hoard Hauler](https://scryfall.com/card/snc/109/hoard-hauler) | Acquisition and transport; less about cataloging |
| [Treasure Trove](https://scryfall.com/card/9ed/110/treasure-trove) | Direct precedent for the trove vocabulary |
| [Dragon's Hoard](https://scryfall.com/card/tdc/317/dragons-hoard) | Classic treasure-store metaphor |
| [Sorcerer's Strongbox](https://scryfall.com/card/m11/213/sorcerers-strongbox) | Direct Magic reference supporting further Strongbox exploration |

Beluna's collecting is theft in the source material; borrow the cabinet
metaphor, not kleptomania as a product value. Likewise, a hideaway land's
connection to safe storage is a branding interpretation, not a security claim.

The owner explicitly called **Troveward and Glint pretty good**. Later screening
found commercial conflicts; creative preference and availability are separate.

### Puns and playful compounds

| Candidate | Wordplay | Assessment |
|---|---|---|
| Hoard Advantage | Card advantage | Collection knowledge becomes a practical benefit |
| Glint Condition | Mint condition, plus Glint artifact birds | Memorable; could imply grading or condition tracking |
| Hoard State | Board state | Current state of everything owned; hoard/horde ambiguity |
| Cache & Carry | Cash and carry | Local-first data and purchases; shop-like |
| Hoarderly | Hoard + orderly | Organization without judging enthusiasm; not specifically Magic |
| Trove & Tell | Show and tell / Show and Tell | Warm and social; suggests showcasing |
| Deckquisition | Deck + acquisition | Funny but narrower than the full product |
| Gilt Trip | Guilt trip + gilded treasure | Purchase joke, not a reassuring central identity |
| Rack & Ruin | Rack + familiar phrase | Destructive meaning works against stewardship |

### Recognizable-card spin-offs

| Actual reference | Proposed name | Assessment |
|---|---|---|
| [Sylvan Library](https://scryfall.com/card/dmr/179/sylvan-library) | Sylventory | Sylvan + inventory; purpose built in, pronunciation needs testing |
| [Chord of Calling](https://scryfall.com/card/rvr/134/chord-of-calling) | Hoard of Calling | Strong card-name pun; long and overtly Magic-coded |
| [Sensei's Divining Top](https://scryfall.com/card/2x2/314/senseis-divining-top) | Divining Box | Finding possibilities in a physical box of cards |
| [Scroll Rack](https://scryfall.com/card/cmr/337/scroll-rack) | Rack & File | Rank-and-file/filing wordplay; could suggest storage hardware |
| [Brainstorm](https://scryfall.com/card/frc/39/brainstorm) | Hoardstorm | Energetic, but less calm and dependable |
| [Ponder](https://scryfall.com/card/tdc/159/ponder) | Ponderkeep | Thoughtful discovery and keeping; faint reference |
| [Fact or Fiction](https://scryfall.com/card/frc/41/fact-or-fiction) | Fact or Foil | Memorable, but sounds like a podcast |
| [Thought Vessel](https://scryfall.com/card/mbc/78/thought-vessel) | Thoughtkeep | Knowledge store; no-maximum-hand-size connection |
| [Enlightened Tutor](https://scryfall.com/card/dmr/6/enlightened-tutor) | Enlightened Hoarder | Better as a personality line than a short brand |

Collected Company, Preordain, and Birthing Pod were also inspected as recognizable
references, but did not produce a leading name in this pass.

## 11. Mechanics and community terminology

The owner's tutor suggestion shifted the question from "where do treasures
live?" to **"how do you find the right thing among everything you own?"**

### Community terms and effect families

These are not all official keywords. Preserve that distinction in any future
brand story or product copy.

| Term | Meaning in Magic | Branding relevance |
|---|---|---|
| Tutor | Library search effect, often restricted; named after tutor cards such as Demonic Tutor | Exact finding and guidance; understandable across TCGs |
| Toolbox | Varied situational cards with ways to access the appropriate one | Specialized tools connected through one collection |
| Wish / Wishboard | Outside-the-game access; a wishboard supplies options, ordinarily from a tournament sideboard | Bridge between the current deck and wider available cards |
| Brew | Experimenting with deck creation | Making something from your cards |
| Engine | Repeated generation of value or resources | Connected functions working together |
| Cantrip | A spell that draws a card alongside another effect | Small useful tool with low overhead |
| Loot | Generally draw, then discard | Selection, plus the ordinary treasure meaning |
| Rummage | Generally discard, then draw | Searching through and improving a pile |
| Dig | Looking through cards to find what is needed | Discovering possibilities already owned |
| Silver bullet | Specialized answer to a particular problem | Precise recommendations and toolbox tools |
| Card selection | Choosing or arranging access to cards | Understanding and improving options |
| Staple | Widely useful, commonly included card | Essential resource and physical organizing-object double meaning |
| Playset | A full playable allotment, often four depending on format | Completeness and readiness |
| Singleton | One-copy restriction, usually with exceptions | Collectibility, but not an accurate description of all inventory |

Wish does not mean that a player can always take any owned card into any game.
Tournament outside-the-game access is restricted to the sideboard, and format
rules matter. The brand metaphor must not be presented as a universal rule.

### Official mechanics and keyword actions

| Term | Brief meaning | Branding relevance or caution |
|---|---|---|
| Scry | Inspect top cards; put some on the bottom and the rest on top | Foresight and selection; Scryfall strongly occupies the category |
| Surveil | Inspect top cards; put some in the graveyard and the rest on top | Sorting, but ordinary surveillance meaning conflicts with privacy |
| Discover | Exile to a qualifying nonland card; cast it free or put it in hand | Unexpected value; generic standalone word |
| Explore | Reveal top card; take a land or strengthen the creature, with graveyard option for a nonland | A landscape of possibilities |
| Transmute | Discard to search for a card of the same mana value | Turning a resource into what is needed |
| Investigate | Create a Clue token that can be sacrificed to draw | Information becoming useful resources; Clue is the friendly root |
| Forage | Exile three graveyard cards or sacrifice a Food | Gathering/storing atmosphere; actual action is paying a cost |
| Buyback | Additional cost returns the resolving spell to hand | Continued utility; can imply a card-buying service |
| Flashback | Cast from the graveyard for a flashback cost | Reuse, rediscovery, history |
| Convoke | Creatures help pay for a spell | Individual pieces enabling something larger |
| Seek | Digital mechanic finding a random qualifying library card | Useful ordinary search word, but not an exact tutor mechanic |
| Conjure | Digital mechanic creating a card in a specified zone | Possibilities, but a poor literal description of physical inventory |
| Learn | Lesson access from outside the game, or discard to draw, or do neither | Helpful knowledge and outside-the-deck options |
| Connive | Draw and discard; a nonland discard adds a counter to the conniving creature | Selection with growth; ordinary dishonesty connotation is unhelpful |

### Names from the terminology round

| Candidate | Construction | Assessment |
|---|---|---|
| **Hoard & Seek** | Hide-and-seek + hoard + finding cards | Strongest new pun in the latest round; actual Seek is random, not a tutor |
| **Wishkeep** | Wish effects + keeping | Quiet home for owned cards and future possibilities |
| Cantrip Cabinet | Small useful magic + collection cabinet | Whimsical connected tools; long |
| Brewbox | Deck brewing + box | Friendly, with beverage associations requiring screening |
| Trove Tutor | Treasure + exact finding | Clear purpose, but retains crowded trove root |
| Rummage Room | Selection + a workspace | Informal and affectionate; clutter implication |
| Strongholdings | Stronghold + holdings | Storage/treasure and Magic-history echo; financial tone |
| Convoque | Respelling inspired by convoke | Assembly metaphor, but unnecessary spelling friction |

**Conceptual priorities:** tutor, toolbox, and wishboard. These remain useful
even if none becomes the actual name.

### Broader vocabulary: resource use, construction, and growth

The owner pointed out that the first terminology pass was too narrow, naming
**Delve, Aristocrats, tokens, and Timmy** as examples of the wider territory.
The reference pool should include mechanics, objects, strategies, player
identities, collecting language, and social vocabulary, not just card search.
This is a selective map for branding, not an exhaustive rules glossary.

| Term | Classification and meaning | Branding opportunity or caution |
|---|---|---|
| **Delve** | Keyword ability: exile graveyard cards to pay generic mana costs | Digging into what you already have to enable something new; strong ordinary meaning as well |
| Affinity | Cost reduction based on specified things you control | Collection pieces gaining usefulness together; also affection for the hobby |
| Improvise | Tap artifacts to help pay generic mana costs | Make something useful from available pieces; especially apt for the toolkit's origins |
| Fabricate | On entering, choose counters or Servo tokens | Build and customize; also means inventing false information, so avoid misleading implications |
| Craft | Exile specified materials and pay a cost to transform a permanent | Turn collected materials into a finished object or deck |
| Assemble | Assemble a Contraption from the separate Contraption deck onto a sprocket | Separate tools becoming a machine; do not imply a regular library mechanic |
| Modular | Enter with counters; on dying, may transfer its counters to a target artifact creature | Interchangeable, connected tools and reusable resources |
| Populate | Create a copy of a creature token you control | Growing a collection; less apt if it sounds like inventory is duplicated automatically |
| Proliferate | Add another counter of each kind already present to chosen players and permanents | Growth and compounding usefulness; somewhat clinical wording |
| Scavenge | Exile a graveyard card to put counters based on its power on a creature | Overlooked cards becoming useful; salvage rather than premium collecting |
| Dredge | Replace a draw with milling the required cards and returning the dredge card to hand | Recovering resources; murky or destructive ordinary associations |
| Escape | Cast from the graveyard by paying an escape cost | Reuse and access, with an ordinary hobby-as-escape reading |
| Retrace | Cast from the graveyard with an additional land discard | Acquisition history, provenance, returning to earlier choices |
| Rebound | A spell cast from hand can return for a free cast on the next upkeep | Repeated usefulness; ordinary resilience association |
| Flash / flash speed | Permission to cast at instant timing / informal timing phrase | Readiness and responsiveness; speed must not replace reliability |
| Morph | Cast face down and later turn face up through its mechanic | Discovery and identity, but hidden inventory is not the product promise |
| Transform | Turn a transforming double-faced card to its other face | Collection becoming decks and plans becoming actions |
| Meld | Specific paired cards combine into a larger game object | Separate components forming a coherent whole |
| Entwine | Additional cost allows all modes rather than just one | Connected workflows and integration |
| Kicker | Optional additional cost for an extra effect | Useful extras; common word with little collection meaning |
| Cascade | Exile through the library to a qualifying cheaper spell | Discovery and chains of value; no guarantee of finding an exact card |
| Storm | Copies a spell based on spells cast before it that turn | Many small actions building to a larger result; chaotic tone |
| Landfall | Ability word grouping triggers for lands entering under your control | Growth and arrivals; too land-specific for the whole brand |
| Treasure / Food / Clue | Predefined artifact-token types with different uses | Stored value, resources, and knowledge; useful individual metaphors |
| **Token** | Game object, not a keyword; also physical collectible representations | Small pieces, creation, and abundance; cryptocurrency confusion is a significant naming concern |
| Counter | Marker on a player or object; also part of the verb for stopping a spell/ability | Counting and interaction double meaning; tokens and counters are not interchangeable |

Definitions here are brief contextual descriptions, not substitute rules text.
In particular, Delve is cost payment rather than library search, and tokens are
game objects rather than a mechanic called "token."

### Archetypes and strategic identities

| Term | Meaning | Branding opportunity or caution |
|---|---|---|
| **Aristocrats** | Sacrifice-and-payoff strategy; name associated with Cartel Aristocrat and Falkenrath Aristocrat | Useful networks of small pieces; distinctive word, but elite/exclusive and sacrifice associations |
| Tokens / go-wide | Strategy producing many bodies rather than concentrating on one | Collection abundance; not synonymous with all token use |
| Blink / flicker | Temporarily exile and return permanents, often reusing entry effects | Rediscovery, refresh, reuse; familiar ordinary words |
| Reanimator | Put substantial threats into play from the graveyard | Giving unused cards new life; horror identity may be too strong |
| Recursion | Repeatedly recovering or reusing resources | Collection reuse and dependable history; technical rather than warm |
| Spellslinger | Strategy centered on instants and sorceries and their payoffs | Energetic hobby identity, but narrows to a playstyle |
| Voltron | Concentrate enhancements on one threat, often a commander | Assembly metaphor, but references another entertainment property; not a clean branding root |
| Eggs | Small artifact/cantrip loops, historically named after egg artifacts | Small pieces forming an engine; opaque outside the archetype |
| Ramp | Increase mana access ahead of ordinary development | Growth and enabling bigger things; broad software/business vocabulary |
| Midrange | Flexible threats and answers between aggressive and controlling extremes | Adaptability; less emotional appeal |
| Tempo | Develop while disrupting the opponent's efficient use of time/resources | Rhythm and smooth workflow; not simply speed |
| Stompy / battlecruiser | Aggressive creature strategies / large-threat-oriented play | Big, tangible enjoyment; not interchangeable strategy terms |
| Goodstuff | Individually strong cards rather than a tightly themed package | Affection for good cards; can imply a lack of identity |
| Jank | Unusual, experimental, often inefficient cards or decks | Creativity and a scrappy toolkit; can imply broken or low-quality software |
| Pile | Informal deck description, sometimes affectionate, sometimes critical | Turns a pile into something usable; don't assume it is always praise |
| Group hug | Provide resources or benefits to multiple players | Friendly sharing, but not private collection management |
| Stax / prison | Resource denial, taxation, and restriction strategies | Recognizable but inhospitable values for this product |
| Build-around | Card that motivates deck construction around its abilities | Discovering what a collection enables |
| Synergy / payoff | Pieces working together / the reward for a strategy | Direct fit to connected collection and deck tools; broad terms |

These are community strategy labels, not official keyword abilities.
Aristocrats is a particularly useful illustration of how a name can become
larger than the original cards that supplied it.

### Player motivations and aesthetic identities

Mark Rosewater distinguishes why people play from what they find beautiful in
the game. These categories overlap and are not skill levels, age groups, or
exclusive audience segments.

| Term | Kind and meaning | Brand relevance |
|---|---|---|
| **Timmy / Tammy** | Psychographic: seeks experiences and emotional engagement, which may be social, dramatic, or surprising | The joy of the hobby; not simply big creatures, beginners, or indiscriminate buying |
| Johnny / Jenny | Psychographic: self-expression through play, construction, or unusual uses | Creative deckbuilding and discovering possibilities |
| Spike | Psychographic: achievement, mastery, and proving capability | Precision and informed decisions; don't equate solely with spending or winning at any cost |
| Vorthos | Aesthetic profile: appreciates flavor, story, and worldbuilding | Art, treatments, theme collecting, and the stories behind cards |
| Mel | Aesthetic profile: appreciates mechanical structure and design | Elegant tools and satisfying connections; not a fourth/fifth psychographic |

The product serves all of these motivations. Naming it after one profile
could unintentionally exclude others; Timmy also has dismissive uses in player
and finance slang. Prefer borrowing the underlying joy or creativity over
labeling the customer.

### Collecting, deckbuilding, and social vocabulary

| Term | Meaning | Brand relevance or caution |
|---|---|---|
| Binder | Physical card storage, display, and trading | Familiar across TCGs; stronger than lore for immediate clarity |
| Bulk | Lower-value cards, often stored in quantity | The product finds uses beyond sticker price; avoid devaluing the collection |
| Chase / chase card | A particularly desired collectible | Discovery and aspiration; not all users collect for scarcity or price |
| Bling | Premium visual treatments or upgraded deck presentation | Personal expression; can overemphasize spending |
| Pet card | A personal favorite retained for affection rather than efficiency | Warm, user-centered collecting |
| Sleeper | An overlooked card with unrealized potential | Discovery within already-owned cards |
| Mana rock / mana dork | Mana-producing artifact / informal name for a mana-producing creature | Small enabling pieces; "dork" is not universally welcoming |
| Gas | Useful action or resources to keep a plan moving | Energy and usefulness; ambiguous outside gaming |
| Topdeck | Draw from the library, often used for a timely draw or playing with no hand | Finding the needed card; already broad gaming vocabulary |
| Curve / curve out | Mana-cost distribution / using resources efficiently across turns | Making the parts fit, but can sound finance-oriented |
| Mulligan / keep | Replace an opening hand / accept it | Fresh starts and curation; keep also connects to storage |
| Sideboard | Cards available for between-game changes under format rules | Reserve possibilities; broader collection is not automatically a legal sideboard |
| Sideboarding | Adjusting a deck for a matchup | Informed choices from known resources |
| Pod | A play group or draft group; also evokes Birthing Pod decks | Community and modular assembly; several different meanings |
| Kitchen table | Informal play outside organized competitive structures | Warm hobby setting across games |
| Goldfish | Test a deck without meaningful opponent interaction | Experimentation; ordinary aquarium meaning dominates |
| The 99 | Commander shorthand for the cards accompanying a single commander | Insider identity; excludes other formats and some commander arrangements |
| The 75 | Shorthand for a 60-card deck plus 15-card sideboard | Collection-to-play completeness; format-specific |
| Playmat / sleeve / deckbox | Physical accessories surrounding the cards | Tactile, cross-game identity; risk sounding like an accessories retailer |

### Additional naming sketches from the expanded map

These are new exploratory sketches recorded while broadening this document,
not owner favorites or availability-screened recommendations.

| Sketch | Root and intended meaning | Main caution |
|---|---|---|
| Delvekeep | Delve + keeping a collection | Another compound; needs a stronger reason than available spelling |
| Delveworks | Deep exploration + useful tools | More technical than personal |
| Delve & Dwell | Digging into a collection + giving it a home | Long, with home/interiors associations |
| Jankyard | Jank + junkyard; creative reuse of an assembled pile | Memorable but risks implying unreliable software |
| Jank Drawer | Jank + junk drawer; useful oddments together | Playful, but can diminish treasured cards |
| Sidehoard | Sideboard + hoard | Good collection/deck pun; ownership extends beyond a sideboard |
| Aristocards | Aristocrats + cards | Recognizable joke, but elite tone and category-wide collision risk |
| Tokenkeep | Tokens + a collection home | Can sound crypto-oriented or token-only |
| Bulk Alchemy | Turning overlooked cards into useful decks | Not literally changing cards or their value; alchemy has other Magic associations |
| Pet Project | Personal favorites + creative deck experiments | Approachable, but generic and not distinctly card-related |

The most productive broader roots to investigate next are **Delve, Affinity,
Improvise, Jank, Sideboard, and player creativity**. Their appeal is conceptual;
none is declared commercially distinctive here.

## 12. Commercial distinctness: consolidated screening

Findings below reflect public-web research on 2026-10-14, not searches of
trademark registries or domain/handle clearance. Search distinctness and legal
availability are different questions. No-hit results are weak evidence, and
several broad searches initially missed real uses found in narrower searches.

| Name | Evidence and source | Consequence for this exploration |
|---|---|---|
| **Trove** | [Trove TCG](https://apps.apple.com/us/app/trove-tcg/id6757101192) offers collection tracking, values, and trading; [Trove: Catalog Your Collection](https://play.google.com/store/apps/details?id=com.jointrove.app&hl=en-US) explicitly includes trading cards | Drop standalone name: direct category overlap |
| **Glint** | [Microsoft Viva Glint](https://www.microsoft.com/en-us/microsoft-viva/glint), plus [Glint Pay](https://help.glintpay.com/hc/en-us/articles/13392284184081-What-is-Glint) for precious-metal holdings and spending | Weak standalone software distinctness |
| **Dream Cache / DreamCache** | [DreamCache](https://www.dreamcache.ai/) is a creative-production software workspace | Deprioritize exact name |
| **Troveward** | [troveward.com](https://troveward.com/) is a live game-recommendation site | Remove from leading commercially viable shortlist |
| **Glintnest** | [AppBrain](https://www.appbrain.com/app/glintnest/com.wxyzglintnest.abcdeshape.kqtmvrl) records a former Android puzzle app, removed from Google Play | Prior use, not a clean slate; weaker than a current competing product |
| **Strongbox** | [Strongbox](https://strongboxsafe.com/) is an existing iOS/macOS password manager | Research container metaphor and derivatives, not assume standalone name is distinctive |
| Omnus | [omnus.dev](https://omnus.dev/), [omnus.io](https://www.omnus.io/), and [Omnus Law](https://www.omnuslaw.com/); additional indexed leads | Deprioritized; owner moved on |
| Lorewright | [Tabletop campaign project](https://github.com/TopherTypes/Lorewright) and [roleplay tool](https://lorewright.net/) | Adjacent audience and software use |
| Scrollwright | [ScrollWright Studios](https://scrollwrightstudios.com/) | Adjacent creative-software use |
| Loreloft | [Gaming-content channel](https://www.youtube.com/@LoreLoft) | Existing entertainment usage |
| Rummageworks | [Business-directory record](https://www.bizapedia.com/wi/rummageworks-llc.html) reports a dissolved LLC | Historical use; neither current conflict nor clearance established |
| Orriva | [Orriva event venue](https://orriva.co.in/) | Exact-name business use, different category |
| Lithora | [Software project](https://github.com/LithoraLabs/Lithora-Release), plus other commercial uses | Not a clean software candidate |
| Hedral | [Engineering-technology business](https://www.steelatlas.vc/hedral/) | Existing technology brand |
| Scryve | [TCG/tabletop app](https://play.google.com/store/apps/details?id=com.sowinghope.count) and other software uses | Directly adjacent use |
| Omnary | [Planning/diary/finance repository](https://github.com/masterteamply-stack/Omnary) surfaced | Exploratory offshoot, not shortlisted |
| Omnora | [Existing knowledge-management company](https://omnora.com/en/company) | Exploratory offshoot, not shortlisted |
| Sylventory | Initial search returned no relevant result | Weak preliminary signal only |
| Glint Condition, Hoard Advantage | No obvious exact commercial collision established; search evidence was thin | Still require deliberate exact-name and close-variant screening |
| Hoard of Calling | Initial search did not establish a commercial collision | Search was not sufficient for clearance |

Omnarium, Lociary, and Locusry were also included in an exploratory search
request, but the search did not return useful evidence. They are not screened
candidates or recommendations.

Every unscreened compound above, including Hoard & Seek, Wishkeep, and the
Strongbox derivatives, needs its own check. Adding a suffix or changing a domain
does not automatically avoid confusion with an existing brand.

## 13. Current exploration state

**Owner signals:** preserve the Myr proposals; explore beyond them; avoid Mox
because it is overused; favor the emotional territory of Trove/Hoard; Troveward
and Glint were positively received; research Strongbox and tutor-like terminology.
The owner also explicitly requested a broader vocabulary than selection/search,
calling out Delve, Aristocrats, tokens, and Timmy.

**Not an approved shortlist:** recent assistant proposals worth retaining for
comparison are Hoard & Seek, Wishkeep, Glint Condition, Hoard Advantage,
Sylventory, Divining Box, and Hoard of Calling. The Myr direction remains
documented, not rejected or selected.

**Commercially problematic exact names:** Trove, Glint, DreamCache, and
Troveward. Glintnest has historical app use. Strongbox has current software use.
Keep their useful metaphors without treating the exact names as clear.

Next research should separate three judgments: whether the owner likes the
name, whether people can say/spell/remember it, and whether it is commercially
distinctive. No name has yet passed all three.

## 14. Sources

Research accessed during the 2026-10-14 discussion:

- [Mark Rosewater, Myr Myr, Off the Wall](https://magic.wizards.com/en/news/making-magic/myr-myr-wall-2004-06-07):
  official design commentary; purpose, order, and replaceable parts.
- [Mark Rosewater, Design Files: Mirrodin, Part 3](https://magic.wizards.com/en/news/making-magic/design-files-mirrodin-part-3):
  official design history; Gnome-to-Myr development and artifact mana creatures.
- [MTG Wiki: Myr](https://mtg.wiki/page/Myr): secondary lore summary,
  pronunciation, etymology, and historical associations.
- [Myr Retriever](https://scryfall.com/card/mrd/215/myr-retriever):
  card reference for the specialized-tool direction.
- [MyLOFT](https://www.myloft.xyz/): existing library-resource brand.
- [MYR](https://www.myr.io/): existing restaurant-software brand.
- [Myrden surname](https://www.familysearch.org/en/surname?surname=Myrden):
  existing-name reference.
- [Myrarium](https://www.myrarium.eu/): indexed collision lead only; direct
  site retrieval failed, so its current activity and scope remain unverified.
- [DESIGN.md](../DESIGN.md), [light tokens](../web/tokens/light.tokens.json),
  and [dark tokens](../web/tokens/dark.tokens.json): implemented visual baseline.

Additional sources are linked beside the relevant claims in sections 8-12:

- [MTG Wiki: Tolarian Academy](https://mtg.wiki/page/Tolarian_Academy),
  [Vedalken](https://mtg.wiki/page/Vedalken), and
  [Thran](https://mtg.wiki/page/Thran): secondary lore foundations.
- [Cogwork Librarian](https://scryfall.com/card/cns/58/cogwork-librarian) and
  [Lore Seeker](https://scryfall.com/card/cns/62/lore-seeker): mechanical
  knowledge-helper references.
- [MTG Wiki: Tamiyo](https://mtg.wiki/page/Tamiyo): traveling story archive.
- [Wizards: Ten Stories Tall](https://magic.wizards.com/en/news/making-magic/ten-stories-tall):
  Beluna's character context.
- [MTG Wiki: Wish](https://mtg.wiki/page/Wish),
  [Transmute](https://mtg.wiki/page/Transmute), and
  [Forage](https://mtg.wiki/page/Forage): terminology and rules distinctions.
- [Wizards: Glossary of Terms](https://magic.wizards.com/en/news/feature/glossary-of-terms):
  player-vocabulary reference.
- [Wizards: Vorthos and Mel](https://magic.wizards.com/en/news/making-magic/vorthos-and-mel-2015-08-31):
  player motivations, aesthetic profiles, overlapping identities, and the
  Timmy/Tammy and Johnny/Jenny names.
- [MTG Wiki: Delve](https://mtg.wiki/page/Delve) and
  [Token](https://mtg.wiki/page/Token): keyword/object distinction and rules context.
- [MTG Wiki: player slang](https://mtg.wiki/page/List_of_Magic_slang):
  evolving community vocabulary, distinct from rules keywords.
- [Aristocrats archetype overview](https://commanderdeckmaker.com/learn/archetypes/aristocrats):
  sacrifice, fodder, payoff structure, and namesake cards.

Card references were checked through the sanctioned Scryfall wrapper. The broad
treasure-name search returned 65 cards; this count describes that query at the
time of research, not all relevant Magic cards:

```text
game:paper -is:universesbeyond (name:trove or name:hoard or name:stockpile or name:treasure or name:covetous or name:cache or name:strongbox)
```

Related cards without those name fragments were checked separately. Search
matches alone do not establish a lore claim, and speculative lore from search
summaries has not been used as a basis for this brief.

## 15. Round 2: screening holdovers and new candidates (2026-10-31)

Same method and caveats as section 12: public-web searches only, not
trademark, domain, or handle clearance. A no-hit result is weak evidence.

### Holdovers from section 13

| Name | Evidence | Consequence |
|---|---|---|
| Hoard & Seek | No exact-name app or game; nearby "Hyde & Seek" dice game | Still viable; pun reads instantly |
| Wishkeep | Two Shopify *wishlist* apps named Wish Keeper / wishkeeper | Drop: same function as this product's wishlist feature |
| Sylventory | No hit; closest is Sylvatrium forestry inventory software | Still viable; pronunciation untested |
| Glint Condition | No exact-name product; a teen wellness app is named "glint" | Still viable; grading implication remains |
| Hoard Advantage | No hit among MTG apps searched | Still viable |

### New candidates

Built from the owner's positive signals: Troveward and Glint (short, crisp,
keeper-of-shiny-things), and Omnus (short standalone sound).

| Name | Root | Evidence | Consequence |
|---|---|---|---|
| **Glintward** | Glint Hawk + Trove Warden: a keeper of gleaming things | No exact-name hit; only Guild Wars 2 "Glint" and Elden Ring "glintstone" lore | **Strongest new lead.** Joins both liked names, avoids Viva Glint and troveward.com as exact names |
| Kyren | Kyren Archive (stores cards for later retrieval) | No exact-name product; homophone Cyren was a cybersecurity firm that closed in 2023 | Viable short standalone; spelling and say-it-aloud friction |
| Reliquary | Reliquary Tower (no maximum hand size, the hoarder's land) | [Reliquary](https://apps.apple.com/us/app/reliquary/id660934196) is an existing MTG collection app, dormant since 2022 | Drop: direct category collision |
| Lodestone | Lodestone Myr / Golem; a magnet drawing things in | No TCG app; but The Lodestone is the official Final Fantasy XIV community site (assistant knowledge, not confirmed by search) | Deprioritize: gaming-adjacent collision |
| Hoardward | Hoard + ward | [Hoardware](https://9to5mac.com/?p=1074662) is an iOS device-collection inventory app | Drop: one letter from a collection app |
| Bindery | Card binders | No exact app; crowded binder-app space (TCG Binder, Binderim, BinderDex, BinderWiz) | Drop: generic within the category |
| Spellbinder | Darksteel artifact + binder pun | No software hit; Spellbinders is an established papercraft brand (assistant knowledge, not confirmed by search) | Deprioritize |
| Shelldock | Shelldock Isle (hideaway) | ShellDock CLI and an SSH app | Drop: software collision |
| Trovara | Coined Latinate trove name in the style of Omnus | No exact hit; crowded Trov-/Trova-/Trove root | Deprioritize |
| Cubby | Cube drafting + a small storage compartment | No TCG app hit; generic consumer word with past software use | Unscreened beyond TCG; creative lead only |

Also noted while screening: "Cascade MTG" is an existing app, so Cascade is
taken in-category.

### State after round 2

The previous round left this test standing: is a name *liked*, *sayable*,
and *distinct*? **Glintward** is the first candidate with a plausible yes on
all three, pending the owner's reaction and real clearance (USPTO TESS, domains,
handles). Viable alternates: Hoard & Seek, Kyren, Sylventory, Hoard Advantage,
Glint Condition.

## 16. Round 3: the leyline direction (2026-10-31)

The owner passed on Glintward and pointed toward **leylines**.

### Why the root fits

- **In Magic:** the Leyline cycle (Leyline of the Void, of Sanctity, of
  Anticipation, …) begins the game already on the battlefield if it is in your
  opening hand. Brand reading: what you already own is already working for you
  before you start.
- **Outside Magic:** ley lines are folklore's hidden lines connecting places.
  Brand reading: the unseen connections between your collection, decks,
  purchases, and wants. The word means something with no Magic knowledge, and
  it isn't tied to any one game, so it works beside Pokemon.
- **Pronunciation:** "lay." Readers may say "lee," which matters most for Leyward.

### Screening

| Name | Construction | Evidence | Consequence |
|---|---|---|---|
| Leyline | The root itself | LeyLine creative project-management SaaS; Leyline Creations game studio (Munich); Leyline Technologies; leyline.gg | Drop as an exact name: crowded, including a game studio and software |
| **Leykeep** | Ley + keep: the place your lines lead back to | No exact-name hit; nearest are Leya / LeyIA legal-AI firms | **Lead.** Clear keeper meaning, easy to spell |
| **Leyward** | Ley + ward (Troveward's construction) | No exact-name hit; Leyard is a Chinese LED maker | **Lead.** Keeps the -ward the owner liked; also sounds like *leeward*, the sheltered side, which is a nice second meaning if people say "lee" |
| **Leyfold** | Ley + fold: an enclosure, plus the folded-mark logo idea from section 5 | No exact-name hit; Leybold (vacuum pumps, assistant knowledge) is one letter away | **Lead.** Pairs with the folded-keeper logo concept |
| Leywell, Leychart, Leymark | Source / map / marker | No exact-name hit (combined query only) | Viable alternates; screen individually before relying on them |
| Leystone, Leyhold, Leylight | Anchor stone / holding / lamplight | No exact-name hit (combined query); Ley Holdings Ltd and Leylock Holdings Ltd are UK companies | Leyhold weakened; others unscreened individually |

A competitor in a different category (LeyLine SaaS, Leyline Creations) could
still object to a Ley- compound in software or games; real clearance has to
cover the family, not just exact names.

### State after round 3

Leading candidates: **Leykeep, Leyward, Leyfold**. Each needs the owner's
reaction, a say-it-aloud test ("lay" vs "lee"), and real clearance.
