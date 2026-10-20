"use client";

import { Menu, ShieldCheck } from "lucide-react";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";
import { getNavigationItem } from "@/lib/navigation";

export function TopHeader({ onMenuOpen }: { onMenuOpen: () => void }) {
  const item = getNavigationItem(usePathname());
  return (
    <header className="sticky top-0 z-20 flex h-18 items-center justify-between gap-4 border-b border-slate-800/80 bg-[#08111f]/85 px-4 backdrop-blur-xl sm:px-6 lg:px-8">
      <div className="flex min-w-0 items-center gap-3">
        <Button variant="ghost" size="icon" className="lg:hidden" onClick={onMenuOpen} aria-label="Open navigation"><Menu className="size-5" /></Button>
        <div className="min-w-0"><h1 className="truncate text-base font-semibold text-slate-100">{item.label}</h1><p className="hidden truncate text-xs text-slate-500 sm:block">{item.description}</p></div>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <div className="hidden items-center gap-2 rounded-md border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs text-slate-400 sm:flex"><ShieldCheck className="size-3.5 text-teal-300" /><span>Simulation mode</span></div>
      </div>
    </header>
  );
}
