// magic-manager companion — TCGplayer order history reader.
//
// Reads YOUR TCGplayer Order History page (store.tcgplayer.com/myaccount/orderhistory),
// which lists every order with its items inline. Per order: order number, order
// date, subtotal / shipping / sales tax / total; per item: name, set name, the
// TCGplayer product id (from its thumbnail link — used to find the exact
// printing), condition, foil, quantity and unit price. Plus the next page link
// and which date range is selected (pick another year on the page itself; the
// companion never submits the page's forms).
// It never reads names, addresses, sellers, tracking, your e-mail, the page's
// request token, cookies or storage, and never calls TCGplayer or anyone else.
//
// Verified against a saved page (tests/fixtures/companion/tcgplayer-orders.html):
// the first page of orders. Following the pager to later pages is UNVERIFIED.
//
// A classic script (no modules): it defines one global function.

function readTcgplayerOrders(doc) {
  'use strict';
  function text(el) { return el ? (el.textContent || '').replace(/\s+/g, ' ').trim() : ''; }
  function money(s) {
    var m = /(-?)\$\s?(\d[\d,]*\.\d{2})/.exec(String(s || ''));
    return m ? Number((m[1] || '') + m[2].replace(/,/g, '')) : null;
  }
  var MONTHS = { january: 1, february: 2, march: 3, april: 4, may: 5, june: 6, july: 7, august: 8, september: 9, october: 10, november: 11, december: 12 };
  function isoDate(s) {
    var m = /([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})/.exec(s || '');
    if (!m || !MONTHS[m[1].toLowerCase()]) return null;
    return m[3] + '-' + ('0' + MONTHS[m[1].toLowerCase()]).slice(-2) + '-' + ('0' + m[2]).slice(-2);
  }

  var path = (doc.location && doc.location.pathname) || '';
  if (/\/login\b/i.test(path) || /^\/?$/.test(path) && !doc.querySelector('.orderWrap')) {
    return { ok: false, code: 'orders.sign_in', message: 'Sign in to TCGplayer in this browser, then try again.', warnings: [] };
  }
  var wraps = doc.querySelectorAll('.orderWrap');
  var warnings = [];
  var orders = [];
  for (var i = 0; i < wraps.length; i++) {
    var w = wraps[i];
    var head = w.querySelector('.orderHeader');
    var num = /Order Number\s*([A-Z0-9]+(?:-[A-Z0-9]+)+)/i.exec(text(head));
    var date = isoDate(text(w.querySelector('[data-aid="spn-sellerorderwidget-orderdate"]')));
    if (!num || !date) { warnings.push({ code: 'orders.row_unreadable', missing: [!num ? 'order number' : 'date'] }); continue; }
    var sums = { subtotal: null, shipping: null, tax: null, total: null };
    var srows = w.querySelectorAll('[data-aid="tbl-sellerorderwidget-productsinorder"] tr');
    for (var s = 0; s < srows.length; s++) {
      var cells = srows[s].querySelectorAll('td');
      if (cells.length < 2) continue;
      var label = text(cells[0]);
      var amount = money(text(cells[1]));
      if (/^subtotal/i.test(label)) sums.subtotal = amount;
      else if (/^shipping/i.test(label)) sums.shipping = amount;
      else if (/tax/i.test(label)) sums.tax = amount;
      else if (/^total/i.test(label)) sums.total = amount;
    }
    var lines = [];
    var items = w.querySelectorAll('[data-aid="tbl-sellerorderwidget-ordertable"] tbody tr');
    for (var r = 0; r < items.length; r++) {
      var row = items[r];
      var problems = [];
      var a = row.querySelector('td.orderHistoryItems a');
      var name = a ? (a.getAttribute('title') || text(a)) : '';
      if (!name) problems.push('name');
      var span = a ? a.parentElement : null;
      var setName = span ? text(span).replace(text(a), '').trim() : '';
      var img = row.querySelector('img');
      // data-original is the real thumbnail; src may already be the page's "no image" fallback (product 0).
      var pid = img ? /\/product\/([1-9]\d*)_/.exec(img.getAttribute('data-original') || '') || /\/product\/([1-9]\d*)_/.exec(img.getAttribute('src') || '') : null;
      var detail = text(row.querySelector('td.orderHistoryDetail'));
      var cond = (/Condition:\s*(.*)$/i.exec(detail) || [])[1] || '';
      var rarity = (/Rarity:\s*([A-Za-z]{1,2})(?=\s|$)/.exec(detail) || [])[1] || '';
      var sealed = /unopened|sealed/i.test(cond);
      var foil = /foil/i.test(cond);
      var condition = cond.replace(/\s*foil\s*/i, ' ').trim() || null;
      var quantity = parseInt(text(row.querySelector('td.orderHistoryQuantity')), 10);
      if (!(quantity >= 1)) { problems.push('quantity'); quantity = 1; }
      var price = money(text(row.querySelector('td.orderHistoryPrice')));
      if (price == null) problems.push('price');
      if (!pid && !sealed) problems.push('printing');
      lines.push({
        kind: sealed ? 'sealed' : 'single',
        tcgplayer_product_id: pid ? Number(pid[1]) : null,
        name: name || null,
        set_name: setName || null,
        rarity: rarity || null,
        finish: foil ? 'foil' : 'nonfoil',
        condition: sealed ? null : condition,
        quantity: quantity,
        price: price
      });
      if (problems.length) warnings.push({ code: 'orders.row_unreadable', order: num[1], row: lines.length, missing: problems });
    }
    orders.push({ order_id: num[1].toUpperCase(), ordered_at: date, lines: lines, subtotal: sums.subtotal, shipping: sums.shipping, tax: sums.tax, total: sums.total });
  }
  var nextA = doc.querySelector('.pager a.nextPage[href]');
  var sel = doc.querySelector('#DateRange option[selected], #DateRange option:checked');
  if (!orders.length) {
    if (/Viewing\s+0\b|no orders/i.test(text(doc.querySelector('.breadcrumbs')) + ' ' + text(doc.body).slice(0, 4000))) {
      return { ok: false, code: 'orders.none', message: 'There are no TCGplayer orders in the selected date range.', warnings: warnings };
    }
    return { ok: false, code: 'orders.page_changed', message: 'TCGplayer changed its Order History page, so no orders could be read.', warnings: warnings };
  }
  return { ok: true, orders: orders, next: nextA ? nextA.getAttribute('href') : null, range: sel ? text(sel) : null, warnings: warnings };
}
