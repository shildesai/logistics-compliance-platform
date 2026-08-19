"use client";

import { useEffect, useState } from "react";

import { useOrg } from "@/contexts/org-context";

interface UseOrgDataResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

interface FetchState<T> {
  key: string;
  data: T | null;
  error: string | null;
}

/** Fetches data scoped to the selected organisation, refetching when the
 * selection changes.
 *
 * Failures in the organisation lookup itself (e.g. the API is unreachable, so
 * no organisation can ever be selected) surface as errors rather than leaving
 * the caller on a loading state that never resolves.
 */
export function useOrgData<T>(
  fetcher: (organisationId: string) => Promise<T>,
): UseOrgDataResult<T> {
  const { selectedOrg, loading: orgLoading, error: orgError } = useOrg();
  const [state, setState] = useState<FetchState<T> | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const key = selectedOrg ? `${selectedOrg.id}:${reloadToken}` : null;

  useEffect(() => {
    if (!selectedOrg || key === null) return;

    let cancelled = false;

    fetcher(selectedOrg.id)
      .then((result) => {
        if (!cancelled) setState({ key, data: result, error: null });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setState({
            key,
            data: null,
            error: err instanceof Error ? err.message : "Failed to load data",
          });
        }
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const reload = () => setReloadToken((t) => t + 1);

  if (orgError) {
    return { data: null, loading: false, error: orgError, reload };
  }
  if (orgLoading) {
    return { data: null, loading: true, error: null, reload };
  }
  if (!selectedOrg) {
    return {
      data: null,
      loading: false,
      error: "No organisation is available for this account.",
      reload,
    };
  }
  if (state?.key !== key) {
    return { data: null, loading: true, error: null, reload };
  }

  return { data: state.data, loading: false, error: state.error, reload };
}
