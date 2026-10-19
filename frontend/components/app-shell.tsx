"use client";

import { useState, type ReactNode } from "react";

import { Sidebar } from "@/components/sidebar";
import { ToastProvider } from "@/components/toast-provider";
import { TopHeader } from "@/components/top-header";
import { cn } from "@/lib/utils";

export function AppShell({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  return (
    <ToastProvider>
      <div className="min-h-screen bg-[#08111f] text-slate-200">
        <Sidebar collapsed={collapsed} mobileOpen={mobileOpen} onToggle={() => setCollapsed((value) => !value)} onMobileClose={() => setMobileOpen(false)} />
        <div className={cn("min-h-screen transition-[padding] duration-200", collapsed ? "lg:pl-[76px]" : "lg:pl-[252px]")}>
          <TopHeader onMenuOpen={() => setMobileOpen(true)} />
          <main className="mx-auto w-full max-w-[1680px] p-4 sm:p-6 lg:p-8">{children}</main>
        </div>
      </div>
    </ToastProvider>
  );
}
