"use client";

import { OrgSelector } from "@/components/layout/OrgSelector";
import { UserMenu } from "@/components/layout/UserMenu";

interface TopBarProps {
  onMenuClick: () => void;
}

export function TopBar({ onMenuClick }: TopBarProps) {
  return (
    <header className="sticky top-0 z-10 flex h-16 items-center justify-between gap-4 border-b border-slate-200 bg-white px-4 sm:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMenuClick}
          aria-label="Toggle navigation"
          className="rounded-md p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path
              d="M2.5 5h15M2.5 10h15M2.5 15h15"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        </button>
        <OrgSelector />
      </div>
      <UserMenu />
    </header>
  );
}
