// The companion's own approval window. Shows the requesting app address and
// exactly the data that would be sent; nothing leaves until "Send". Built with
// textContent only — page data is never parsed as HTML.

import { APPROVAL_TTL_MS, CART_STORES, unpackData } from './protocol.js';

const $ = (id) => document.getElementById(id);
const KIND_TITLE = { tabs: 'Send your open store tabs?', moxfield: 'Send this Moxfield deck?', archidekt: 'Send this Archidekt deck?',
  moxfield_collection: 'Send your Moxfield cards?', moxfield_binders: 'Send your list of Moxfield binders?', order_list: 'Send your list of orders?', orders: 'Send these orders?', watched: 'Send your watched store prices?' };
const MAX_ROWS = 500;
/** A collection read is listed in full (scrollable): rows are added in batches so a 60,000-line
 *  read doesn't freeze the window. */
const ROW_BATCH = 2000;
/** The table being drawn (see table()). */
let drawing = Promise.resolve();

/** A cell: plain text, or {text, meta} — the name with a muted detail line under it. */
function cell(tr, value, cls) {
  const td = document.createElement(tr.parentElement?.tagName === 'THEAD' ? 'th' : 'td');
  if (value && typeof value === 'object') {
    const main = document.createElement('span');
    main.textContent = value.text == null ? '' : String(value.text);
    td.appendChild(main);
    const meta = (value.meta || []).filter(Boolean).join(' · ');
    if (meta) { const m = document.createElement('span'); m.className = 'meta'; m.textContent = meta; td.appendChild(m); }
  } else td.textContent = value == null ? '' : String(value);
  if (cls) td.className = cls;
  tr.appendChild(td);
}

/** The table of what is sent. max = Infinity lists every row, ROW_BATCH at a time; the promise
 *  settles once every row is on screen (Send stays off until then). */
function table(headers, rows, max = MAX_ROWS) {
  let drawn;
  const done = new Promise((r) => { drawn = r; });
  drawing = done;
  const t = $('table');
  t.replaceChildren();
  const head = t.createTHead().insertRow();
  headers.forEach(([h, cls]) => { const th = document.createElement('th'); th.textContent = h; if (cls) th.className = cls; head.appendChild(th); });
  const body = t.createTBody();
  const shown = Math.min(rows.length, max);
  const add = (from) => {
    if (t.tBodies[0] !== body) { drawn(); return; }   // re-rendered meanwhile
    rows.slice(from, Math.min(from + ROW_BATCH, shown)).forEach((r) => { const tr = body.insertRow(); r.forEach((v, i) => cell(tr, v, headers[i][1])); });
    if (from + ROW_BATCH < shown) setTimeout(() => add(from + ROW_BATCH), 0);
    else {
      if (rows.length > max) { const tr = body.insertRow(); cell(tr, `…and ${rows.length - max} more (see the raw data)`); }
      drawn();
    }
  };
  add(0);
  return done;
}

const money = (n) => (n == null ? '—' : `$${Number(n).toFixed(2)}`);
/** A printing as people read it: set code or name + collector number. Store/Scryfall ids stay in the raw data. */
const printing = (set, number) => [set, number ? `#${number}` : null].filter(Boolean).join(' ');

/** A pending request with its data unpacked (the worker holds it packed — see protocol.js). */
async function withData(p) {
  return p && p.packed != null ? { ...p, data: await unpackData(p.packed) } : p;
}

function render(p) {
  const confirm = p.stage === 'confirm';
  $('title').textContent = confirm ? 'Read your watched store pages?'
    : p.kind === 'cart' ? `Send your ${CART_STORES[p.data.store]?.name || 'Mana Pool'} cart?` : KIND_TITLE[p.kind] || 'Send to magic-manager?';
  $('what').textContent = confirm ? 'The pages the companion will read' : 'Exactly what will be sent';
  $('approve').textContent = confirm ? 'Read these pages' : 'Send to magic-manager';
  $('deny').textContent = confirm ? 'Don’t read' : 'Don’t send';
  $('nothing').textContent = confirm
    ? 'Nothing is opened, read or sent yet. Pages not open in this browser open in a background tab and close after the read. You approve what is sent next.'
    : 'Nothing else is sent: no cookies, passwords, sign-in tokens, email or addresses. Nothing has been sent yet.';
  $('origin').textContent = p.origin;
  $('summary').textContent = p.summary;
  const d = p.data;
  if (p.kind === 'cart') {
    table([['Card'], ['Qty', 'num'], ['Each', 'num']],
      d.items.map((i) => [{ text: i.name, meta: [
        printing(i.set_name, i.number),
        i.kind && i.kind !== 'single' ? `${i.kind}, not a card` : i.finish,
        ...(i.treatments || []), i.condition, i.language && i.language !== 'English' ? i.language : null,
      ] }, i.quantity, money(i.price)]));
  } else if (p.kind === 'tabs') {
    table([['Store page'], ['Page reading']],
      d.tabs.map((t) => [t.title || t.url, d.pages[t.url] ? `title, price tags, ${d.pages[t.url].text.split('\n').filter(Boolean).length} price/stock lines` : 'link and title only']));
  } else if (p.kind === 'watched' && confirm) {
    table([['Store'], ['Page'], ['How it is read']],
      d.urls.map((u) => [u.store, u.url, u.open ? 'your open tab' : 'opens in a background tab, then closes']));
  } else if (p.kind === 'watched') {
    table([['Store'], ['Page'], ['Page reading']],
      d.urls.map((u) => [u.store, u.url, (d.pages || {})[u.url] ? `title, price tags, ${d.pages[u.url].text.split('\n').filter(Boolean).length} price/stock lines` : 'couldn’t read, not sent']));
  } else if (p.kind === 'moxfield') {
    const rows = [];
    Object.entries(d.deck.boards).forEach(([board, b]) => Object.values(b.cards).forEach((c) => rows.push([
      { text: c.card.name, meta: [board, printing(c.card.set?.toUpperCase(), c.card.cn), c.isFoil ? 'foil' : c.finish] }, c.quantity])));
    table([['Card'], ['Qty', 'num']], rows);
  } else if (p.kind === 'archidekt') {
    table([['Card'], ['Qty', 'num']],
      d.deck.cards.map((c) => [{ text: c.card.oracleCard.name, meta: [(c.categories || []).join(', '),
        printing(c.card.edition.editioncode?.toUpperCase(), c.card.collectorNumber), c.modifier] }, c.quantity]));
  } else if (p.kind === 'moxfield_binders') {
    table([['Binder'], ['Cards', 'num']], d.binders.map((b) => [b.name, b.cards ?? '']));
  } else if (p.kind === 'moxfield_collection') {
    const c = d.collection;
    table([['Card'], ['Qty', 'num']],
      c.lines.map((l) => [{ text: l.name, meta: [printing(l.set?.toUpperCase(), l.cn), l.finish,
        l.proxy ? 'proxy, skipped' : null, l.digital ? 'digital, skipped' : null] }, l.quantity]), Infinity);
  } else if (p.kind === 'order_list') {
    table([['Order'], ['Placed'], ['Total', 'num']], d.orders.map((o) => [o.order_id, o.ordered_at, money(o.total)]));
  } else if (p.kind === 'orders') {
    const rows = [];
    d.orders.forEach((o) => o.lines.forEach((l) => rows.push([{ text: l.name, meta: [`Order ${o.order_id}`, l.set_name || l.detail, l.kind === 'single' ? l.finish : l.kind] }, l.quantity, money(l.price)])));
    table([['Item'], ['Qty', 'num'], ['Each', 'num']], rows);
  }
  const warnings = d.warnings || [];
  $('warnings').replaceChildren(...warnings.slice(0, 20).map((w) => {
    const div = document.createElement('div');
    div.className = 'warn';
    div.textContent = w.code === 'cart.signed_out' ? `You are not signed in to ${CART_STORES[d.store]?.name || 'Mana Pool'} in this browser, so this is the guest cart.`
      : w.code === 'cart.row_unreadable' ? `Cart line ${w.row}: couldn't read ${w.missing.join(', ')}.`
      : w.code === 'tabs.page_unreadable' ? `Couldn't read ${w.url}. Reload that tab and read again.`
      : w.code === 'orders.row_unreadable' ? `Order ${w.order || ''} line ${w.row || ''}: couldn't read ${(w.missing || []).join(', ')}.`
      : w.code === 'orders.unverified_line' ? `Order ${w.order || ''} line ${w.row}: not a recognised product line. It will be recorded but never added to your collection.`
      : w.code === 'orders.not_found' ? `Order ${w.order} wasn't on your order pages.`
      : w.code === 'watched.load_timeout' ? `${w.url} didn't finish loading. Open it yourself and read again.` : w.code;
    return div;
  }));
  // Filled when opened: a whole collection is megabytes of text.
  const details = $('raw').closest('details');
  const fill = () => { $('raw').textContent = JSON.stringify(d, null, 2); };
  if (details.open) fill(); else { $('raw').textContent = ''; details.addEventListener('toggle', fill, { once: true }); }
}

let created = 0;
/** The request this window was opened for (from its address) — decisions are always sent for THIS id. */
let requestId = null;

async function decide(approve) {
  $('approve').disabled = $('deny').disabled = true;
  const p = (await chrome.storage.session.get('pending')).pending;
  if (!p || p.id !== requestId) { window.close(); return; }   // a newer request replaced ours
  if (approve === true && p.stage === 'confirm') return readPages(p);
  const r = await chrome.runtime.sendMessage({ type: 'decision', id: requestId, approve });
  if (approve === true && r && !r.ok) { $('status').textContent = r.message || 'Not sent.'; return; }
  window.close();
}

/** Watched pages: you approved the list → read them, then show what would be sent. */
async function readPages(p) {
  created = 0;   // no expiry while reading
  $('ttl').textContent = '';
  $('deny').disabled = false;
  $('status').textContent = `Reading ${(await withData(p)).data.urls.length} pages… tabs opened for this close afterwards.`;
  const r = await chrome.runtime.sendMessage({ type: 'decision', id: p.id, approve: 'read' });
  const now = (await chrome.storage.session.get('pending')).pending;
  if (!r?.ok || !now || now.id !== p.id || now.stage !== 'send') { window.close(); return; }
  $('status').textContent = '';
  ready(now);
}

/** Show a pending request and arm its buttons. */
async function ready(p) {
  if (p.stage === 'reading') {   // this window was reloaded mid-read: wait for it
    $('approve').disabled = true;
    $('deny').disabled = false;
    $('status').textContent = 'Reading the pages…';
    setTimeout(async () => {
      const now = (await chrome.storage.session.get('pending')).pending;
      if (!now || now.id !== p.id) window.close();
      else { if (now.stage !== 'reading') $('status').textContent = ''; ready(now); }
    }, 1000);
    return;
  }
  render(await withData(p));
  created = p.created;
  // Like Chrome's own permission prompts: focus the safe choice, and keep Send
  // disabled briefly so a keypress meant for another window can't approve.
  $('approve').disabled = true;
  $('deny').disabled = false;
  $('deny').focus();
  // …and until every row of what is sent is on screen.
  const shown = drawing;
  Promise.all([shown, new Promise((r) => setTimeout(r, 1000))]).then(() => { if (drawing === shown) $('approve').disabled = false; });
}

async function main() {
  requestId = new URLSearchParams(location.search).get('id');
  const p = (await chrome.storage.session.get('pending')).pending;
  if (!p || p.id !== requestId) { $('status').textContent = 'Nothing is waiting for approval.'; $('approve').disabled = true; return; }
  $('approve').addEventListener('click', () => decide(true));
  $('deny').addEventListener('click', () => decide(false));
  const tick = () => {
    if (created) {
      const left = APPROVAL_TTL_MS - (Date.now() - created);
      if (left <= 0) { decide('expired'); return; }
      $('ttl').textContent = `Expires in ${Math.ceil(left / 1000)} s.`;
    }
    setTimeout(tick, 1000);
  };
  ready(p);
  tick();
}

main();
