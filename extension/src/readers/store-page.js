// magic-manager companion — open store tab reader (Deals).
//
// For stores whose prices only exist in the rendered page (Best Buy, Target,
// eBay …), reads the minimum the app's store recipes need, from a tab YOU have
// open: the page title, its product price/stock tags, its schema.org Product
// data, and only the visible text lines that mention a price or stock. Nothing
// else on the page (your name, address, cart, account) is collected.
//
// The app applies the store's recipe (config/vendors.toml) to this — the
// extension holds no price logic. A classic script: one global function.

function readStorePage(doc) {
  'use strict';
  var META = /^(og:title|og:price:amount|og:price:currency|product:price:amount|product:price:currency|product:availability|og:availability|twitter:title)$/i;
  var LINE = /\$\s?\d|sold out|out of stock|in stock|coming soon|not available|pre-?order|add to cart|listing (?:was |has )?ended|unavailable/i;
  var CURRENCY = /\bUSD?\s?\$|\bUSD\b/; // case-sensitive: "US $12.00", not "Contact Us"
  var MAX_LINES = 60;
  var MAX_TEXT = 6000;
  var MAX_LD = 8;

  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;'); }

  var head = '';
  var metas = doc.querySelectorAll('meta[property], meta[name]');
  for (var i = 0; i < metas.length; i++) {
    var m = metas[i];
    var key = m.getAttribute('property') || m.getAttribute('name') || '';
    if (!META.test(key)) continue;
    var attr = m.hasAttribute('property') ? 'property' : 'name';
    head += '<meta ' + attr + '="' + esc(key) + '" content="' + esc(m.getAttribute('content') || '') + '">';
  }
  // schema.org microdata (any element): price, currency, availability only.
  var micro = doc.querySelectorAll('[itemprop="price"], [itemprop="priceCurrency"], [itemprop="availability"]');
  for (var mi = 0; mi < micro.length && mi < 12; mi++) {
    var el = micro[mi];
    var val = el.getAttribute('content') || el.getAttribute('href') || (el.textContent || '').trim();
    head += '<meta itemprop="' + esc(el.getAttribute('itemprop')) + '" content="' + esc(String(val).slice(0, 200)) + '">';
  }

  function isProduct(node) {
    if (!node || typeof node !== 'object') return false;
    var t = node['@type'];
    var types = Array.isArray(t) ? t : [t];
    for (var j = 0; j < types.length; j++) if (/^(Product|ProductGroup|Offer|AggregateOffer|IndividualProduct)$/.test(String(types[j]))) return true;
    return false;
  }
  var ld = [];
  var scripts = doc.querySelectorAll('script[type="application/ld+json"]');
  for (var s = 0; s < scripts.length && ld.length < MAX_LD; s++) {
    var raw = scripts[s].textContent || '';
    var data;
    try { data = JSON.parse(raw); } catch (e) { continue; }
    var nodes = Array.isArray(data) ? data : (data && Array.isArray(data['@graph']) ? data['@graph'] : [data]);
    var keep = [];
    for (var n = 0; n < nodes.length; n++) if (isProduct(nodes[n])) keep.push(nodes[n]);
    if (keep.length) ld.push(JSON.stringify(keep.length === 1 ? keep[0] : keep));
  }

  var lines = [];
  var total = 0;
  var all = ((doc.body && doc.body.innerText) || '').split(/\n+/);
  for (var l = 0; l < all.length && lines.length < MAX_LINES; l++) {
    var line = all[l].replace(/\s+/g, ' ').trim();
    if (!line || line.length > 200 || !(LINE.test(line) || CURRENCY.test(line))) continue;
    if (total + line.length > MAX_TEXT) break;
    lines.push(line);
    total += line.length + 1;
  }

  return { title: (doc.title || '').slice(0, 500), head: head, ld: ld, text: lines.join('\n') };
}
