import { COLLECTION_URL, expect, fixtures, test } from './support';

// The app is a fixed chassis: on a desktop-sized window the page itself never
// scrolls and never rubber-bands; only the panes that overflow scroll.
const VIEWS = [
  ['Collection', COLLECTION_URL],
  ['Purchase history', '/collection/history'],
  ['Decks', '/decks'],
  ['Deck editor', `/decks/${encodeURIComponent(fixtures.deckDetail.deck.slug)}/edit`],
  ['Explore rankings', '/explore?mode=rankings'],
  ['Explore cards', '/explore?mode=card&a=Tifa%20Lockhart'],
  ['Explore earmarked', '/explore?mode=earmarked'],
  ['Market', '/market'],
  ['Jobs', '/jobs'],
] as const;

const chassis = () => {
  const root = document.scrollingElement!;
  const css = (el: Element) => getComputedStyle(el).overscrollBehaviorY;
  // An absolutely positioned element (e.g. an sr-only label) inside a scrolling pane
  // whose containing block is the page itself sits at its static position in the
  // pane's CONTENT — so with enough rows it reaches past the window and makes the
  // page scroll. Every scroll pane must be its own containing block.
  const scroller = (e: Element) => ['auto', 'scroll'].includes(getComputedStyle(e).overflowY);
  const escapes = [...document.querySelectorAll('body *')].filter((e) => {
    if (getComputedStyle(e).position !== 'absolute') return false;
    for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) {
      if (getComputedStyle(p).position !== 'static') return false;      // contained before any scroller
      if (scroller(p)) return true;                                     // a scroller that isn't positioned
    }
    return false;
  }).map((e) => `${e.tagName.toLowerCase()}.${String(e.className).split(' ').slice(0, 3).join('.')}`);
  return {
    scrolls: root.scrollHeight > root.clientHeight || root.scrollWidth > root.clientWidth,
    overscroll: [css(document.documentElement), css(document.body)],
    escapes: [...new Set(escapes)],
  };
};

for (const [name, url] of VIEWS) {
  test(`chassis is static: ${name}`, async ({ page }) => {
    await page.route((u) => u.pathname === `/api/decks/${fixtures.deckDetail.deck.slug}`, (r) => r.fulfill({ json: { ...fixtures.deckDetail, version_id: 7, editable: true } }));
    await page.goto(url);
    await page.waitForLoadState('networkidle');
    expect(await page.evaluate(chassis)).toEqual({ scrolls: false, overscroll: ['none', 'none'], escapes: [] });
    // A wheel over the header (not a scroll surface) leaves the page where it is.
    await page.mouse.move(800, 20);
    await page.mouse.wheel(0, 600);
    expect(await page.evaluate(() => [scrollX, scrollY])).toEqual([0, 0]);
  });
}

test('on a phone the page scrolls, but never rubber-bands past its ends', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/decks');
  await page.waitForLoadState('networkidle');
  expect((await page.evaluate(chassis)).overscroll).toEqual(['none', 'none']);
});
