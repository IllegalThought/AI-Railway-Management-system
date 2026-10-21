import type { LucideIcon } from "lucide-react";

import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export function KpiCard({ label, value, detail, icon: Icon, loading = false, tone = "neutral" }: { label: string; value: string; detail: string; icon: LucideIcon; loading?: boolean; tone?: "neutral" | "positive" | "warning" }) {
  return (
    <Card className="relative overflow-hidden p-4">
      <div className={cn("absolute inset-y-0 left-0 w-1", tone === "positive" ? "bg-[#648B71]" : tone === "warning" ? "bg-[#C59032]" : "bg-[#8A9AA7]")} />
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-[#687581]">{label}</p>
          {loading ? <Skeleton className="mt-3 h-8 w-24" /> : <p className={cn("mt-2 font-mono text-2xl font-semibold tracking-tight", tone === "positive" ? "text-[#4F7A63]" : tone === "warning" ? "text-[#956B20]" : "text-[#202B36]")}>{value}</p>}
          {loading ? <Skeleton className="mt-2 h-3 w-32" /> : <p className="mt-1 truncate text-[11px] text-[#687581]">{detail}</p>}
        </div>
        <span className="grid size-8 shrink-0 place-items-center rounded-md bg-[#EEF2F5] text-[#52616F]"><Icon className="size-4" strokeWidth={1.8} /></span>
      </div>
    </Card>
  );
}
