import { useQuery } from '@tanstack/react-query';
import { oracleTagsQuery } from '../../app/queries';
import { InfoTip } from '../../components/InfoTip';
import { TagSearchField, type TagHits } from '../../components/TagSearchField';
import { fmtInt } from '../../core/format';

function useOracleHits(needle: string): TagHits {
  const res = useQuery({ ...oracleTagsQuery(needle), enabled: needle.length > 0 });
  return {
    synced: res.data?.synced,
    tags: (res.data?.tags ?? []).map((t) => ({ id: t.id, slug: t.slug, label: t.label, count: t.cards })),
    fetching: res.isFetching,
    stale: res.isPlaceholderData,
  };
}

/** Any Scryfall Tagger card tag (any of) — the long tail beyond the Function roots. */
export function OracleTagField({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <TagSearchField
      label="Card tags"
      noun="card tag"
      placeholder="burn, mill, flicker…"
      value={value}
      onChange={onChange}
      useHits={useOracleHits}
      countTitle={(t) => `${fmtInt(t.count)} cards tagged ${t.label} (child tags included)`}
      unsyncedNote={() => 'No card tags loaded here yet — run “Sync card and art tags” in Jobs.'}
      labelExtra={<InfoTip label="What are card tags?">Any of Scryfall’s community card tags (Tagger), searched by name. A tag includes its more specific child tags — beyond the Function shortlist above.</InfoTip>}
    />
  );
}
