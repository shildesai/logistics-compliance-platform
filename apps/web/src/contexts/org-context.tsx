"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api } from "@/lib/api";
import type { Organization } from "@/lib/types";

const STORAGE_KEY = "logistics-compliance:selected-org";

interface OrgContextValue {
  organizations: Organization[];
  selectedOrg: Organization | null;
  setSelectedOrgSlug: (slug: string) => void;
  loading: boolean;
  error: string | null;
}

const OrgContext = createContext<OrgContextValue | null>(null);

export function OrgProvider({ children }: { children: ReactNode }) {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    api
      .listOrganizations()
      .then((orgs) => {
        if (cancelled) return;
        setOrganizations(orgs);
        const stored =
          typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_KEY) : null;
        const initial = orgs.find((o) => o.slug === stored) ?? orgs[0] ?? null;
        setSelectedSlug(initial?.slug ?? null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load organizations");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const setSelectedOrgSlug = (slug: string) => {
    setSelectedSlug(slug);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, slug);
    }
  };

  const selectedOrg = useMemo(
    () => organizations.find((o) => o.slug === selectedSlug) ?? null,
    [organizations, selectedSlug],
  );

  return (
    <OrgContext.Provider
      value={{ organizations, selectedOrg, setSelectedOrgSlug, loading, error }}
    >
      {children}
    </OrgContext.Provider>
  );
}

export function useOrg(): OrgContextValue {
  const ctx = useContext(OrgContext);
  if (!ctx) {
    throw new Error("useOrg must be used within an OrgProvider");
  }
  return ctx;
}
