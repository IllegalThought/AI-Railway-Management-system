import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type BadgeTone = "neutral" | "positive" | "warning" | "critical" | "danger";

const tones: Record<BadgeTone, string> = {
  neutral: "border-[#D7DEE3] bg-[#F3F5F6] text-[#52616F]",
  positive: "border-[#BCD0C2] bg-[#EDF5EF] text-[#3F6B51]",
  warning: "border-[#E5D0A8] bg-[#FFF7E8] text-[#8A641F]",
  critical: "border-[#E1B9B9] bg-[#FCEEEE] text-[#9B4141]",
  danger: "border-[#E1B9B9] bg-[#FCEEEE] text-[#9B4141]",
};

export function Badge({ className, tone = "neutral", ...props }: HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium", tones[tone], className)} {...props} />;
}
