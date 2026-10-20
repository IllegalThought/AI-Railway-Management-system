import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type BadgeTone = "neutral" | "positive" | "warning" | "critical" | "danger";

const tones: Record<BadgeTone, string> = {
  neutral: "border-slate-700 bg-slate-800/70 text-slate-300",
  positive: "border-teal-400/20 bg-teal-400/10 text-teal-300",
  warning: "border-amber-400/20 bg-amber-400/10 text-amber-300",
  critical: "border-rose-400/20 bg-rose-400/10 text-rose-300",
  danger: "border-rose-400/20 bg-rose-400/10 text-rose-300",
};

export function Badge({ className, tone = "neutral", ...props }: HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium", tones[tone], className)} {...props} />;
}
