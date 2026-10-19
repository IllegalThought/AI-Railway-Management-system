import type { LucideIcon } from "lucide-react";

import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export function KpiCard({ label, value, detail, icon: Icon, loading = false, tone = "neutral" }: { label: string; value: string; detail: string; icon: LucideIcon; loading?: boolean; tone?: "neutral" | "positive" | "warning" }) {
  return (
    <Card className="relative overflow-hidden p-4 sm:p-5">
      <div className={cn("absolute inset-x-0 top-0 h-px", tone === "positive" ? "bg-teal-400/55" : tone === "warning" ? "bg-amber-400/45" : "bg-slate-700")} />
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-slate-500">{label}</p>
          {loading ? <Skeleton className="mt-3 h-8 w-24" /> : <p className={cn("mt-2 font-mono text-2xl font-semibold tracking-tight sm:text-[28px]", tone === "positive" ? "text-teal-300" : tone === "warning" ? "text-amber-300" : "text-slate-100")}>{value}</p>}
          {loading ? <Skeleton className="mt-2 h-3 w-32" /> : <p className="mt-1.5 truncate text-[11px] text-slate-500">{detail}</p>}
        </div>
        <span className="grid size-9 shrink-0 place-items-center rounded-lg border border-slate-800 bg-slate-950/60 text-slate-400"><Icon className="size-4" strokeWidth={1.8} /></span>
      </div>
    </Card>
  );
}
