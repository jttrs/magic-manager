// May you start a catalog-wide job here? (JobSpec scope `catalog`: admins only when hosted.)
import { useQuery } from '@tanstack/react-query';
import { jobAccessQuery } from './queries';

/** False only when the server says so; while loading (and locally) a job is offered. */
export function useJobAllowed(name: string): boolean {
  const q = useQuery(jobAccessQuery());
  return q.data?.[name] !== false;
}
