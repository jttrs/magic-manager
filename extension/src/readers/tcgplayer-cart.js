// magic-manager companion — TCGplayer cart reader.
//
// Reads ONLY what your TCGplayer cart page (www.tcgplayer.com/cart) shows for
// each cart line: the TCGplayer product id (from the product link — used to
// find the exact printing), card name, set name, collector number, condition,
// language, finish, quantity and unit price. It never reads the sellers,
// shipping, totals, your saved-for-later list, cookies, storage or your
// account, nor a seller's own listing title (the catalog name is used), and
// never calls TCGplayer or anyone else.
//
// Verified against a saved guest cart (tests/fixtures/companion/tcgplayer-cart.html):
// singles in several conditions, a foil, a non-English listing, a sealed product
// and a quantity above one. A signed-in cart uses the same page (owner to confirm).
//
// A classic script (no modules): it defines one global function.

function readTcgplayerCart(doc) {
  'use strict';
  var CONDITIONS = { 'near mint': 'NM', 'lightly played': 'LP', 'moderately played': 'MP', 'heavily played': 'HP', damaged: 'DMG' };
  function text(el) { return el ? (el.textContent || '').replace(/\s+/g, ' ').trim() : ''; }
  function money(s) {
    var m = /\$\s?(\d[\d,]*\.\d{2})/.exec(String(s || ''));
    return m ? Number(m[1].replace(/,/g, '')) : null;
  }

  var path = (doc.location && doc.location.pathname) || '';
  if (/\/login\b|\/signin\b/i.test(path)) {
    return { ok: false, code: 'cart.sign_in', message: 'TCGplayer sent you to its sign-in page. Sign in, open your cart, then try again.', warnings: [] };
  }
  var body = text(doc.body);
  var warnings = [];
  if (/sign in to see items from a previous visit/i.test(body)) warnings.push({ code: 'cart.signed_out' });

  // Cart lines live in seller packages; "Saved for later" is not part of the cart.
  var rows = doc.querySelectorAll('.package section.package-item');
  var items = [];
  for (var i = 0; i < rows.length; i++) {
    var row = rows[i];
    var problems = [];
    var link = row.querySelector('a[href*="/product/"]');
    var pid = link ? /\/product\/([1-9]\d*)(?:[/?#]|$)/.exec(link.getAttribute('href') || '') : null;
    // The catalog name (image alt), not a seller's own listing title.
    var img = row.querySelector('img[data-testid="productImage"]');
    var name = img ? (img.getAttribute('alt') || '').replace(/^Product Image for\s+/i, '').trim() : '';
    if (!name) name = text(row.querySelector('[data-testid="productName"]'));
    name = name.replace(/(?:\s+\([^()]*\))+$/, '');
    if (!name) problems.push('name');

    // "Set, Game, Rarity, Number" — sealed products carry only "Set, Game".
    var meta = [];
    var spans = row.querySelectorAll('p.item-metadata > span');
    for (var s = 0; s < spans.length; s++) meta.push(text(spans[s]).replace(/,\s*$/, ''));
    var setName = meta[0] || null;
    var game = meta[1] || '';
    var number = meta.length >= 4 ? meta[3] : null;

    var cond = text(row.querySelector('[data-testid="txtItemCondition"]'));
    var language = null;
    var dash = /\s+-\s+(.+)$/.exec(cond);
    if (dash) { language = dash[1]; cond = cond.slice(0, dash.index); }
    var finish = /\betched\b/i.test(cond) ? 'etched' : /\bfoil\b/i.test(cond) ? 'foil' : 'nonfoil';
    var base = cond.replace(/\b(?:foil|etched)\b/gi, '').replace(/\s+/g, ' ').trim().toLowerCase();
    var kind = 'single';
    if (game && !/magic/i.test(game)) kind = 'other';
    else if (/unopened|sealed/.test(base) || !number) kind = 'sealed';
    var condition = kind === 'single' ? (CONDITIONS[base] || (base ? base.slice(0, 8).toUpperCase() : null)) : null;

    var qtyEl = row.querySelector('select[data-testid="mp-select__UpdateProductQuantity"]');
    var quantity = parseInt(qtyEl && qtyEl.value ? qtyEl.value : text(row.querySelector('.add-to-cart__dropdown__overlay')), 10);
    if (!(quantity >= 1)) { problems.push('quantity'); quantity = 1; }
    var price = money(text(row.querySelector('[data-testid="txtItemPrice"]')));
    if (price == null) problems.push('price');
    if (!pid && kind === 'single') problems.push('printing');

    items.push({
      kind: kind,
      tcgplayer_product_id: pid ? Number(pid[1]) : null,
      name: name || null,
      set_name: setName,
      number: number,
      finish: finish,
      condition: condition,
      language: kind === 'single' ? (language || 'English') : null,
      quantity: quantity,
      price: price
    });
    if (problems.length) warnings.push({ code: 'cart.row_unreadable', row: items.length, missing: problems });
  }

  if (!items.length) {
    if (/your cart is empty/i.test(body)) {
      return { ok: false, code: 'cart.empty', message: 'Your TCGplayer cart is empty in this browser.', warnings: warnings };
    }
    return { ok: false, code: 'cart.page_changed', message: 'TCGplayer changed its cart page, so no cards could be read.', warnings: warnings };
  }
  return { ok: true, items: items, warnings: warnings };
}
