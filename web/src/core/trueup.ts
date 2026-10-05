// Product coverage review (the trueup.scan / trueup.apply jobs): framework-free.

export type CoverageProduct = {
  fileName: string;
  name: string;
  type: string | null;
  code: string | null;
  release_date: string | null;
  recipe_qty: number;
  usd: number;
};
export type CoverageScan = {
  ready: CoverageProduct[];
  conflicts: (CoverageProduct & { lost_to: string[] })[];
  applied: boolean;
  registered: number;
  reattributed: number;
};

/** The scan artifact from a finished job, if any. */
export function scanFrom(artifacts: unknown): CoverageScan | null {
  const art = (artifacts as { label: string; data: CoverageScan }[] | undefined)?.find((a) => a.label === 'scan');
  return art?.data ?? null;
}

/** "Box Set · HOB · 2026" */
export function productMeta(p: CoverageProduct): string {
  return [p.type, p.code?.toUpperCase(), p.release_date?.slice(0, 4)].filter(Boolean).join(' · ');
}

/** Products confirmed for recording: ready ones not marked "not mine". */
export function confirmed(scan: CoverageScan, notMine: ReadonlySet<string>): CoverageProduct[] {
  return scan.ready.filter((p) => !notMine.has(p.fileName));
}

const REFUTED = 'mm.trueup.notMine';

/** Products the user said they never bought — kept out of later scans. */
export function readNotMine(): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(REFUTED) ?? '[]');
    return Array.isArray(v) ? v.map(String) : [];
  } catch {
    return [];
  }
}

export function rememberNotMine(fileNames: readonly string[]) {
  try {
    localStorage.setItem(REFUTED, JSON.stringify([...new Set([...readNotMine(), ...fileNames])]));
  } catch {
    // Storage blocked: they'll simply show up again next scan.
  }
}
