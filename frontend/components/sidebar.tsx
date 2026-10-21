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
      {mobileOpen ? <button className="fixed inset-0 z-30 bg-[#202831]/55 backdrop-blur-sm lg:hidden" aria-label="Close navigation" onClick={onMobileClose} /> : null}
      <aside className={cn("fixed inset-y-0 left-0 z-40 flex flex-col border-r border-[#303b45] bg-[#202831] text-white transition-[width,transform] duration-200 lg:translate-x-0", collapsed ? "w-[76px]" : "w-[252px]", mobileOpen ? "translate-x-0" : "-translate-x-full")}>
        <div className="flex h-16 items-center justify-between border-b border-white/10 px-5">
          <Brand compact={collapsed} />
          <Button className="lg:hidden" variant="ghost" size="icon" onClick={onMobileClose} aria-label="Close navigation"><X className="size-4" /></Button>
        </div>
        <nav aria-label="Primary navigation" className="flex-1 space-y-1 overflow-y-auto px-3 py-5">
          {!collapsed ? <p className="mb-2 px-2 text-[10px] font-medium uppercase tracking-[0.16em] text-slate-500">Workspaces</p> : null}
          {navigationItems.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link key={item.href} href={item.href} onClick={onMobileClose} title={collapsed ? item.label : undefined} aria-current={active ? "page" : undefined} className={cn("group flex h-10 items-center gap-3 rounded-md px-3 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7298b8]", active ? "bg-white/10 text-white shadow-[inset_3px_0_0_#7298b8]" : "text-slate-400 hover:bg-white/[0.06] hover:text-slate-100", collapsed && "justify-center px-0")}>
                <Icon className="size-[17px] shrink-0" strokeWidth={active ? 2 : 1.7} />
                {!collapsed ? <span className="truncate">{item.label}</span> : <span className="sr-only">{item.label}</span>}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-white/10 p-3">
          <Button type="button" variant="ghost" className="hidden w-full text-slate-400 hover:bg-white/[0.06] hover:text-white lg:flex" onClick={onToggle} aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}>{collapsed ? <ChevronRight className="size-4" /> : <><ChevronLeft className="size-4" /><span>Collapse sidebar</span></>}</Button>
        </div>
      </aside>
    </>
  );
}
