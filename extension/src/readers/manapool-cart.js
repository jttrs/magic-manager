// magic-manager companion — Mana Pool cart reader.
//
// Reads ONLY what your Mana Pool cart page shows: for each cart row, the card's
// exact printing (the Scryfall id in its image link), name, finish, condition,
// quantity and price. It never reads cookies, storage, your login, your
// address or the sellers, and never calls Mana Pool or anyone else.
//
// Shared verbatim by the extension (injected into the cart tab) and the
// bookmarklet (copied to your clipboard). Pinned against a saved cart page in
// tests/fixtures/companion/ — when Mana Pool changes the page, follow the
// scrape-doctor skill to recapture and fix.
//
// A classic script (no modules): it defines one global function.

function readManaPoolCart(doc) {
  'use strict';
  var UUID = /\/cards\/[^/]+\/front\/[0-9a-f]\/[0-9a-f]\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.(?:jpg|jpeg|png|webp)/i;
  var CONDITIONS = { NM: 1, LP: 1, MP: 1, HP: 1, DMG: 1 };
  var MONEY = /\$\s?(\d[\d,]*\.\d{2})/g;

  function text(el) { return el ? (el.textContent || '').replace(/\s+/g, ' ').trim() : ''; }
  function money(s) { return Number(String(s).replace(/,/g, '')); }

  var path = (doc.location && doc.location.pathname) || '';
  if (/^\/auth\b/.test(path)) {
    return { ok: false, code: 'cart.sign_in', message: 'Mana Pool sent you to its sign-in page. Sign in, open your cart, then try again.', warnings: [] };
  }
  var root = doc.querySelector('section[aria-labelledby="cart-heading"]');
  var signedOut = !!doc.querySelector('a[href^="/auth"]');
  var warnings = [];
  if (signedOut) warnings.push({ code: 'cart.signed_out' });

  if (!root) {
    var body = text(doc.body);
    if (/your cart is empty|cart is empty|no items in your cart/i.test(body) || /\bCart\b/.test(text(doc.querySelector('h1')))) {
      return { ok: false, code: 'cart.empty', message: 'Your Mana Pool cart is empty in this browser.', warnings: warnings };
    }
    return { ok: false, code: 'cart.page_changed', message: 'No cart found on this page. Open your Mana Pool cart, then try again.', warnings: warnings };
  }

  var items = [];
  var rows = root.querySelectorAll('li');
  for (var i = 0; i < rows.length; i++) {
    var row = rows[i];
    var qtyEl = row.querySelector('button[aria-label="Update Quantity"], select[aria-label="Update Quantity"], input[type="number"]');
    var img = row.querySelector('img[src*="/products/mtg/cards/"]');
    if (!qtyEl && !img) continue; // not a cart line (shipping options etc.)

    var problems = [];
    var m = img ? UUID.exec(img.getAttribute('src') || '') : null;
    if (!m) problems.push('printing');
    var name = text(row.querySelector('h3'));
    if (!name && img) name = (img.getAttribute('alt') || '').replace(/ - [^-]+$/, '').trim();
    if (!name) problems.push('name');

    var setName = text(row.querySelector('h3 + div p, p.text-gray-500'));
    var badges = [];
    var badgeEls = row.querySelectorAll('span.inline-flex');
    for (var b = 0; b < badgeEls.length; b++) badges.push(text(badgeEls[b]));
    var finish = 'nonfoil';
    var condition = null;
    var treatments = [];
    for (var j = 0; j < badges.length; j++) {
      var t = badges[j];
      if (/^etched( foil)?$/i.test(t)) finish = 'etched';
      else if (/^foil$/i.test(t) || (/foil/i.test(t) && !/non-?foil/i.test(t))) { if (finish !== 'etched') finish = 'foil'; }
      else if (CONDITIONS[t.toUpperCase()]) condition = t.toUpperCase();
      else if (t) treatments.push(t);
    }

    var quantity = NaN;
    if (qtyEl) quantity = parseInt(qtyEl.value != null && qtyEl.tagName !== 'BUTTON' ? qtyEl.value : text(qtyEl), 10);
    if (!(quantity >= 1)) { problems.push('quantity'); quantity = 1; }

    // The price paragraph is the line total; "(…$X each)" carries the unit price.
    var priceText = '';
    var ps = row.querySelectorAll('p');
    for (var k = 0; k < ps.length; k++) if (/\$\s?\d/.test(ps[k].textContent || '')) priceText = text(ps[k]);
    var each = /\(\s*\$\s?(\d[\d,]*\.\d{2})\s*each\s*\)/i.exec(priceText);
    var amounts = priceText.match(MONEY) || [];
    var price = null;
    if (each) price = money(each[1]);
    else if (amounts.length) price = Math.round((money(amounts[0].replace(/[^\d.,]/g, '')) / quantity) * 100) / 100;
    if (price == null) problems.push('price');

    items.push({
      scryfall_id: m ? m[1].toLowerCase() : null,
      name: name || null,
      set_name: setName || null,
      finish: finish,
      condition: condition,
      treatments: treatments,
      quantity: quantity,
      price: price
    });
    if (problems.length) warnings.push({ code: 'cart.row_unreadable', row: items.length, missing: problems });
  }

  if (!items.length && /cart empty|your cart is empty|no items in your cart/i.test(text(root))) {
    return { ok: false, code: 'cart.empty', message: 'Your Mana Pool cart is empty in this browser.', warnings: warnings };
  }
  if (!items.length) {
    return { ok: false, code: 'cart.page_changed', message: 'Mana Pool changed its cart page, so no cards could be read.', warnings: warnings };
  }
  return { ok: true, items: items, warnings: warnings };
}
