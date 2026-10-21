"use client";

import { Menu, ShieldCheck } from "lucide-react";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";
import { getNavigationItem } from "@/lib/navigation";

export function TopHeader({ onMenuOpen }: { onMenuOpen: () => void }) {
  const item = getNavigationItem(usePathname());
  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-4 border-b border-[#DFE4E8] bg-white/95 px-4 backdrop-blur sm:px-5 lg:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <Button variant="ghost" size="icon" className="lg:hidden" onClick={onMenuOpen} aria-label="Open navigation"><Menu className="size-5" /></Button>
        <h1 className="truncate text-base font-semibold text-[#202B36]">{item.label}</h1>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <div className="hidden items-center gap-2 rounded-md border border-[#D7DEE3] bg-[#F6F7F9] px-3 py-1.5 text-xs text-[#687581] sm:flex"><ShieldCheck className="size-3.5 text-[#4F7A63]" /><span>Simulation mode</span></div>
      </div>
    </header>
  );
}
