// magic-manager companion — Card Kingdom cart reader.
//
// Reads ONLY what your Card Kingdom cart page (www.cardkingdom.com/cart) shows
// for each cart line: Card Kingdom's product id (from the card image — used to
// find the exact printing), card name, edition, grade (NM / EX / VG / G),
// finish, quantity and unit price. It never reads the page's request token,
// the sign-in form, totals, cookies, storage or your account, and never calls
// Card Kingdom or anyone else.
//
// Verified against a saved guest cart (tests/fixtures/companion/cardkingdom-cart.html):
// singles in several grades, a foil-only variant, a foil promo, a sealed
// product and a quantity above one. A signed-in cart uses the same page (owner to confirm).
//
// A classic script (no modules): it defines one global function.

function readCardKingdomCart(doc) {
  'use strict';
  var GRADES = { NM: 1, EX: 1, VG: 1, G: 1 };
  var LANGUAGES = /\b(Japanese|German|French|Italian|Spanish|Portuguese|Korean|Russian|Chinese(?: Simplified| Traditional)?|Phyrexian)\b/i;
  function text(el) { return el ? (el.textContent || '').replace(/\s+/g, ' ').trim() : ''; }
  function money(s) {
    var m = /\$\s?(\d[\d,]*\.\d{2})/.exec(String(s || ''));
    return m ? Number(m[1].replace(/,/g, '')) : null;
  }

  var path = (doc.location && doc.location.pathname) || '';
  if (/customer_login|\/login\b/i.test(path)) {
    return { ok: false, code: 'cart.sign_in', message: 'Card Kingdom sent you to its sign-in page. Sign in, open your cart, then try again.', warnings: [] };
  }
  var warnings = [];
  if (doc.querySelector('input[type="password"]')) warnings.push({ code: 'cart.signed_out' });

  var root = doc.querySelector('.cartItemList');
  var rows = root ? root.querySelectorAll('.cart-item-wrapper') : [];
  var items = [];
  for (var i = 0; i < rows.length; i++) {
    var row = rows[i];
    var problems = [];
    var link = row.querySelector('a.product-link');
    var href = link ? (link.getAttribute('href') || '').replace(/^\//, '') : '';
    var sealed = /^mtg-sealed\//.test(href) || !!row.querySelector('img.sealedThumb');
    var kind = sealed ? 'sealed' : /^mtg\//.test(href) ? 'single' : 'other';

    var title = text(row.querySelector('.product-link .title'));
    var variant = /\s*\(([^()]*)\)\s*$/.exec(title);
    var name = variant ? title.slice(0, variant.index).trim() : title;
    if (!name) problems.push('name');
    var number = variant ? (/^0*(\d+[a-z]?)\s+-/i.exec(variant[1]) || [])[1] || null : null;
    var lang = variant ? LANGUAGES.exec(variant[1]) : null;
    var edition = text(row.querySelector('.product-link .edition')).replace(/\s*\([A-Z]\)\s*$/, '') || null;

    var img = row.querySelector('img.imgix-card-image');
    var pid = img ? /cardkingdom\.imgix\.net\/[a-z0-9-]*?-(\d+)(?:[?#]|$)/i.exec(img.getAttribute('src') || '') : null;
    var foil = !!row.querySelector('.product-link .foil');
    var finish = foil ? (/etched/i.test(title) ? 'etched' : 'foil') : 'nonfoil';
    var style = text(row.querySelector('.product-link .style')).toUpperCase();
    var condition = kind === 'single' ? (GRADES[style] ? style : (style ? style.slice(0, 8) : null)) : null;

    var combo = row.querySelector('.lineitemForm [role="combobox"]');
    var q = /current:\s*(\d+)/i.exec(combo ? combo.getAttribute('aria-label') || '' : '');
    var quantity = parseInt(q ? q[1] : text(combo), 10);
    if (!(quantity >= 1)) { problems.push('quantity'); quantity = 1; }
    var each = /\(\s*\$\s?(\d[\d,]*\.\d{2})\s*\/\s*ea\s*\)/i.exec(text(row.querySelector('.item-price-wrapper')));
    var price = each ? Number(each[1].replace(/,/g, '')) : null;
    if (price == null) {
      var line = money(text(row.querySelector('.cart-item-price')));
      if (line != null) price = Math.round((line / quantity) * 100) / 100;
    }
    if (price == null) problems.push('price');
    if (!pid && kind === 'single') problems.push('printing');

    items.push({
      kind: kind,
      cardkingdom_product_id: kind === 'single' && pid ? Number(pid[1]) : null,
      name: name || null,
      set_name: kind === 'single' ? edition : null,
      number: kind === 'single' ? number : null,
      finish: kind === 'single' ? finish : 'nonfoil',
      condition: condition,
      language: kind === 'single' ? (lang ? lang[1] : 'English') : null,
      quantity: quantity,
      price: price
    });
    if (problems.length) warnings.push({ code: 'cart.row_unreadable', row: items.length, missing: problems });
  }

  if (!items.length) {
    if (/your (?:shopping )?cart is empty/i.test(text(doc.body))) {
      return { ok: false, code: 'cart.empty', message: 'Your Card Kingdom cart is empty in this browser.', warnings: warnings };
    }
    return { ok: false, code: 'cart.page_changed', message: 'Card Kingdom changed its cart page, so no cards could be read.', warnings: warnings };
  }
  return { ok: true, items: items, warnings: warnings };
}
