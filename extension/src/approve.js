// The companion's own approval window. Shows the requesting app address and
// exactly the data that would be sent; nothing leaves until "Send". Built with
// textContent only — page data is never parsed as HTML.

import { APPROVAL_TTL_MS } from './protocol.js';

const $ = (id) => document.getElementById(id);
const KIND_TITLE = { cart: 'Send your Mana Pool cart?', tabs: 'Send your open store tabs?', moxfield: 'Send this Moxfield deck?' };
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
  $('title').textContent = KIND_TITLE[p.kind] || 'Send to magic-manager?';
  $('origin').textContent = p.origin;
  $('summary').textContent = p.summary;
  const d = p.data;
  if (p.kind === 'cart') {
    table([['Card'], ['Printing'], ['Finish'], ['Cond.'], ['Qty', 'num'], ['Price each', 'num']],
      d.items.map((i) => [i.name, i.scryfall_id ? i.scryfall_id.slice(0, 8) + '…' : 'unknown', [i.finish, ...(i.treatments || [])].join(' · '), i.condition, i.quantity, money(i.price)]));
  } else if (p.kind === 'tabs') {
    table([['Store page'], ['Page reading']],
      d.tabs.map((t) => [t.title || t.url, d.pages[t.url] ? `title, price tags, ${d.pages[t.url].text.split('\n').filter(Boolean).length} price/stock lines` : 'link and title only']));
  } else if (p.kind === 'moxfield') {
    const rows = [];
    Object.entries(d.deck.boards).forEach(([board, b]) => Object.values(b.cards).forEach((c) => rows.push([c.card.name, board, c.card.set ? `${c.card.set.toUpperCase()} ${c.card.cn || ''}` : '', c.isFoil ? 'foil' : (c.finish || ''), c.quantity])));
    table([['Card'], ['Board'], ['Printing'], ['Finish'], ['Qty', 'num']], rows);
  }
  const warnings = d.warnings || [];
  $('warnings').replaceChildren(...warnings.slice(0, 20).map((w) => {
    const div = document.createElement('div');
    div.className = 'warn';
    div.textContent = w.code === 'cart.signed_out' ? 'You are not signed in to Mana Pool in this browser — this is the guest cart.'
      : w.code === 'cart.row_unreadable' ? `Cart line ${w.row}: couldn't read ${w.missing.join(', ')}.`
      : w.code === 'tabs.page_unreadable' ? `Couldn't read ${w.url} — reload that tab and read again.` : w.code;
    return div;
  }));
  $('raw').textContent = JSON.stringify(d, null, 2);
}

async function decide(approve) {
  $('approve').disabled = $('deny').disabled = true;
  const p = (await chrome.storage.session.get('pending')).pending;
  if (!p) { window.close(); return; }
  const r = await chrome.runtime.sendMessage({ type: 'decision', id: p.id, approve });
  if (approve === true && r && !r.ok) { $('status').textContent = r.message || 'Not sent.'; return; }
  window.close();
}

async function main() {
  const p = (await chrome.storage.session.get('pending')).pending;
  if (!p) { $('status').textContent = 'Nothing is waiting for approval.'; $('approve').disabled = true; return; }
  render(p);
  $('approve').addEventListener('click', () => decide(true));
  $('deny').addEventListener('click', () => decide(false));
  const tick = () => {
    const left = APPROVAL_TTL_MS - (Date.now() - p.created);
    if (left <= 0) { decide('expired'); return; }
    $('ttl').textContent = `Expires in ${Math.ceil(left / 1000)} s.`;
    setTimeout(tick, 1000);
  };
  tick();
  // Like Chrome's own permission prompts: focus the safe choice, and keep Send
  // disabled briefly so a keypress meant for another window can't approve.
  $('deny').disabled = false;
  $('deny').focus();
  setTimeout(() => { $('approve').disabled = false; }, 1000);
}

main();
