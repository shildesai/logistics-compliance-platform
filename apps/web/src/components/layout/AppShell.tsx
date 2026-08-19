"use client";

import { useState, type ReactNode } from "react";

import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { OrgProvider } from "@/contexts/org-context";

export function AppShell({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <OrgProvider>
      <div className="flex min-h-screen bg-slate-50">
        <Sidebar open={sidebarOpen} onNavigate={() => setSidebarOpen(false)} />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar onMenuClick={() => setSidebarOpen((v) => !v)} />
          <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">{children}</main>
        </div>
      </div>
    </OrgProvider>
  );
}
