import type { Locator, Page } from '@playwright/test';
import { expect, test } from './support';

// Tab rows scroll sideways on narrow screens (overflow-x: auto). That makes
// overflow-y auto too, so a tab hanging a pixel below the row (to sit its
// underline on the rule) used to give the row a vertical scrollbar — a stray
// grey pill at the end of the tabs, since scrollbars are always drawn (#159).
const noVerticalScroll = async (row: Locator) => {
  const { scrollHeight, clientHeight, overflowY } = await row.evaluate((el) => ({
    scrollHeight: el.scrollHeight,
    clientHeight: el.clientHeight,
    overflowY: getComputedStyle(el).overflowY,
  }));
  if (overflowY !== 'hidden' && overflowY !== 'clip') expect(scrollHeight).toBeLessThanOrEqual(clientHeight);
};

const openAddCards = async (page: Page) => {
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: { companion: true } } }));
  await page.goto('/collection');
  await page.getByRole('button', { name: 'Add cards' }).click();
  return page.getByRole('dialog', { name: 'Add cards' }).getByRole('tablist', { name: 'How to add' });
};

for (const width of [1400, 380]) {
  test.describe(`tab rows have no vertical scrollbar at ${width}px`, () => {
    test.use({ viewport: { width, height: 900 } });

    test('Add cards tabs', async ({ page }) => {
      const tabs = await openAddCards(page);
      await expect(tabs.getByRole('tab', { name: 'Import a collection' })).toBeVisible();
      await noVerticalScroll(tabs);
      // The active tab's underline still sits on the header rule.
      await tabs.getByRole('tab', { name: 'Bulk add a list' }).click();
      await noVerticalScroll(tabs);
    });

    test('section tabs and the primary nav', async ({ page }) => {
      await page.goto('/collection');
      const section = page.getByRole('navigation', { name: 'Collection views' });
      await expect(section).toBeVisible();
      await noVerticalScroll(section);
      await noVerticalScroll(page.getByRole('navigation', { name: 'Primary' }));
    });
  });
}

test('narrow: the Add cards tabs still scroll sideways', async ({ page }) => {
  await page.setViewportSize({ width: 380, height: 900 });
  const tabs = await openAddCards(page);
  const { scrollWidth, clientWidth } = await tabs.evaluate((el) => ({ scrollWidth: el.scrollWidth, clientWidth: el.clientWidth }));
  expect(scrollWidth).toBeGreaterThan(clientWidth);
  await tabs.evaluate((el) => { el.scrollLeft = el.scrollWidth; });
  await expect(tabs.getByRole('tab', { name: 'Import a collection' })).toBeInViewport();
});
