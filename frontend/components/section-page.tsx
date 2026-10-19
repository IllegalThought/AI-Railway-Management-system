import { EmptyState } from "@/components/empty-state";

export function SectionPage({ title, description }: { title: string; description: string }) {
  return (
    <div className="animate-[toast-in_220ms_ease-out]">
      <div className="mb-6"><p className="text-[11px] font-medium uppercase tracking-[0.18em] text-cyan-400/70">Operations workspace</p><h2 className="mt-2 text-xl font-semibold tracking-tight text-white sm:text-2xl">{title}</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">{description}</p></div>
      <EmptyState title={`${title} is not yet connected`} description="This workspace is reserved for a later implementation phase. No operational data or controls are simulated here." />
    </div>
  );
}
