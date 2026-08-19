"use client";

import { useEffect, useRef, useState } from "react";

// Synthetic signed-in user for the Phase 1 shell — real auth/RBAC is out of
// scope (see docs/DOMAIN_MODEL.md Identity & Tenancy context).
const CURRENT_USER = {
  name: "Sam Chen",
  email: "sam.chen@example.com",
  role: "Compliance Manager",
};

export function UserMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const initials = CURRENT_USER.name
    .split(" ")
    .map((part) => part[0])
    .join("");

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
        <span className="hidden text-sm font-medium text-slate-700 sm:inline">
          {CURRENT_USER.name}
        </span>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-40 mt-2 w-56 rounded-md border border-slate-200 bg-white py-1 shadow-lg"
        >
          <div className="border-b border-slate-100 px-4 py-2">
            <p className="text-sm font-medium text-slate-900">{CURRENT_USER.name}</p>
            <p className="text-xs text-slate-500">{CURRENT_USER.email}</p>
            <p className="mt-1 text-xs font-medium text-slate-400">{CURRENT_USER.role}</p>
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
