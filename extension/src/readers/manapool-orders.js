// magic-manager companion — Mana Pool order history readers.
//
// Two reads of YOUR Mana Pool order pages, nothing else:
//  * readManaPoolOrderList(doc): each order on the Orders page — its order
//    number, when it was placed, its total, and the page link (used only by the
//    companion to open it; never sent to the app). Plus the next-page link.
//  * readManaPoolOrder(doc): one order's Item List — per line the card's exact
//    printing (the Scryfall id in its image link, plus set code + number from
//    the card link), name, set name, finish, condition, quantity and unit price;
//    and the order's subtotal / shipping / fees / store credit / tax / total.
// It never reads your name, address, payment card, tracking numbers, sellers,
// cookies or storage, and never calls Mana Pool or anyone else.
// manaPoolShowItems(doc) presses the page's own "Item List" tab (a view switch,
// not a write).
//
// Pinned against saved pages in tests/fixtures/companion/manapool-order*.html —
// when Mana Pool changes the page, follow the scrape-doctor skill.
//
// A classic script (no modules): it defines global functions.

function manaPoolOrdersText(el) { return el ? (el.textContent || '').replace(/\s+/g, ' ').trim() : ''; }

function manaPoolOrdersMoney(s) {
  var m = /(-?)\$\s?(\d[\d,]*\.\d{2})/.exec(String(s || ''));
  return m ? Number((m[1] || '') + m[2].replace(/,/g, '')) : null;
}

function manaPoolSignedOut(doc) {
  var path = (doc.location && doc.location.pathname) || '';
  return /^\/auth\b/.test(path) || (!!doc.querySelector('a[href^="/auth"]') && !doc.querySelector('a[href^="/settings/orders/"]'));
}

function readManaPoolOrderList(doc) {
  'use strict';
  var text = manaPoolOrdersText;
  if (manaPoolSignedOut(doc)) {
    return { ok: false, code: 'orders.sign_in', message: 'Sign in to Mana Pool in this browser, then try again.', warnings: [] };
  }
  var links = doc.querySelectorAll('a[href^="/settings/orders/"]');
  var orders = [];
  var seen = {};
  var warnings = [];
  for (var i = 0; i < links.length; i++) {
    var a = links[i];
    var href = a.getAttribute('href') || '';
    if (!/^\/settings\/orders\/[0-9a-f-]{36}$/i.test(href) || seen[href]) continue; // skip replacement suborders
    // The order's own box: the nearest ancestor that also holds its <time>.
    var box = a.parentElement;
    while (box && !box.querySelector('time')) box = box.parentElement;
    if (!box) { warnings.push({ code: 'orders.row_unreadable', missing: ['date'] }); continue; }
    var num = /Order\s*#\s*([A-Za-z0-9-]+)/.exec(text(box));
    var time = box.querySelector('time');
    var placed = time ? (time.getAttribute('datetime') || '') : '';
    var iso = /^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})/.exec(placed);
    var total = null;
    var labels = box.querySelectorAll('div');
    for (var j = 0; j < labels.length; j++) {
      if (/^total$/i.test(text(labels[j])) && labels[j].nextElementSibling) { total = manaPoolOrdersMoney(text(labels[j].nextElementSibling)); break; }
    }
    if (!num || !iso) { warnings.push({ code: 'orders.row_unreadable', missing: [!num ? 'order number' : 'date'] }); continue; }
    seen[href] = true;
    orders.push({ order_id: num[1], ordered_at: iso[1] + 'T' + iso[2] + 'Z', total: total, path: href });
  }
  var next = null;
  var nav = doc.querySelectorAll('a[href*="page="]');
  for (var k = 0; k < nav.length; k++) if (/next/i.test(text(nav[k]) + ' ' + (nav[k].getAttribute('aria-label') || ''))) next = nav[k].getAttribute('href');
  if (!orders.length) {
    if (/no orders|haven.t placed|0 results/i.test(text(doc.body))) return { ok: false, code: 'orders.none', message: 'There are no orders on your Mana Pool account.', warnings: warnings };
    return { ok: false, code: 'orders.page_changed', message: 'Mana Pool changed its Orders page, so no orders could be read.', warnings: warnings };
  }
  return { ok: true, orders: orders, next: next, warnings: warnings };
}

function manaPoolShowItems(doc) {
  'use strict';
  var tabs = doc.querySelectorAll('[role="tab"]');
  for (var i = 0; i < tabs.length; i++) {
    if (/^item list$/i.test(manaPoolOrdersText(tabs[i]))) {
      if (tabs[i].getAttribute('aria-selected') !== 'true') tabs[i].click();
      return true;
    }
  }
  return false;
}

function readManaPoolOrder(doc) {
  'use strict';
  var text = manaPoolOrdersText;
  var money = manaPoolOrdersMoney;
  var UUID = /\/cards\/[^/]+\/front\/[0-9a-f]\/[0-9a-f]\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.(?:jpg|jpeg|png|webp)/i;
  var CONDITIONS = { NM: 1, LP: 1, MP: 1, HP: 1, DMG: 1 };
  if (manaPoolSignedOut(doc)) {
    return { ok: false, code: 'orders.sign_in', message: 'Sign in to Mana Pool in this browser, then try again.', warnings: [] };
  }
  var h1 = text(doc.querySelector('h1'));
  var num = /Order\s*#\s*([A-Za-z0-9-]+)/.exec(h1);
  var sub = h1 && doc.querySelector('h1') ? text(doc.querySelector('h1').nextElementSibling) : '';
  var date = /(\d{1,2})\/(\d{1,2})\/(\d{4})/.exec(sub);
  var table = null;
  var tables = doc.querySelectorAll('table');
  for (var t = 0; t < tables.length; t++) {
    var head = text(tables[t].querySelector('thead'));
    if (/item/i.test(head) && /qty/i.test(head) && /price/i.test(head)) { table = tables[t]; break; }
  }
  if (!num || !table) {
    return { ok: false, code: 'orders.page_changed', message: 'Mana Pool changed its order page, so the order could not be read.', warnings: [] };
  }

  var warnings = [];
  var lines = [];
  var rows = table.querySelectorAll('tbody tr');
  for (var i = 0; i < rows.length; i++) {
    var cells = rows[i].querySelectorAll('td');
    if (cells.length < 3) continue;
    var problems = [];
    var link = cells[0].querySelector('a[href^="/card/"], a[href^="/sealed/"]');
    var href = link ? link.getAttribute('href') || '' : '';
    var kind = /^\/card\//.test(href) ? 'single' : /^\/sealed\//.test(href) ? 'sealed' : 'other';
    var nameEl = cells[0].querySelector('a.font-medium, a.truncate') || link;
    var name = text(nameEl);
    if (!name) { var img0 = cells[0].querySelector('img'); name = img0 ? (img0.getAttribute('alt') || '').trim() : ''; }
    if (!name) problems.push('name');
    var setEl = nameEl && nameEl.nextElementSibling && nameEl.nextElementSibling.tagName === 'DIV' ? nameEl.nextElementSibling : null;
    var setName = setEl && !setEl.querySelector('span') ? text(setEl) : '';
    var img = cells[0].querySelector('img[src*="/products/mtg/cards/"]');
    var m = img ? UUID.exec(img.getAttribute('src') || '') : null;
    var sc = /^\/card\/([a-z0-9]+)\/([^/]+)\//i.exec(href);
    if (kind === 'single' && !m && !sc) problems.push('printing');
    var finish = 'nonfoil';
    var condition = null;
    var treatments = [];
    var badges = cells[0].querySelectorAll('span.inline-flex');
    for (var b = 0; b < badges.length; b++) {
      var bt = text(badges[b]);
      if (/^etched( foil)?$/i.test(bt)) finish = 'etched';
      else if (/foil/i.test(bt) && !/non-?foil/i.test(bt)) { if (finish !== 'etched') finish = 'foil'; if (!/^foil$/i.test(bt)) treatments.push(bt); }
      else if (CONDITIONS[bt.toUpperCase()]) condition = bt.toUpperCase();
      else if (bt) treatments.push(bt);
    }
    var quantity = parseInt(text(cells[1]), 10);
    if (!(quantity >= 1)) { problems.push('quantity'); quantity = 1; }
    var priceCell = cells[2].cloneNode(true);
    var extra = priceCell.querySelectorAll('div');
    for (var e = 0; e < extra.length; e++) extra[e].remove();
    var price = money(text(priceCell));
    if (price == null) problems.push('price');
    lines.push({
      kind: kind,
      scryfall_id: m ? m[1].toLowerCase() : null,
      set_code: sc ? sc[1].toLowerCase() : null,
      collector_number: sc ? decodeURIComponent(sc[2]) : null,
      name: name || null,
      set_name: setName || null,
      finish: finish,
      condition: condition,
      treatments: treatments,
      quantity: quantity,
      price: price
    });
    if (problems.length) warnings.push({ code: 'orders.row_unreadable', row: lines.length, missing: problems });
  }

  // The order summary: label → amount pairs at the bottom of the page.
  var sums = { subtotal: null, shipping: null, tax: null, fees: null, credit: null, total: null };
  var pairs = doc.querySelectorAll('dl > div');
  for (var p = 0; p < pairs.length; p++) {
    var kids = pairs[p].children;
    if (kids.length < 2) continue;
    var label = text(kids[0].querySelector('span:not(.sr-only)') || kids[0]).replace(/\s+/g, ' ');
    var amount = money(text(kids[kids.length - 1]));
    if (amount == null) continue;
    if (/^subtotal/i.test(label)) sums.subtotal = amount;
    else if (/^shipping$/i.test(label)) sums.shipping = amount;
    else if (/^tax/i.test(label)) sums.tax = amount;
    else if (/^order total/i.test(label)) sums.total = amount;
    else if (/fee/i.test(label)) sums.fees = Math.round(((sums.fees || 0) + amount) * 100) / 100;
    else if (/extra mana|credit|discount|coupon/i.test(label)) sums.credit = Math.round(((sums.credit || 0) + Math.abs(amount)) * 100) / 100;
  }

  if (!lines.length) {
    return { ok: false, code: 'orders.page_changed', message: 'Mana Pool changed its order page, so no lines could be read.', warnings: warnings };
  }
  return {
    ok: true,
    order: {
      order_id: num[1],
      ordered_on: date ? date[3] + '-' + ('0' + date[1]).slice(-2) + '-' + ('0' + date[2]).slice(-2) : null,
      lines: lines,
      subtotal: sums.subtotal, shipping: sums.shipping, tax: sums.tax, fees: sums.fees, credit: sums.credit, total: sums.total
    },
    warnings: warnings
  };
}
