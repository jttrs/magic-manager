// magic-manager companion — Card Kingdom order history readers.
//
//  * readCardKingdomOrderList(doc): the Order History table — per order its
//    order id, date, total and invoice link (used only by the companion).
//  * readCardKingdomInvoice(doc): one invoice's line table — per line the
//    description, quantity and unit price; plus subtotal / shipping / tax / total.
// Reads table cells only. It never reads names, addresses, payment, tracking,
// the page's embedded order data (scripts), cookies or storage, and never calls
// Card Kingdom or anyone else.
//
// Verified against saved pages (tests/fixtures/companion/cardkingdom-*.html) for
// SEALED products only. How Card Kingdom shows SINGLES is UNVERIFIED (the owner
// has no single-card orders to check against): any line that isn't a plain
// product row is returned as kind 'other' with an orders.unverified_line
// warning, so it is recorded with its price but never added to a collection.
//
// A classic script (no modules): it defines global functions.

function cardKingdomText(el) { return el ? (el.textContent || '').replace(/\s+/g, ' ').trim() : ''; }

function cardKingdomMoney(s) {
  var m = /(-?)\$?\s?(\d[\d,]*\.\d{2})/.exec(String(s || ''));
  return m ? Number((m[1] || '') + m[2].replace(/,/g, '')) : null;
}

function cardKingdomSignedOut(doc) {
  var path = (doc.location && doc.location.pathname) || '';
  return /customer_login|\/login\b/i.test(path);
}

function readCardKingdomOrderList(doc) {
  'use strict';
  var text = cardKingdomText;
  var MONTHS = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12 };
  if (cardKingdomSignedOut(doc)) {
    return { ok: false, code: 'orders.sign_in', message: 'Sign in to Card Kingdom in this browser, then try again.', warnings: [] };
  }
  var links = doc.querySelectorAll('a[href^="/myaccount/invoice/"]');
  var orders = [];
  var warnings = [];
  for (var i = 0; i < links.length; i++) {
    var a = links[i];
    var href = a.getAttribute('href') || '';
    var id = /^\/myaccount\/invoice\/(\d+)$/.exec(href);
    var row = a.closest('tr');
    if (!id || !row) continue;
    var cells = row.querySelectorAll('td');
    var dateCell = null;
    var totalCell = null;
    for (var c = 0; c < cells.length; c++) {
      if (cells[c].id === 'order_date') dateCell = cells[c];
      if (cells[c].id === 'order_total') totalCell = cells[c];
    }
    var d = /([A-Za-z]{3})[a-z]*\s+(\d{1,2}),\s*(\d{4})\s+(\d{1,2}):(\d{2})\s*(AM|PM)/i.exec(text(dateCell));
    if (!d || !MONTHS[d[1].toLowerCase()]) { warnings.push({ code: 'orders.row_unreadable', missing: ['date'] }); continue; }
    var hh = Number(d[4]) % 12 + (/pm/i.test(d[6]) ? 12 : 0);
    orders.push({
      order_id: id[1],
      ordered_at: d[3] + '-' + ('0' + MONTHS[d[1].toLowerCase()]).slice(-2) + '-' + ('0' + d[2]).slice(-2) + 'T' + ('0' + hh).slice(-2) + ':' + d[5],
      total: cardKingdomMoney(text(totalCell)),
      path: href
    });
  }
  var next = doc.querySelector('.bottom-nav a[rel="next"], .pagination a[rel="next"]');
  if (!orders.length) {
    if (/\b0 results\b|no orders/i.test(text(doc.body))) return { ok: false, code: 'orders.none', message: 'There are no orders on your Card Kingdom account.', warnings: warnings };
    return { ok: false, code: 'orders.page_changed', message: 'Card Kingdom changed its Order History page, so no orders could be read.', warnings: warnings };
  }
  return { ok: true, orders: orders, next: next ? next.getAttribute('href') : null, warnings: warnings };
}

function readCardKingdomInvoice(doc) {
  'use strict';
  var text = cardKingdomText;
  var money = cardKingdomMoney;
  if (cardKingdomSignedOut(doc)) {
    return { ok: false, code: 'orders.sign_in', message: 'Sign in to Card Kingdom in this browser, then try again.', warnings: [] };
  }
  var num = /Order\s*#\s*(\d+)/.exec(text(doc.querySelector('h1')));
  var table = doc.querySelector('table.orderContents');
  if (!num || !table) {
    return { ok: false, code: 'orders.page_changed', message: 'Card Kingdom changed its invoice page, so the order could not be read.', warnings: [] };
  }
  var warnings = [];
  var lines = [];
  var sums = { subtotal: null, shipping: null, tax: null, total: null };
  var rows = table.querySelectorAll('tr');
  for (var i = 0; i < rows.length; i++) {
    var cells = rows[i].querySelectorAll('td');
    var desc = rows[i].querySelector('td.Description');
    if (desc && cells.length >= 5) {
      var extra = text(cells[1]);
      var quantity = parseInt(text(cells[2]), 10);
      var price = money(text(cells[3]));
      var plain = !extra && !desc.querySelector('*');
      lines.push({
        kind: plain ? 'sealed' : 'other',
        name: text(desc) || null,
        detail: extra || null,
        quantity: quantity >= 1 ? quantity : 1,
        price: price
      });
      if (!plain) warnings.push({ code: 'orders.unverified_line', row: lines.length });
      if (!(quantity >= 1) || price == null) warnings.push({ code: 'orders.row_unreadable', row: lines.length, missing: [price == null ? 'price' : 'quantity'] });
      continue;
    }
    var last = cells.length ? cells[cells.length - 1] : null;
    if (!last || cells.length < 2) continue;
    var label = text(cells[0]);
    if (last.id === 'shipping_cost' || /^shipping/i.test(label)) sums.shipping = money(text(last));
    else if (last.id === 'tax_value' || /tax/i.test(label)) sums.tax = money(text(last));
    else if (last.id === 'order_total' || /^total/i.test(label)) sums.total = money(text(last));
    else if (/^subtotal/i.test(label)) sums.subtotal = money(text(last));
  }
  if (!lines.length) {
    return { ok: false, code: 'orders.page_changed', message: 'Card Kingdom changed its invoice page, so no lines could be read.', warnings: warnings };
  }
  return { ok: true, order: { order_id: num[1], lines: lines, subtotal: sums.subtotal, shipping: sums.shipping, tax: sums.tax, total: sums.total }, warnings: warnings };
}
