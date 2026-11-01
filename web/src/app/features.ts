import { useQuery } from '@tanstack/react-query';
import { featuresQuery, ownerPathsQuery } from './queries';

/** Is a feature flag on for you (config/features*.toml; hosted, with your admin-set overrides)? Off while loading. */
export function useFeature(name: string): boolean {
  const q = useQuery(featuresQuery());
  return q.data?.[name] ?? false;
}

/** May you use a path that runs on the owner's machine or logins (e.g. `manapool.server_login`)?
 *  Locally yes; hosted, admins only — whatever the flags say. No while loading. */
export function useOwnerPath(key: string): boolean {
  const q = useQuery(ownerPathsQuery());
  if (!q.data) return false;
  // A server that doesn't list the path: allowed locally (your own machine), never when hosted.
  return q.data.paths[key] ?? !q.data.hosted;
}
