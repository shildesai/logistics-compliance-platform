"use client";

import { useEffect, useState } from "react";

import { useOrg } from "@/contexts/org-context";

interface UseOrgDataResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

interface FetchState<T> {
  slug: string;
  data: T | null;
  error: string | null;
}

/** Fetches data scoped to the currently selected organisation, and refetches
 * whenever the organisation selection changes. */
export function useOrgData<T>(fetcher: (orgSlug: string) => Promise<T>): UseOrgDataResult<T> {
  const { selectedOrg } = useOrg();
  const [state, setState] = useState<FetchState<T> | null>(null);

  useEffect(() => {
    if (!selectedOrg) return;

    let cancelled = false;

    fetcher(selectedOrg.slug)
      .then((result) => {
        if (!cancelled) setState({ slug: selectedOrg.slug, data: result, error: null });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setState({
            slug: selectedOrg.slug,
            data: null,
            error: err instanceof Error ? err.message : "Failed to load data",
          });
        }
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedOrg?.slug]);

  const loading = !selectedOrg || state?.slug !== selectedOrg.slug;

  return {
    data: loading ? null : state?.data ?? null,
    loading,
    error: loading ? null : state?.error ?? null,
  };
}
