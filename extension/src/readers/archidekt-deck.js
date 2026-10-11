// magic-manager companion — Archidekt deck reader.
//
// Runs in an archidekt.com tab and fetches the deck's own page, the way your
// browser loads it: Archidekt renders the deck into the page (its Next.js
// __NEXT_DATA__ block), including your private decks when you're signed in —
// the browser attaches your session itself; the companion never reads cookies
// or tokens. The page is parsed as data (DOMParser, scripts never run). Only
// the deck's id, name, owner name and each card's printing, quantity, finish
// (modifier) and categories are kept and sent — nothing else from the page.
//
// A classic script: one global async function.

async function readArchidektDeck(deckId) {
  'use strict';
  if (!/^\d{1,12}$/.test(String(deckId || ''))) return { ok: false, code: 'archidekt.bad_url' };
  var res;
  try {
    res = await fetch('https://archidekt.com/decks/' + deckId, { credentials: 'include', headers: { Accept: 'text/html' } });
  } catch (e) {
    return { ok: false, code: 'archidekt.blocked' };
  }
  if (res.status === 404) return { ok: false, code: 'archidekt.not_found', status: 404 };
  if (res.status === 401 || res.status === 403) return { ok: false, code: 'archidekt.private', status: res.status };
  if (!res.ok) return { ok: false, code: 'archidekt.http', status: res.status };
  var doc = new DOMParser().parseFromString(await res.text(), 'text/html');
  var el = doc.getElementById('__NEXT_DATA__');
  if (!el) return { ok: false, code: 'archidekt.changed' };
  var nd;
  try { nd = JSON.parse(el.textContent || ''); } catch (e) { return { ok: false, code: 'archidekt.changed' }; }
  var props = nd && nd.props && nd.props.pageProps;
  if (!props || typeof props !== 'object') return { ok: false, code: 'archidekt.changed' };
  var deck = props.redux && props.redux.deck;
  // A deck Archidekt won't show this browser renders without its id / cards.
  if (!deck || typeof deck !== 'object' || deck.id == null) return { ok: false, code: 'archidekt.private' };
  var map = deck.cardMap;
  if (!map || typeof map !== 'object') return { ok: false, code: 'archidekt.changed' };

  function str(v, n) { return v == null ? null : String(v).slice(0, n); }
  var cards = [];
  Object.keys(map).slice(0, 2000).forEach(function (k) {
    var c = map[k] || {};
    var q = Number(c.qty);
    if (!(q >= 1)) return;
    cards.push({
      quantity: Math.min(999, Math.floor(q)),
      modifier: str(c.modifier, 20),
      categories: (Array.isArray(c.categories) ? c.categories : []).slice(0, 10).map(function (x) { return str(x, 60); }),
      card: {
        uid: str(c.uid, 40),
        collectorNumber: str(c.collectorNumber, 12),
        edition: { editioncode: str(c.setCode, 10) },
        oracleCard: { name: str(c.name, 200) }
      }
    });
  });
  if (!cards.length && deck.private) return { ok: false, code: 'archidekt.private' };
  return {
    ok: true,
    deck: { id: Number(deck.id), name: str(deck.name, 200), owner: { username: str(deck.owner, 100) }, cards: cards }
  };
}
