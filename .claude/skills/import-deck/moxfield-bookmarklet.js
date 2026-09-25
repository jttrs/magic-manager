/*
 * Moxfield deck exporter — bookmarklet (Moxfield read fallback).
 *
 * WHAT IT DOES
 *   Run this while viewing a Moxfield deck page (moxfield.com/decks/<id>, logged
 *   in or not — the deck just has to be viewable by you). It fetches the deck
 *   from Moxfield's api2 endpoint FROM INSIDE YOUR AUTHENTICATED TAB — so it
 *   rides whatever Cloudflare clearance + session the page already holds, needs
 *   no stored credentials, and is robust to backend changes since it's the same
 *   call the site itself makes. It copies a normalized-cards JSON object to your
 *   clipboard. Paste that into:
 *       pbpaste | uv run python scripts/import_deck.py --file - \
 *           | uv run mm deck import-deck --slug my-deck -
 *
 * WHY A BOOKMARKLET
 *   Moxfield has no sanctioned API and api2 is Cloudflare-gated: a plain
 *   curl/urllib gets HTTP 403. The primary path (scripts/import_deck.py) drives a
 *   real Playwright browser to get past that; THIS is the zero-dependency manual
 *   fallback for when you'd rather not run a browser from the CLI.
 *
 * INSTALL
 *   New bookmark; set its URL to the minified `javascript:` one-liner in
 *   moxfield-bookmarklet.min.txt. Click it on a deck page.
 *
 * BOARD / FINISH MAPPING must match src/magic_manager/decksource.py (parse_moxfield):
 *   mainboard→main, sideboard→side, maybeboard→maybe, commanders→commander,
 *   companions→companion, tokens→token; isFoil||finish∈{foil,etched} → foil.
 */
(async () => {
  const BOARD_MAP = {
    mainboard: "main", sideboard: "side", maybeboard: "maybe",
    commanders: "commander", companions: "companion", tokens: "token",
  };
  const FOIL = new Set(["foil", "etched"]);

  // deck public id from the URL: /decks/<id>[/...]
  const m = location.pathname.match(/\/decks\/([^/]+)/);
  if (!m) {
    alert("Moxfield export: this doesn't look like a deck page (/decks/<id>).");
    return;
  }
  const id = m[1];

  try {
    const data = await fetch("https://api2.moxfield.com/v3/decks/all/" + id, {
      headers: { Accept: "application/json" },
      credentials: "include",
    }).then((r) => {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });

    const cards = [];
    const boards = data.boards || {};
    for (const [boardName, board] of Object.entries(boards)) {
      const target = BOARD_MAP[String(boardName).toLowerCase()];
      if (!target) continue;
      const entries = (board && board.cards) || {};
      for (const entry of Object.values(entries)) {
        const card = entry.card || {};
        const finRaw = String(entry.finish || card.finish || "").toLowerCase();
        const finish = entry.isFoil || FOIL.has(finRaw) ? "foil" : "nonfoil";
        cards.push({
          qty: entry.quantity || 1,
          board: target,
          finish,
          scryfall_id: card.scryfall_id || card.scryfallId || card.id || null,
          set: card.set || card.setCode || null,
          collector_number: card.cn || card.collector_number || card.collectorNumber || null,
          name: card.name || null,
          category: null,
        });
      }
    }
    if (!cards.length) {
      alert("Moxfield export: parsed 0 cards. Backend shape may have changed.");
      return;
    }

    const author = (data.createdByUser && (data.createdByUser.userName || data.createdByUser.username)) || null;
    const payload = JSON.stringify(
      { source: "moxfield-bookmarklet", id, name: data.name || null, author, cards }, null, 2);
    await navigator.clipboard.writeText(payload);
    alert("Moxfield export: copied " + cards.length + " cards to clipboard.\nNow run:\n" +
      "  pbpaste | uv run python scripts/import_deck.py --file - | uv run mm deck import-deck --slug my-deck -");
  } catch (e) {
    alert("Moxfield export failed: " + e.message +
      "\n(Session expired, or the backend changed — reload the deck page and retry.)");
  }
})();
