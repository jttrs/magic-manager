// magic-manager companion — Moxfield collection / binder reader.
//
// Runs in a moxfield.com tab (after moxfield-api.js) and reads, page by page,
// one of: your whole collection, a collection or binder share link, or the
// list of your binders. Each card line keeps only what an inventory import
// needs — printing (Scryfall id, set, collector number), name, finish,
// quantity, and whether it's a proxy or a digital (Arena/MTGO) copy so the app
// can skip those. Condition, language, prices, notes, dates and Moxfield's
// own ids are dropped here (owner, 2026-10-11: inventory is printing × finish).
// Copies of the same printing + finish are summed into one line.
//
// A classic script: one global async function.

async function readMoxfieldCollection(opts) {
  'use strict';
  var what = opts && opts.what;
  var id = opts && opts.id != null ? String(opts.id) : null;
  var PAGE_SIZE = 5000;
  var MAX_PAGES = 40;
  var MAX_LINES = 60000;
  if (what !== 'collection' && what !== 'binder' && what !== 'binders') return { ok: false, code: 'moxfield.bad_url' };
  if (id != null && !/^[A-Za-z0-9_-]{4,64}$/.test(id)) return { ok: false, code: 'moxfield.bad_url' };
  if (what === 'binder' && id == null) return { ok: false, code: 'moxfield.bad_url' };
  var api = moxfieldSession(); // eslint-disable-line no-undef

  function str(v, n) { return v == null ? null : String(v).slice(0, n); }
  function fail(r) { return { ok: false, code: 'moxfield.' + r.code, status: r.status }; }

  if (what === 'binders') {
    var b = await api.get('/v1/trade-binders', 'always');
    if (!b.ok) return fail(b);
    var list = Array.isArray(b.data) ? b.data : b.data && Array.isArray(b.data.data) ? b.data.data : null;
    if (!list) return { ok: false, code: 'moxfield.changed' };
    var binders = [];
    list.slice(0, 500).forEach(function (x) {
      var pid = x && (x.publicId || x.id);
      if (!pid || !/^[A-Za-z0-9_-]{4,64}$/.test(String(pid))) return;
      var n = x.totalCards != null ? x.totalCards : x.cardCount != null ? x.cardCount : x.totalOverall;
      binders.push({ id: String(pid), name: str(x.name, 200), cards: Number.isFinite(Number(n)) && n != null ? Number(n) : null });
    });
    return { ok: true, binders: binders };
  }

  var base = what === 'binder' ? '/v1/trade-binders/' + encodeURIComponent(id) + '/search'
    : id ? '/v1/collections/search/' + encodeURIComponent(id) : '/v1/collections/search';
  var auth = id ? 'if_private' : 'always';
  var byKey = {};
  var order = [];
  var name = null;
  var total = null;
  var items = 0;
  for (var page = 1; page <= MAX_PAGES; page++) {
    var r = await api.get(base + '?pageNumber=' + page + '&pageSize=' + PAGE_SIZE + '&sortType=cardName&sortDirection=ascending', auth);
    if (!r.ok) return fail(r);
    var d = r.data;
    if (!d || typeof d !== 'object' || !Array.isArray(d.data)) return { ok: false, code: 'moxfield.changed' };
    if (page === 1) {
      total = Number.isFinite(Number(d.totalResults)) ? Number(d.totalResults) : null;
      if (d.tradeBinder && d.tradeBinder.name) name = str(d.tradeBinder.name, 200);
    }
    for (var i = 0; i < d.data.length; i++) {
      var e = d.data[i] || {};
      var c = e.card || {};
      var fin = String(e.finish || '').toLowerCase();
      var finish = fin === 'etched' ? 'etched' : fin === 'foil' || (!fin && e.isFoil) ? 'foil' : 'nonfoil';
      var line = {
        quantity: Math.max(1, Math.min(9999, Number(e.quantity) || 1)),
        finish: finish,
        scryfall_id: str(c.scryfall_id, 40),
        set: str(c.set, 10),
        cn: str(c.cn, 12),
        name: str(c.name, 200)
      };
      if (e.isProxy) line.proxy = true;
      if (e.game && String(e.game).toLowerCase() !== 'paper') line.digital = true;
      var key = [line.scryfall_id || (line.set + '#' + line.cn), line.finish, line.proxy ? 1 : 0, line.digital ? 1 : 0].join('|');
      if (byKey[key]) byKey[key].quantity += line.quantity;
      else {
        if (order.length >= MAX_LINES) return { ok: false, code: 'moxfield.too_large' };
        byKey[key] = line;
        order.push(key);
      }
      items++;
    }
    var pages = Number(d.totalPages) || 1;
    if (page >= pages || !d.data.length) break;
    if (page === MAX_PAGES) return { ok: false, code: 'moxfield.too_large' };
  }
  if (!order.length) return { ok: false, code: 'moxfield.collection_empty' };
  return {
    ok: true,
    collection: {
      scope: what, id: id, name: name, signed_in: api.signedIn(), total: total, entries: items,
      lines: order.map(function (k) { return byKey[k]; })
    }
  };
}
