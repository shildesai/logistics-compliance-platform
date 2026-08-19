"use client";

import { useEffect, useRef, useState } from "react";

import { useOrg } from "@/contexts/org-context";
import { api } from "@/lib/api";
import type { CurrentUser } from "@/lib/types";

export function UserMenu() {
  const [open, setOpen] = useState(false);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  const { selectedMembership } = useOrg();

  useEffect(() => {
    let cancelled = false;
    api
      .getMe()
      .then((me) => {
        if (!cancelled) setUser(me);
      })
      .catch(() => {
        /* The dashboard surfaces API failures; the menu just stays anonymous. */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    function handleClick(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const name = user?.full_name ?? "Not signed in";
  const initials = user
    ? user.full_name
        .split(" ")
        .map((part) => part[0])
        .join("")
        .slice(0, 2)
    : "–";

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex items-center gap-2 rounded-full border border-slate-200 py-1 pl-1 pr-3 hover:bg-slate-50"
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-900 text-xs font-semibold text-white">
          {initials}
        </span>
        <span className="hidden text-sm font-medium text-slate-700 sm:inline">{name}</span>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-40 mt-2 w-64 rounded-md border border-slate-200 bg-white py-1 shadow-lg"
        >
          <div className="border-b border-slate-100 px-4 py-2">
            <p className="text-sm font-medium text-slate-900">{name}</p>
            {user && <p className="text-xs text-slate-500">{user.email}</p>}
            {selectedMembership && (
              <p className="mt-1 text-xs font-medium text-slate-400">
                {selectedMembership.role.replaceAll("_", " ")} ·{" "}
                {selectedMembership.organisation.name}
              </p>
            )}
            {user?.is_platform_admin && (
              <p className="mt-1 text-xs font-medium text-amber-600">
                Platform administrator
              </p>
            )}
          </div>
          <button
            role="menuitem"
            type="button"
            className="block w-full px-4 py-2 text-left text-sm text-slate-600 hover:bg-slate-50"
          >
            Profile settings
          </button>
          <button
            role="menuitem"
            type="button"
            className="block w-full px-4 py-2 text-left text-sm text-slate-600 hover:bg-slate-50"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
