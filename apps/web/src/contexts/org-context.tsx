"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api } from "@/lib/api";
import type { Membership, Organisation, Permission } from "@/lib/types";

const STORAGE_KEY = "logistics-compliance:selected-organisation";

interface OrgContextValue {
  memberships: Membership[];
  selectedMembership: Membership | null;
  selectedOrg: Organisation | null;
  setSelectedOrgId: (id: string) => void;
  /** Permission check for the *current* organisation. The server enforces
   * this independently; this only decides what the UI offers. */
  can: (permission: Permission) => boolean;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

const OrgContext = createContext<OrgContextValue | null>(null);

export function OrgProvider({ children }: { children: ReactNode }) {
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;

    api
      .listMyOrganisations()
      .then((result) => {
        if (cancelled) return;
        setMemberships(result);
        setError(null);
        const stored =
          typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_KEY) : null;
        const initial =
          result.find((m) => m.organisation.id === stored) ?? result[0] ?? null;
        setSelectedId(initial?.organisation.id ?? null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setMemberships([]);
        setError(err instanceof Error ? err.message : "Failed to load organisations");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  const setSelectedOrgId = useCallback((id: string) => {
    setSelectedId(id);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, id);
    }
  }, []);

  const selectedMembership = useMemo(
    () => memberships.find((m) => m.organisation.id === selectedId) ?? null,
    [memberships, selectedId],
  );

  const can = useCallback(
    (permission: Permission) =>
      selectedMembership?.permissions.includes(permission) ?? false,
    [selectedMembership],
  );

  const value = useMemo<OrgContextValue>(
    () => ({
      memberships,
      selectedMembership,
      selectedOrg: selectedMembership?.organisation ?? null,
      setSelectedOrgId,
      can,
      loading,
      error,
      reload: () => setReloadToken((t) => t + 1),
    }),
    [memberships, selectedMembership, setSelectedOrgId, can, loading, error],
  );

  return <OrgContext.Provider value={value}>{children}</OrgContext.Provider>;
}

export function useOrg(): OrgContextValue {
  const ctx = useContext(OrgContext);
  if (!ctx) {
    throw new Error("useOrg must be used within an OrgProvider");
  }
  return ctx;
}
