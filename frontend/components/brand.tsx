import { TrainFront } from "lucide-react";

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <span className="grid size-9 shrink-0 place-items-center rounded-lg border border-cyan-400/20 bg-cyan-400/10 text-cyan-300"><TrainFront className="size-[18px]" strokeWidth={1.8} /></span>
      {!compact ? <div className="min-w-0"><p className="truncate text-sm font-semibold tracking-tight text-white">RailOps AI</p><p className="truncate text-[10px] uppercase tracking-[0.18em] text-slate-500">Operations workspace</p></div> : null}
    </div>
  );
}
