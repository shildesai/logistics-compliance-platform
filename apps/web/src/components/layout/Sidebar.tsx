"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV_ITEMS } from "@/lib/nav";

interface SidebarProps {
  open: boolean;
  onNavigate?: () => void;
}

export function Sidebar({ open, onNavigate }: SidebarProps) {
  const pathname = usePathname();

  return (
    <>
      {open && (
        <button
          aria-label="Close navigation"
          className="fixed inset-0 z-20 bg-slate-900/40 lg:hidden"
          onClick={onNavigate}
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex w-64 shrink-0 transform flex-col border-r border-slate-200 bg-white transition-transform duration-200 ease-in-out lg:static lg:z-auto lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-16 items-center gap-2 border-b border-slate-200 px-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-900 text-sm font-semibold text-white">
            LC
          </div>
          <span className="text-sm font-semibold text-slate-900">
            Logistics Compliance
          </span>
        </div>
        <nav aria-label="Primary" className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname?.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onNavigate}
                aria-current={isActive ? "page" : undefined}
                className={`block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-slate-900 text-white"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-200 px-4 py-3 text-xs text-slate-400">
          Phase 1 shell &middot; synthetic data
        </div>
      </aside>
    </>
  );
}
