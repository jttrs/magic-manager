// Scenes in Collection — framework-free. A family's configured scene/poster runs
// (CollectionOut.scenes, engine magic_manager.scenes) become a "Scene" group in the
// Collection guide: each run is a section whose head carries per-finish completion,
// cost to finish, and buy lists for the missing panels.
import type { SceneFinishOut, SceneOut } from './api';
import { CARD_SORT, CARD_SORT_PRESETS } from './cardSort';
import { fmtCount, fmtInt, fmtUsd } from './format';
import type { GuideCard } from './guideCard';
import type { SortPreset, SortRegistry } from './sort';

/** Section key for printings outside every scene (sorts last). */
export const NO_SCENE = 'scene:none';

/** Collection's sort registry: the shared card keys plus Scene (rank in config order). */
export const COLLECTION_SORT = {
  ...CARD_SORT,
  scene: { label: 'Scene', get: (c) => c.sceneRank ?? null, defaultDir: 'asc', section: (c) => c.scene ?? NO_SCENE },
} satisfies SortRegistry<GuideCard>;

export type CollectionSortKey = keyof typeof COLLECTION_SORT;

export const SCENE_PRESET: SortPreset<CollectionSortKey> = { label: 'Scene › Number', rules: [{ key: 'scene', dir: 'asc' }, { key: 'cn', dir: 'asc' }] };

/** Presets offered in the sort builder; Scene › Number leads when the families define scenes. */
export const collectionPresets = (hasScenes: boolean): SortPreset<CollectionSortKey>[] =>
  hasScenes ? [SCENE_PRESET, ...CARD_SORT_PRESETS] : CARD_SORT_PRESETS;

/** The sort keys offered: Scene only when the families define scenes (pair with `activeRules`). */
export function collectionSortKeys(hasScenes: boolean): typeof COLLECTION_SORT {
  if (hasScenes) return COLLECTION_SORT;
  const { scene: _scene, ...rest } = COLLECTION_SORT;
  return rest as typeof COLLECTION_SORT;
}

/** Rules in effect: a Scene rule is dropped when no family in view defines scenes. */
export const activeRules = <R extends { key: string }>(rules: readonly R[], hasScenes: boolean): R[] =>
  hasScenes ? [...rules] : rules.filter((r) => r.key !== 'scene');

/** scene key → global order (payload order: family, then config order). */
export const sceneRanks = (scenes: readonly SceneOut[]): Map<string, number> => new Map(scenes.map((s, i) => [s.key, i]));

/** Whole-number % of the scene's printings held in any finish. */
export const scenePct = (s: SceneOut): number => (s.printings ? Math.round((s.owned_printings / s.printings) * 100) : 0);

export const FINISH_LABEL: Record<SceneFinishOut['finish'], string> = { nonfoil: 'Nonfoil', foil: 'Foil' };

export const isComplete = (f: SceneFinishOut): boolean => f.owned >= f.printings;

/** "4/6 · $12.12 to finish", "Complete", or "4/6 · $3.10 + 1 unpriced". */
export function finishTally(f: SceneFinishOut): string {
  if (isComplete(f)) return `${fmtInt(f.owned)}/${fmtInt(f.printings)} · complete`;
  const cost = f.missing_usd > 0 || !f.unpriced ? fmtUsd(f.missing_usd) : '';
  const unpriced = f.unpriced ? `${cost ? ' + ' : ''}${fmtInt(f.unpriced)} unpriced` : '';
  return `${fmtInt(f.owned)}/${fmtInt(f.printings)} · ${cost}${unpriced} to finish`;
}

/** Plain-language summary for the buy popover row, e.g. "4 missing · $12.12". */
export function missingLine(f: SceneFinishOut): string {
  const n = f.missing_ids.length;
  if (!n) return 'Complete';
  return `${fmtCount(n, 'missing printing')} · ${fmtUsd(f.missing_usd)}${f.unpriced ? ` + ${fmtInt(f.unpriced)} unpriced` : ''}`;
}

/** Buy-list items for one finish of a scene (one copy of each missing printing). */
export const sceneBuyItems = (f: SceneFinishOut) => f.missing_ids.map((scryfall_id) => ({ scryfall_id, finish: f.finish, qty: 1 }));

/** "Livia Prima · LTR 399–404" — the line printed beside a scene's name. */
export const sceneByline = (s: SceneOut): string =>
  [s.artist, `${s.set_code.toUpperCase()} ${s.cn_lo}–${s.cn_hi}`].filter(Boolean).join(' · ');
