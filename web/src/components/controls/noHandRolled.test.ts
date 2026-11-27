// Guard: views and feature components are built from the shared controls, icons and
// tokens — nothing hand-rolled. A failure names the file and what to use instead.
import { describe, expect, it } from 'vitest';

const sources = import.meta.glob(['/src/**/*.tsx', '!/src/**/*.test.tsx'], { query: '?raw', import: 'default', eager: true }) as Record<string, string>;
const rel = (k: string) => k.replace(/^\/src\//, '');

/** The shared controls themselves: the only files that may draw raw elements. Every
 *  entry must still need it (a test below fails on an exemption with nothing to exempt). */
const CONTROL_FILES = new Set([
  'components/Button.tsx',
  'components/IconAction.tsx',
  'components/InfoTip.tsx',
  'components/MarkToggle.tsx',
  'components/CopyButton.tsx',
  'components/CopyMarked.tsx',
  'components/SortBuilder.tsx',
  'components/ArrangeControls.tsx',
]);
const isControl = (f: string) => f.startsWith('components/controls/') || f.startsWith('components/icons/') || CONTROL_FILES.has(f);
const isIcon = (f: string) => f.startsWith('components/icons/');

/** Charts and data marks: SVG geometry computed from data, not icons. */
const CHART_FILES = new Set(['views/market/PriceHistory.tsx']);

/** Runtime-computed geometry (virtual rows, progress widths, chart positions). */
const STYLE_FILES = new Set([
  'components/VirtualGuide.tsx',
  'components/ProgressRule.tsx',
  'components/CardRow.tsx',
  'components/CardFace.tsx',
  'views/AnalyticsView.tsx',
  'views/JobsView.tsx',
  'views/CollectionView.tsx',
  'views/collection/Checklist.tsx',
  'views/collection/SceneHead.tsx',
  'views/decks/RecipeList.tsx',
  'views/market/ProductContents.tsx',
  'views/market/PriceHistory.tsx',
  'components/addcards/CollectionPane.tsx',
]);

/** Values that have a token: [pattern, what to use]. */
const TOKENISED: [RegExp, string][] = [
  [/shadow-\[0_12px_28px[^\]]*\]/, 'shadow-popover'],
  [/shadow-\[0_24px_60px[^\]]*\]/, 'shadow-dialog'],
  [/tracking-\[0\.0[468]em\]/, 'tracking-caps / tracking-caps-tight / tracking-caps-wide'],
  [/\bsize-\[1\.(?:1|125|15|2|35)rem\]/, 'size-icon-sm|md|lg'],
  [/max-w-\[(?:46|52|62|70)ch\]/, 'max-w-measure-narrow|body|wide'],
  [/aspect-\[488\/680\]/, 'aspect-card'],
  [/rounded-\[4\.5%\/3\.2%\]/, 'rounded-card'],
  [/accent-\[var\(--theme-accent\)\]/, 'the Check control (accent-accent)'],
  [/\bmin-h-9\b/, 'min-h-control (or a shared control)'],
  [/\b(?:h|top|bottom)-\[[23]px\]/, 'h-underline / h-underline-quiet / h-bar'],
];

function violations(test: (file: string, src: string) => string[]): string[] {
  return Object.entries(sources).flatMap(([k, src]) => test(rel(k), src).map((m) => `${rel(k)}: ${m}`));
}

describe('no hand-rolled UI', () => {
  it('scans the app sources', () => {
    expect(Object.keys(sources).length).toBeGreaterThan(100);
    expect(Object.keys(sources).map(rel)).toContain('views/CollectionView.tsx');
  });

  it('raw <button>/<input>/<select>/<textarea> only inside shared controls', () => {
    expect(violations((f, s) => (isControl(f) ? [] : [...new Set(s.match(/<(button|input|select|textarea)\b/g) ?? [])].map((t) => `${t}> — use Button / IconAction / ListRow / Pressable / TextInput / Check / NumberField / SelectInput / TextArea`)))).toEqual([]);
  });

  it('<svg> only in the icon module and charts', () => {
    expect(violations((f, s) => (isIcon(f) || CHART_FILES.has(f) || !/<svg\b/.test(s) ? [] : ['<svg> — add the mark to components/icons/marks.tsx']))).toEqual([]);
  });

  it('caret glyphs are icons, not text', () => {
    expect(violations((_f, s) => (/[▾▸▴]/.test(s) ? ['▾ glyph — use CaretMark / Chevron'] : []))).toEqual([]);
  });

  it('token-backed values use their token', () => {
    expect(violations((_f, s) => TOKENISED.filter(([re]) => re.test(s)).map(([, use]) => `use ${use}`))).toEqual([]);
  });

  it('inline style only for runtime geometry', () => {
    expect(violations((f, s) => (STYLE_FILES.has(f) || !/\bstyle=\{/.test(s) ? [] : ['style={…} — use classes/tokens']))).toEqual([]);
  });

  it('every exemption is still needed', () => {
    const src = (f: string) => sources[`/src/${f}`] ?? '';
    const stale = [
      ...[...CONTROL_FILES].filter((f) => !/<(button|input|select|textarea)\b/.test(src(f))).map((f) => `${f}: no raw control left — drop it from CONTROL_FILES`),
      ...[...STYLE_FILES].filter((f) => !/\bstyle=\{/.test(src(f))).map((f) => `${f}: no inline style left — drop it from STYLE_FILES`),
      ...[...CHART_FILES].filter((f) => !/<svg\b/.test(src(f))).map((f) => `${f}: no <svg> left — drop it from CHART_FILES`),
    ];
    expect(stale).toEqual([]);
  });
});
