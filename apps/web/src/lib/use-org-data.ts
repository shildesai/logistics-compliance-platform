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
 * whenever the organisation selection changes.
 *
 * Failures in the organisation lookup itself (e.g. the API is unreachable, so
 * no organisation can ever be selected) are surfaced as errors rather than
 * leaving the caller on a loading state that would never resolve.
 */
export function useOrgData<T>(fetcher: (orgSlug: string) => Promise<T>): UseOrgDataResult<T> {
  const { selectedOrg, loading: orgLoading, error: orgError } = useOrg();
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

  if (orgError) {
    return { data: null, loading: false, error: orgError };
  }

  if (orgLoading) {
    return { data: null, loading: true, error: null };
  }

  if (!selectedOrg) {
    return {
      data: null,
      loading: false,
      error: "No organisation is available for this account.",
    };
  }

  // Selection changed but its data hasn't arrived yet.
  if (state?.slug !== selectedOrg.slug) {
    return { data: null, loading: true, error: null };
  }

  return { data: state.data, loading: false, error: state.error };
}
