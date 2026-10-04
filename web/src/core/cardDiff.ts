// Pure view-model derivations for the missing-set card-diff view (exact printings).
import type { CardDiffTile } from './api';
import type { CardDiffSort, Pool } from './search';

export type Tile = CardDiffTile;

export function filterTiles(tiles: Tile[], q: string, show: readonly Pool[]): Tile[] {
  const ql = q.toLowerCase();
  const shown = new Set<string>(show);
  return tiles.filter((t) => (!ql || t.name.toLowerCase().includes(ql)) && t.pools.some((p) => shown.has(p)));
}

function cnKey(cn: string | null): [number, string] {
  const m = /^(\d+)(.*)$/.exec(cn ?? '');
  return m ? [Number(m[1]), m[2]] : [Number.POSITIVE_INFINITY, cn ?? ''];
}

export function sortTiles(tiles: Tile[], sort: CardDiffSort): Tile[] {
  const cmpCn = (x: Tile, y: Tile) => {
    const [a, as] = cnKey(x.collector_number);
    const [b, bs] = cnKey(y.collector_number);
    return (x.set_code ?? '').localeCompare(y.set_code ?? '') || a - b || as.localeCompare(bs);
  };
  const by: Record<CardDiffSort, (x: Tile, y: Tile) => number> = {
    value: (x, y) => (y.usd ?? -1) - (x.usd ?? -1) || cmpCn(x, y),
    name: (x, y) => x.name.localeCompare(y.name) || cmpCn(x, y),
    cn: cmpCn,
  };
  return [...tiles].sort(by[sort]);
}
