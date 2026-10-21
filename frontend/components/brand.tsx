import { TrainFront } from "lucide-react";

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <span className="grid size-8 shrink-0 place-items-center rounded-md bg-[#36638A] text-white"><TrainFront className="size-[17px]" strokeWidth={1.9} /></span>
      {!compact ? <div className="min-w-0"><p className="truncate text-sm font-semibold tracking-tight text-white">RailOps AI</p><p className="truncate text-[10px] uppercase tracking-[0.16em] text-slate-500">Operations control</p></div> : null}
    </div>
  );
}
