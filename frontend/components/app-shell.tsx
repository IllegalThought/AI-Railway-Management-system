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
      <div className="min-h-screen bg-[#F6F7F9] text-[#202B36]">
        <a href="#main-content" className="fixed left-4 top-3 z-[60] -translate-y-16 rounded-md bg-[#36638A] px-3 py-2 text-sm font-semibold text-white transition-transform focus:translate-y-0">Skip to main content</a>
        <Sidebar collapsed={collapsed} mobileOpen={mobileOpen} onToggle={() => setCollapsed((value) => !value)} onMobileClose={() => setMobileOpen(false)} />
        <div className={cn("min-h-screen transition-[padding] duration-200", collapsed ? "lg:pl-[76px]" : "lg:pl-[252px]")}>
          <TopHeader onMenuOpen={() => setMobileOpen(true)} />
          <main id="main-content" tabIndex={-1} className="mx-auto w-full max-w-[1720px] p-4 outline-none sm:p-5 lg:p-6">{children}</main>
        </div>
      </div>
    </ToastProvider>
  );
}
