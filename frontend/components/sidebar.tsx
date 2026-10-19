"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronLeft, ChevronRight, X } from "lucide-react";

import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { navigationItems } from "@/lib/navigation";
import { cn } from "@/lib/utils";

export function Sidebar({ collapsed, mobileOpen, onToggle, onMobileClose }: { collapsed: boolean; mobileOpen: boolean; onToggle: () => void; onMobileClose: () => void }) {
  const pathname = usePathname();
  return (
    <>
      {mobileOpen ? <button className="fixed inset-0 z-30 bg-slate-950/75 backdrop-blur-sm lg:hidden" aria-label="Close navigation" onClick={onMobileClose} /> : null}
      <aside className={cn("fixed inset-y-0 left-0 z-40 flex flex-col border-r border-slate-800/90 bg-[#07101f]/95 transition-[width,transform] duration-200 lg:translate-x-0", collapsed ? "w-[76px]" : "w-[252px]", mobileOpen ? "translate-x-0" : "-translate-x-full")}>
        <div className="flex h-18 items-center justify-between border-b border-slate-800/80 px-5">
          <Brand compact={collapsed} />
          <Button className="lg:hidden" variant="ghost" size="icon" onClick={onMobileClose} aria-label="Close navigation"><X className="size-4" /></Button>
        </div>
        <nav aria-label="Primary navigation" className="flex-1 space-y-1 overflow-y-auto px-3 py-5">
          {!collapsed ? <p className="mb-2 px-2 text-[10px] font-medium uppercase tracking-[0.18em] text-slate-600">Workspace</p> : null}
          {navigationItems.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link key={item.href} href={item.href} onClick={onMobileClose} title={collapsed ? item.label : undefined} aria-current={active ? "page" : undefined} className={cn("group flex h-10 items-center gap-3 rounded-md px-3 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/60", active ? "bg-cyan-400/10 text-cyan-200 shadow-[inset_2px_0_0_#22d3ee]" : "text-slate-400 hover:bg-slate-800/70 hover:text-slate-100", collapsed && "justify-center px-0")}>
                <Icon className="size-[17px] shrink-0" strokeWidth={active ? 2 : 1.7} />
                {!collapsed ? <span className="truncate">{item.label}</span> : <span className="sr-only">{item.label}</span>}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-800/80 p-3">
          {!collapsed ? <div className="mb-3 rounded-lg border border-slate-800 bg-slate-950/50 p-3"><div className="flex items-center gap-2 text-xs font-medium text-slate-300"><span className="size-1.5 rounded-full bg-teal-400 shadow-[0_0_8px_rgba(45,212,191,0.6)]" />Synthetic environment</div><p className="mt-1.5 text-[11px] leading-4 text-slate-500">Decision-support simulation only</p></div> : null}
          <Button type="button" variant="ghost" className="hidden w-full text-slate-500 lg:flex" onClick={onToggle} aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}>{collapsed ? <ChevronRight className="size-4" /> : <><ChevronLeft className="size-4" /><span>Collapse sidebar</span></>}</Button>
        </div>
      </aside>
    </>
  );
}
