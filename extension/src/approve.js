// The companion's own approval window. Shows the requesting app address and
// exactly the data that would be sent; nothing leaves until "Send". Built with
// textContent only — page data is never parsed as HTML.

import { APPROVAL_TTL_MS, CART_STORES } from './protocol.js';

const $ = (id) => document.getElementById(id);
const KIND_TITLE = { tabs: 'Send your open store tabs?', moxfield: 'Send this Moxfield deck?', order_list: 'Send your list of orders?', orders: 'Send these orders?', watched: 'Send your watched store prices?' };
const MAX_ROWS = 500;

function cell(tr, text, cls) {
  const td = document.createElement(tr.parentElement?.tagName === 'THEAD' ? 'th' : 'td');
  td.textContent = text == null ? '' : String(text);
  if (cls) td.className = cls;
  tr.appendChild(td);
}

function table(headers, rows) {
  const t = $('table');
  t.replaceChildren();
  const head = t.createTHead().insertRow();
  headers.forEach(([h, cls]) => { const th = document.createElement('th'); th.textContent = h; if (cls) th.className = cls; head.appendChild(th); });
  const body = t.createTBody();
  rows.slice(0, MAX_ROWS).forEach((r) => { const tr = body.insertRow(); r.forEach((v, i) => cell(tr, v, headers[i][1])); });
  if (rows.length > MAX_ROWS) { const tr = body.insertRow(); cell(tr, `…and ${rows.length - MAX_ROWS} more (see the raw data)`); }
}

const money = (n) => (n == null ? '—' : `$${Number(n).toFixed(2)}`);

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
    const printing = (i) => i.scryfall_id ? i.scryfall_id.slice(0, 8) + '…'
      : i.tcgplayer_product_id ? `TCGplayer #${i.tcgplayer_product_id}${i.number ? ` · ${i.set_name || ''} ${i.number}` : ''}`
        : i.cardkingdom_product_id ? `Card Kingdom #${i.cardkingdom_product_id} · ${i.set_name || ''}`
          : i.kind && i.kind !== 'single' ? `${i.kind} — not a card` : 'unknown';
    table([['Card'], ['Printing'], ['Finish'], ['Cond.'], ['Qty', 'num'], ['Price each', 'num']],
      d.items.map((i) => [i.name, printing(i), [i.finish, ...(i.treatments || [])].join(' · '),
        [i.condition, i.language && i.language !== 'English' ? i.language : null].filter(Boolean).join(' · '), i.quantity, money(i.price)]));
  } else if (p.kind === 'tabs') {
    table([['Store page'], ['Page reading']],
      d.tabs.map((t) => [t.title || t.url, d.pages[t.url] ? `title, price tags, ${d.pages[t.url].text.split('\n').filter(Boolean).length} price/stock lines` : 'link and title only']));
  } else if (p.kind === 'watched' && confirm) {
    table([['Store'], ['Page'], ['How it is read']],
      d.urls.map((u) => [u.store, u.url, u.open ? 'your open tab' : 'opens in a background tab, then closes']));
  } else if (p.kind === 'watched') {
    table([['Store'], ['Page'], ['Page reading']],
      d.urls.map((u) => [u.store, u.url, (d.pages || {})[u.url] ? `title, price tags, ${d.pages[u.url].text.split('\n').filter(Boolean).length} price/stock lines` : 'couldn’t read — not sent']));
  } else if (p.kind === 'moxfield') {
    const rows = [];
    Object.entries(d.deck.boards).forEach(([board, b]) => Object.values(b.cards).forEach((c) => rows.push([c.card.name, board, c.card.set ? `${c.card.set.toUpperCase()} ${c.card.cn || ''}` : '', c.isFoil ? 'foil' : (c.finish || ''), c.quantity])));
    table([['Card'], ['Board'], ['Printing'], ['Finish'], ['Qty', 'num']], rows);
  } else if (p.kind === 'order_list') {
    table([['Order'], ['Placed'], ['Total', 'num']], d.orders.map((o) => [o.order_id, o.ordered_at, money(o.total)]));
  } else if (p.kind === 'orders') {
    const rows = [];
    d.orders.forEach((o) => o.lines.forEach((l) => rows.push([o.order_id, l.name, l.set_name || l.detail || '', l.kind === 'single' ? l.finish : l.kind, l.quantity, money(l.price)])));
    table([['Order'], ['Item'], ['Set'], ['Finish'], ['Qty', 'num'], ['Price each', 'num']], rows);
  }
  const warnings = d.warnings || [];
  $('warnings').replaceChildren(...warnings.slice(0, 20).map((w) => {
    const div = document.createElement('div');
    div.className = 'warn';
    div.textContent = w.code === 'cart.signed_out' ? `You are not signed in to ${CART_STORES[d.store]?.name || 'Mana Pool'} in this browser — this is the guest cart.`
      : w.code === 'cart.row_unreadable' ? `Cart line ${w.row}: couldn't read ${w.missing.join(', ')}.`
      : w.code === 'tabs.page_unreadable' ? `Couldn't read ${w.url} — reload that tab and read again.`
      : w.code === 'orders.row_unreadable' ? `Order ${w.order || ''} line ${w.row || ''}: couldn't read ${(w.missing || []).join(', ')}.`
      : w.code === 'orders.unverified_line' ? `Order ${w.order || ''} line ${w.row}: not a recognised product line — it will be recorded but never added to your collection.`
      : w.code === 'orders.not_found' ? `Order ${w.order} wasn't on your order pages.`
      : w.code === 'watched.load_timeout' ? `${w.url} didn't finish loading — open it yourself and read again.` : w.code;
    return div;
  }));
  $('raw').textContent = JSON.stringify(d, null, 2);
}

let created = 0;

async function decide(approve) {
  $('approve').disabled = $('deny').disabled = true;
  const p = (await chrome.storage.session.get('pending')).pending;
  if (!p) { window.close(); return; }
  if (approve === true && p.stage === 'confirm') return readPages(p);
  const r = await chrome.runtime.sendMessage({ type: 'decision', id: p.id, approve });
  if (approve === true && r && !r.ok) { $('status').textContent = r.message || 'Not sent.'; return; }
  window.close();
}

/** Watched pages: you approved the list → read them, then show what would be sent. */
async function readPages(p) {
  created = 0;   // no expiry while reading
  $('ttl').textContent = '';
  $('deny').disabled = false;
  $('status').textContent = `Reading ${p.data.urls.length} pages… tabs opened for this close afterwards.`;
  const r = await chrome.runtime.sendMessage({ type: 'decision', id: p.id, approve: 'read' });
  const now = (await chrome.storage.session.get('pending')).pending;
  if (!r?.ok || !now || now.id !== p.id || now.stage !== 'send') { window.close(); return; }
  $('status').textContent = '';
  ready(now);
}

/** Show a pending request and arm its buttons. */
function ready(p) {
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
  render(p);
  created = p.created;
  // Like Chrome's own permission prompts: focus the safe choice, and keep Send
  // disabled briefly so a keypress meant for another window can't approve.
  $('approve').disabled = true;
  $('deny').disabled = false;
  $('deny').focus();
  setTimeout(() => { $('approve').disabled = false; }, 1000);
}

async function main() {
  const p = (await chrome.storage.session.get('pending')).pending;
  if (!p) { $('status').textContent = 'Nothing is waiting for approval.'; $('approve').disabled = true; return; }
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
