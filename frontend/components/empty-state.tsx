import { Inbox } from "lucide-react";

import { Card } from "@/components/ui/card";

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <Card className="grid min-h-[420px] place-items-center">
      <div className="max-w-md px-6 py-16 text-center">
        <span className="mx-auto grid size-12 place-items-center rounded-xl border border-slate-800 bg-slate-950/60 text-slate-400"><Inbox className="size-5" /></span>
        <h2 className="mt-5 text-base font-semibold text-slate-100">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
      </div>
    </Card>
  );
}
