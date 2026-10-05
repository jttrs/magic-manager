// The safe Mana Pool cart bookmarklet. It reads ONLY what the cart page shows —
// each card's link (set + collector number), quantity, price and foil label —
// and copies that as JSON. It never reads your login, cookies or storage, and
// never calls Mana Pool or anyone else; the app matches the lines locally.
// Best-effort by nature: if Mana Pool redesigns the cart page, it may need an update.

const SOURCE = `(() => {
  const rows = new Map();
  for (const a of document.querySelectorAll('a[href*="/card/"]')) {
    const m = (a.getAttribute('href') || '').match(/\\/card\\/([a-z0-9]+)\\/([^/?#]+)/i);
    if (!m) continue;
    let row = a.parentElement;
    while (row && row !== document.body && !/\\$\\s?\\d/.test(row.innerText || '')) row = row.parentElement;
    if (!row || row === document.body) continue;
    const key = m[1].toLowerCase() + '|' + m[2];
    const prior = rows.get(row);
    if (prior && prior.key !== key) continue;
    const name = (a.textContent || '').trim();
    rows.set(row, { key, set: m[1].toLowerCase(), number: decodeURIComponent(m[2]), name: (prior && prior.name) || name });
  }
  const items = [];
  for (const [row, r] of rows) {
    const text = row.innerText || '';
    const price = text.match(/\\$\\s?([\\d,]+\\.\\d{2})/);
    const field = row.querySelector('input[type="number"], select');
    const qtyText = text.match(/(?:qty|quantity)\\s*:?\\s*(\\d+)|×\\s*(\\d+)|(\\d+)\\s*×/i);
    const qty = Number((field && field.value) || (qtyText && (qtyText[1] || qtyText[2] || qtyText[3])) || 1) || 1;
    const foil = /\\b(etched|foil)\\b/i.test(text) && !/non-?foil/i.test(text);
    items.push({ set: r.set, number: r.number, name: r.name || null, quantity: qty,
      price: price ? Number(price[1].replace(/,/g, '')) : null, finish: foil ? 'foil' : 'nonfoil' });
  }
  if (!items.length) { alert('magic-manager: no cards found. Open your Mana Pool cart page, then click this again.'); return; }
  const payload = JSON.stringify({ source: 'manapool-cart-page', count: items.length, items });
  const done = () => alert('magic-manager: copied ' + items.length + ' cart lines. Paste them into Check my Mana Pool cart.');
  navigator.clipboard.writeText(payload).then(done, () => { prompt('Copy these cart lines:', payload); });
})();`;

/** The bookmarklet as a `javascript:` URL (set via the DOM — React blocks it as an href prop). */
export const cartBookmarkletHref = (): string => `javascript:${encodeURIComponent(SOURCE.replace(/\n\s*/g, ' '))}`;
