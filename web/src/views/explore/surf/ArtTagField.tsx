import { useQuery } from '@tanstack/react-query';
import { artTagsQuery } from '../../../app/queries';
import { fmtInt } from '../../../core/format';
import { TagSearchField, type TagHits } from '../../../components/TagSearchField';

function useArtHits(needle: string): TagHits {
  const res = useQuery({ ...artTagsQuery(needle), enabled: needle.length > 0 });
  return {
    synced: res.data?.synced,
    tags: (res.data?.tags ?? []).map((t) => ({ id: t.id, slug: t.slug, label: t.label, count: t.illustrations })),
    fetching: res.isFetching,
    stale: res.isPlaceholderData,
  };
}

/** Art tags (any of): suggestions from the local Scryfall art-tag cache; Enter adds the
 *  best match, or the typed tag as-is (the Surfer can ask Scryfall for any art tag). */
export function ArtTagField({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <TagSearchField
      label="Art tags"
      noun="art tag"
      placeholder="dragon, moon, ocean…"
      value={value}
      onChange={onChange}
      useHits={useArtHits}
      countTitle={(t) => `${fmtInt(t.count)} artworks tagged ${t.label}`}
      unsyncedNote={(needle) => `No art tags loaded here yet — press Enter to search Scryfall for “${needle}”.`}
      freeText
    />
  );
}
