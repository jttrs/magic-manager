// magic-manager companion — Moxfield deck reader.
//
// Runs in a moxfield.com tab and asks Moxfield's own deck API for ONE deck,
// exactly as the Moxfield site does when you open the deck — so Moxfield's bot
// check and (for your own private decks) your signed-in session apply as
// usual. The companion never reads your cookies or tokens; the browser attaches
// them itself. Only the deck's name, author and each card's printing, quantity,
// finish and board are kept and sent — nothing else from the response.
//
// A classic script: one global async function.

async function readMoxfieldDeck(deckId) {
  'use strict';
  if (!/^[A-Za-z0-9_-]{4,64}$/.test(String(deckId || ''))) return { ok: false, code: 'moxfield.bad_url' };
  var res;
  try {
    res = await fetch('https://api2.moxfield.com/v3/decks/all/' + encodeURIComponent(deckId), {
      credentials: 'include', headers: { Accept: 'application/json' }
    });
  } catch (e) {
    return { ok: false, code: 'moxfield.blocked' };
  }
  if (res.status === 401 || res.status === 403) {
    // Cloudflare's challenge is also a 403 — tell them apart by the body type.
    var ct = res.headers.get('content-type') || '';
    return { ok: false, code: /json/.test(ct) ? 'moxfield.private' : 'moxfield.blocked', status: res.status };
  }
  if (res.status === 404) return { ok: false, code: 'moxfield.not_found', status: 404 };
  if (!res.ok) return { ok: false, code: 'moxfield.http', status: res.status };
  var data;
  try { data = await res.json(); } catch (e) { return { ok: false, code: 'moxfield.changed' }; }
  if (!data || typeof data !== 'object' || !data.boards || typeof data.boards !== 'object') return { ok: false, code: 'moxfield.changed' };

  function str(v, n) { return v == null ? null : String(v).slice(0, n); }
  var boards = {};
  var count = 0;
  Object.keys(data.boards).slice(0, 20).forEach(function (bn) {
    var board = data.boards[bn];
    var entries = board && board.cards;
    if (!entries || typeof entries !== 'object') return;
    var cards = {};
    Object.keys(entries).slice(0, 1000).forEach(function (k, i) {
      var e = entries[k] || {};
      var c = e.card || {};
      cards[String(i)] = {
        quantity: Number(e.quantity) || 1,
        isFoil: !!(e.isFoil || e.foil),
        finish: str(e.finish, 20),
        card: {
          scryfall_id: str(c.scryfall_id || c.scryfallId, 40),
          set: str(c.set || c.setCode, 10),
          cn: str(c.cn || c.collector_number || c.collectorNumber, 12),
          name: str(c.name, 200),
          finish: str(c.finish, 20)
        }
      };
      count++;
    });
    boards[str(bn, 40)] = { cards: cards };
  });
  if (!count) return { ok: false, code: 'moxfield.changed' };
  var author = data.createdByUser && (data.createdByUser.userName || data.createdByUser.displayName);
  return {
    ok: true,
    deck: { publicId: str(data.publicId || deckId, 64), name: str(data.name, 200), createdByUser: { userName: str(author, 100) }, boards: boards }
  };
}
