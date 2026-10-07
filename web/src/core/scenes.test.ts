import { describe, expect, it } from 'vitest';
import type { SceneFinishOut, SceneOut } from './api';
import { CARD_SORT_PRESETS } from './cardSort';
import type { GuideCard } from './guideCard';
import { activeRules, collectionPresets, collectionSortKeys, COLLECTION_SORT, finishTally, missingLine, NO_SCENE, SCENE_PRESET, sceneBuyItems, sceneByline, scenePct, sceneRanks } from './scenes';
import { leadSection, sortBy } from './sort';

const fin = (o: Partial<SceneFinishOut>): SceneFinishOut => ({ finish: 'nonfoil', printings: 6, owned: 4, missing_usd: 12.12, unpriced: 0, missing_ids: ['a', 'b'], ...o });
const scene = (o: Partial<SceneOut>): SceneOut => ({
  key: 'ltr:399-404', family: 'ltr', rank: 0, name: 'Shire / Hobbits', artist: 'Livia Prima', kind: 'scene', set_code: 'ltr', cn_lo: 399, cn_hi: 404,
  printings: 6, owned_printings: 4, finishes: [fin({}), fin({ finish: 'foil', owned: 0, missing_usd: 30, missing_ids: ['a', 'b', 'c', 'd', 'e', 'f'] })], ...o,
});
const card = (name: string, scene: string | null, sceneRank: number | null, cn: string) => ({ key: name, name, scene, sceneRank, cn }) as unknown as GuideCard;

describe('scenes view-model', () => {
  it('sorts by scene rank, cards outside every scene last, and sections by scene key', () => {
    const cards = [card('x', null, null, '1'), card('b', 'ltr:405-410', 1, '406'), card('a', 'ltr:399-404', 0, '400'), card('a2', 'ltr:399-404', 0, '399')];
    const rules = SCENE_PRESET.rules;
    const sorted = sortBy(cards, rules, COLLECTION_SORT);
    expect(sorted.map((c) => c.name)).toEqual(['a2', 'a', 'b', 'x']);
    const section = leadSection(rules, COLLECTION_SORT)!;
    expect(sorted.map(section)).toEqual(['ltr:399-404', 'ltr:399-404', 'ltr:405-410', NO_SCENE]);
  });

  it('offers Scene only when the families define scenes', () => {
    expect('scene' in collectionSortKeys(true)).toBe(true);
    expect('scene' in collectionSortKeys(false)).toBe(false);
    expect(collectionPresets(true)[0]).toBe(SCENE_PRESET);
    expect(collectionPresets(false)).toBe(CARD_SORT_PRESETS);
    const rules = [{ key: 'scene' as const, dir: 'asc' as const }, { key: 'cn' as const, dir: 'asc' as const }];
    expect(activeRules(rules, true)).toEqual(rules);
    expect(activeRules(rules, false)).toEqual([{ key: 'cn', dir: 'asc' }]);
  });

  it('ranks scenes in payload order', () => {
    expect([...sceneRanks([scene({}), scene({ key: 'ltr:405-410' })])]).toEqual([['ltr:399-404', 0], ['ltr:405-410', 1]]);
  });

  it('describes completion and cost per finish', () => {
    expect(scenePct(scene({}))).toBe(67);
    expect(scenePct(scene({ printings: 0, owned_printings: 0 }))).toBe(0);
    expect(finishTally(fin({}))).toMatch(/^4\/6 · \$12\.12 to finish$/);
    expect(finishTally(fin({ owned: 6, missing_ids: [] }))).toBe('6/6 · complete');
    expect(finishTally(fin({ missing_usd: 3.1, unpriced: 1 }))).toMatch(/\$3\.10 \+ 1 unpriced to finish$/);
    expect(finishTally(fin({ missing_usd: 0, unpriced: 2 }))).toBe('4/6 · 2 unpriced to finish');
    expect(missingLine(fin({}))).toMatch(/^2 missing printings · \$12\.12$/);
    expect(missingLine(fin({ missing_ids: [] }))).toBe('Complete');
  });

  it('builds one buy item per missing printing in that finish', () => {
    expect(sceneBuyItems(fin({ finish: 'foil', missing_ids: ['a', 'b'] }))).toEqual([
      { scryfall_id: 'a', finish: 'foil', qty: 1 },
      { scryfall_id: 'b', finish: 'foil', qty: 1 },
    ]);
  });

  it('prints artist and collector-number run', () => {
    expect(sceneByline(scene({}))).toBe('Livia Prima · LTR 399–404');
    expect(sceneByline(scene({ artist: null }))).toBe('LTR 399–404');
  });
});
