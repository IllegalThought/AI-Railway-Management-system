import { Construction } from "lucide-react";

import { Card } from "@/components/ui/card";

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <Card className="grid min-h-[420px] place-items-center">
      <div className="max-w-md px-6 py-16 text-center">
        <span className="mx-auto grid size-12 place-items-center rounded-xl border border-slate-800 bg-slate-950/60 text-cyan-300"><Construction className="size-5" /></span>
        <h2 className="mt-5 text-base font-semibold text-slate-100">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
        <div className="mx-auto mt-6 inline-flex items-center gap-2 rounded-full border border-slate-800 bg-slate-950/40 px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500"><span className="size-1.5 rounded-full bg-slate-600" />Not available in Phase 2</div>
      </div>
    </Card>
  );
}
