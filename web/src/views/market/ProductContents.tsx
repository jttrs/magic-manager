import { useQuery } from '@tanstack/react-query';
import { productTreeQuery } from '../../app/queries';
import type { TreeNodeOut } from '../../core/api';
import { fmtUsd } from '../../core/format';

/** A sealed product's contents tree: each sub-product's market price beside what the cards inside are worth. */
export function ProductContents({ set, name }: { set: string; name: string }) {
  const tree = useQuery(productTreeQuery(set, name, true));
  if (tree.isPending) return <p role="status" className="text-sm text-ink-muted">Opening the box…</p>;
  if (tree.isError) return <p className="text-sm text-danger">Couldn’t read its contents: {(tree.error as Error).message}</p>;
  return (
    <ul aria-label={`${name} contents`} className="flex flex-col">
      <li aria-hidden="true" className="flex gap-3 border-b border-rule pb-1 text-xs voice-semi text-ink-muted">
        <span className="flex-1">Contents</span>
        <span className="w-20 text-right">Market</span>
        <span className="w-20 text-right">Cards inside</span>
      </li>
      {tree.data.children?.length ? tree.data.children.map((n, i) => <TreeLine key={i} n={n} depth={0} />) : <li className="text-sm text-ink-muted">No listed contents.</li>}
    </ul>
  );
}

function TreeLine({ n, depth }: { n: TreeNodeOut; depth: number }) {
  return (
    <li>
      <div className="flex items-baseline gap-3 border-b border-rule/50 py-1 text-sm" style={{ paddingLeft: `${depth * 1.25}rem` }}>
        <span className="min-w-0 flex-1 text-ink">
          {n.count > 1 && <span className="tabular text-ink-muted">{n.count}× </span>}
          {n.name}
          <span className="ml-1.5 text-xs text-ink-muted">{n.kind}</span>
        </span>
        <span className="w-20 shrink-0 text-right tabular text-ink-muted" title="Market price">{fmtUsd(n.market)}</span>
        <span className="w-20 shrink-0 text-right tabular text-ink" title="Cards inside">{fmtUsd(n.contents_value)}</span>
      </div>
      {n.children?.length ? <ul>{n.children.map((c, i) => <TreeLine key={i} n={c} depth={depth + 1} />)}</ul> : null}
    </li>
  );
}
