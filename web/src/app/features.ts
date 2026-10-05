import { useQuery } from '@tanstack/react-query';
import { featuresQuery } from './queries';

/** Is an internal feature flag on for this machine (config/features*.toml)? Off while loading. */
export function useFeature(name: string): boolean {
  const q = useQuery(featuresQuery());
  return q.data?.[name] ?? false;
}
