import type { QueryClient } from '@tanstack/react-query';

/** Refresh everything a recipe read or a precon add can change. */
export async function refreshRecipes(qc: QueryClient) {
  await Promise.all(['decks', 'jumpstart', 'collection', 'holdings', 'history'].map((k) => qc.invalidateQueries({ queryKey: [k] })));
}
